import { sanitizeObject, generateIdempotencyKey } from '../utils/security';

export class ApiError extends Error {
  public readonly status: number;
  public readonly detail: string;
  public readonly refreshAttempted: boolean;

  constructor(status: number, detail: string, refreshAttempted = false) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.refreshAttempted = refreshAttempted;
  }
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  body?: unknown;
  idempotencyKey?: string;
  csrfToken?: string;
  headers?: Record<string, string>;
}

const MUTATING_METHODS = new Set(['POST', 'PUT', 'DELETE', 'PATCH']);
const REFRESH_EXCLUDED_PATHS = new Set([
  '/api/auth/login',
  '/api/auth/register',
  '/api/auth/refresh',
  '/api/auth/logout',
]);

export function readCsrfCookie(): string | null {
  if (typeof document === 'undefined' || !document.cookie) {
    return null;
  }
  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [rawName, ...rawRest] = cookie.trim().split('=');
    if (rawName === 'csrf_token') {
      const value = rawRest.join('=').trim();
      return value ? decodeURIComponent(value) : null;
    }
  }
  return null;
}

const DEFAULT_CSRF_TOKEN = 'csrf-client-initialized';
let activeCsrfToken = readCsrfCookie() ?? DEFAULT_CSRF_TOKEN;
let lastCookieCsrfToken: string | null = readCsrfCookie();
let inflightRefresh: Promise<boolean> | null = null;
let unauthorizedCallback: ((err: ApiError) => Promise<void> | void) | null = null;

function syncCsrfFromCookieIfNeeded(): void {
  const cookieToken = readCsrfCookie();
  if (
    cookieToken &&
    (activeCsrfToken === DEFAULT_CSRF_TOKEN || cookieToken !== lastCookieCsrfToken)
  ) {
    lastCookieCsrfToken = cookieToken;
    activeCsrfToken = cookieToken;
  }
}

export function setCsrfToken(token: string): void {
  activeCsrfToken = token;
}

export function resetCsrfToken(): void {
  activeCsrfToken = DEFAULT_CSRF_TOKEN;
  lastCookieCsrfToken = null;
}

export function registerUnauthorizedCallback(
  callback: ((err: ApiError) => Promise<void> | void) | null,
): void {
  unauthorizedCallback = callback;
}

export function getCsrfToken(): string {
  syncCsrfFromCookieIfNeeded();
  return activeCsrfToken;
}

function syncCsrfFromResponse(response: Response, parsed: unknown): void {
  const headerToken = response.headers?.get?.('x-csrf-token')?.trim();
  if (headerToken) {
    activeCsrfToken = headerToken;
    return;
  }
  if (parsed && typeof parsed === 'object' && 'csrf_token' in parsed) {
    const bodyToken = (parsed as { csrf_token?: unknown }).csrf_token;
    if (typeof bodyToken === 'string' && bodyToken.trim().length > 0) {
      activeCsrfToken = bodyToken.trim();
      return;
    }
  }
  syncCsrfFromCookieIfNeeded();
}

function extractErrorDetail(payload: unknown, fallbackStatus: number): string {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string };
      if (first && typeof first.msg === 'string') {
        return first.msg;
      }
    }
  }
  return `Error HTTP ${fallbackStatus}`;
}

async function parseJsonSafely(response: Response): Promise<unknown> {
  const contentType = response.headers?.get?.('content-type') ?? '';
  if (!contentType.includes('application/json')) {
    return null;
  }
  try {
    return sanitizeObject(await response.json());
  } catch {
    return null;
  }
}

function isBinaryBody(body: unknown): boolean {
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;
  const isBlob = typeof Blob !== 'undefined' && body instanceof Blob;
  return isFormData || isBlob;
}

async function executeRefreshSession(): Promise<boolean> {
  try {
    const res = await fetch('/api/auth/refresh', {
      method: 'POST',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'X-CSRF-Token': getCsrfToken(),
      },
    });
    const parsed = await parseJsonSafely(res);
    syncCsrfFromResponse(res, parsed);
    return res.ok;
  } catch {
    return false;
  }
}

async function trySingleFlightRefresh(): Promise<boolean> {
  if (!inflightRefresh) {
    inflightRefresh = executeRefreshSession().finally(() => {
      inflightRefresh = null;
    });
  }
  return inflightRefresh;
}

function buildRequestHeaders(
  method: string,
  options: RequestOptions,
  rawBody: boolean,
): Record<string, string> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(options.headers ?? {}),
  };
  if (options.body !== undefined && !rawBody && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }
  if (MUTATING_METHODS.has(method)) {
    headers['X-CSRF-Token'] = options.csrfToken ?? getCsrfToken();
  }
  if (options.idempotencyKey) {
    headers['Idempotency-Key'] = options.idempotencyKey;
  }
  return headers;
}

async function notifyUnauthorizedFailure(err: ApiError): Promise<void> {
  resetCsrfToken();
  if (unauthorizedCallback) {
    await unauthorizedCallback(err);
  }
}

async function executeApiRequest<T>(
  path: string,
  options: RequestOptions,
  retried: boolean,
): Promise<T> {
  const method = options.method ?? 'GET';
  const basePath = path.split('?')[0];
  const rawBody = isBinaryBody(options.body);
  const headers = buildRequestHeaders(method, options, rawBody);

  let serializedBody: BodyInit | undefined;
  if (options.body !== undefined) {
    serializedBody = rawBody ? (options.body as BodyInit) : JSON.stringify(options.body);
  }

  let response: Response;
  try {
    response = await fetch(path, {
      method,
      credentials: 'include',
      headers,
      body: serializedBody,
    });
  } catch {
    throw new ApiError(0, 'Sin conexión con el servidor. Verifique su red.');
  }

  const parsed = await parseJsonSafely(response);
  syncCsrfFromResponse(response, parsed);

  if (response.status === 401 && !retried && !REFRESH_EXCLUDED_PATHS.has(basePath)) {
    const refreshed = await trySingleFlightRefresh();
    if (refreshed) {
      return executeApiRequest<T>(path, options, true);
    }
    const authErr = new ApiError(401, extractErrorDetail(parsed, 401), true);
    await notifyUnauthorizedFailure(authErr);
    throw authErr;
  }

  if (!response.ok) {
    throw new ApiError(response.status, extractErrorDetail(parsed, response.status), retried);
  }

  return parsed as T;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? 'GET';
  const basePath = path.split('?')[0];
  const needsAutoIdempotency =
    MUTATING_METHODS.has(method) &&
    !REFRESH_EXCLUDED_PATHS.has(basePath) &&
    !options.idempotencyKey;

  const resolvedOptions: RequestOptions = needsAutoIdempotency
    ? { ...options, idempotencyKey: generateIdempotencyKey() }
    : options;

  return executeApiRequest<T>(path, resolvedOptions, false);
}

export const apiClient = {
  get<T>(path: string, options: Omit<RequestOptions, 'method' | 'body'> = {}): Promise<T> {
    return apiRequest<T>(path, { ...options, method: 'GET' });
  },
  post<T>(
    path: string,
    body?: unknown,
    options: Omit<RequestOptions, 'method' | 'body'> = {},
  ): Promise<T> {
    return apiRequest<T>(path, { ...options, method: 'POST', body });
  },
  put<T>(
    path: string,
    body?: unknown,
    options: Omit<RequestOptions, 'method' | 'body'> = {},
  ): Promise<T> {
    return apiRequest<T>(path, { ...options, method: 'PUT', body });
  },
  patch<T>(
    path: string,
    body?: unknown,
    options: Omit<RequestOptions, 'method' | 'body'> = {},
  ): Promise<T> {
    return apiRequest<T>(path, { ...options, method: 'PATCH', body });
  },
  delete<T>(path: string, options: Omit<RequestOptions, 'method' | 'body'> = {}): Promise<T> {
    return apiRequest<T>(path, { ...options, method: 'DELETE' });
  },
};
