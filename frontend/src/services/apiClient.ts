import { sanitizeObject } from '../utils/security';

export class ApiError extends Error {
  public readonly status: number;
  public readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
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

let activeCsrfToken = 'csrf-client-initialized';

export function setCsrfToken(token: string): void {
  activeCsrfToken = token;
}

export function getCsrfToken(): string {
  return activeCsrfToken;
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

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? 'GET';
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(options.headers ?? {}),
  };

  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  if (MUTATING_METHODS.has(method)) {
    headers['X-CSRF-Token'] = options.csrfToken ?? activeCsrfToken;
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
  const contentType = response.headers.get('content-type') ?? '';
  if (contentType.includes('application/json')) {
    parsed = sanitizeObject(await response.json());
  }

  if (!response.ok) {
    throw new ApiError(response.status, extractErrorDetail(parsed, response.status));
  }

  return parsed as T;
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
