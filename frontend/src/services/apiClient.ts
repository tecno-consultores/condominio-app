import { sanitizeObject } from '../utils/security';

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

let activeCsrfToken = readCsrfCookie() ?? 'csrf-client-initialized';
let lastCookieCsrfToken: string | null = readCsrfCookie();
let inflightRefresh: Promise<boolean> | null = null;

function syncCsrfFromCookieIfNeeded(): void {
  const cookieToken = readCsrfCookie();
  if (
    cookieToken &&
    (activeCsrfToken === 'csrf-client-initialized' || cookieToken !== lastCookieCsrfToken)
  ) {
    lastCookieCsrfToken = cookieToken;
    activeCsrfToken = cookieToken;
  }
}

export function setCsrfToken(token: string): void {
  activeCsrfToken = token;
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
    const contentType = res.headers?.get?.('content-type') ?? '';
    let parsed: unknown = null;
    if (contentType.includes('application/json')) {
      parsed = sanitizeObject(await res.json());
    }
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

async function executeApiRequest<T>(
  path: string,
  options: RequestOptions,
  retried: boolean,
): Promise<T> {
  const method = options.method ?? 'GET';
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(options.headers ?? {}),
  };

  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  if (MUTATING_METHODS.has(method)) {
    headers['X-CSRF-Token'] = options.csrfToken ?? getCsrfToken();
  }
  if (options.idempotencyKey) {
    headers['Idempotency-Key'] = options.idempotencyKey;
  }

  let response: Response;
  try {
    response = await fetch(path, {
      method,
      credentials: 'include',
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    throw new ApiError(0, 'Sin conexión con el servidor. Verifique su red.');
  }

  let parsed: unknown = null;
  const contentType = response.headers?.get?.('content-type') ?? '';
  if (contentType.includes('application/json')) {
    parsed = sanitizeObject(await response.json());
  }
  syncCsrfFromResponse(response, parsed);

  if (response.status === 401 && !retried && !REFRESH_EXCLUDED_PATHS.has(path)) {
    const refreshed = await trySingleFlightRefresh();
    if (refreshed) {
      return executeApiRequest<T>(path, options, true);
    }
    throw new ApiError(401, extractErrorDetail(parsed, 401), true);
  }

  if (!response.ok) {
    throw new ApiError(response.status, extractErrorDetail(parsed, response.status), retried);
  }

  return parsed as T;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  return executeApiRequest<T>(path, options, false);
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
};
