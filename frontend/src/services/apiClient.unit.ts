import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  apiClient,
  ApiError,
  apiRequest,
  getCsrfToken,
  readCsrfCookie,
  setCsrfToken,
} from './apiClient';

describe('Cliente HTTP Resiliente (apiClient.ts)', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('gestiona el token CSRF y envía credentials: include e Idempotency-Key en mutaciones', async () => {
    setCsrfToken('csrf-token-123');
    expect(getCsrfToken()).toBe('csrf-token-123');

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ id: 7, estado: 'CREADO' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const res = await apiRequest<{ id: number; estado: string }>('/api/auth/register', {
      method: 'POST',
      idempotencyKey: 'uuid-key-1',
      body: { nombre: 'Ana' },
    });

    expect(res.id).toBe(7);
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/register',
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          'X-CSRF-Token': 'csrf-token-123',
          'Idempotency-Key': 'uuid-key-1',
        }),
      }),
    );
  });

  it('transforma errores HTTP (detail string, detail array y sin JSON) y fallos de red en ApiError', async () => {
    // Caso 1: detail como string (ej. 401)
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ detail: 'Credenciales inválidas' }),
      }),
    );
    await expect(apiRequest('/api/auth/login', { method: 'POST', body: {} })).rejects.toEqual(
      new ApiError(401, 'Credenciales inválidas'),
    );

    // Caso 2: detail como arreglo de validación 422
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ detail: [{ msg: 'correo electrónico inválido' }] }),
      }),
    );
    await expect(apiRequest('/api/auth/register', { method: 'POST', body: {} })).rejects.toEqual(
      new ApiError(422, 'correo electrónico inválido'),
    );

    // Caso 3: Respuesta 500 sin cuerpo JSON
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        headers: new Headers({ 'content-type': 'text/plain' }),
      }),
    );
    await expect(apiRequest('/api/health')).rejects.toEqual(new ApiError(500, 'Error HTTP 500'));

    // Caso 4: Fallo de red (fetch rechaza promesa)
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network offline')));
    await expect(apiRequest('/api/auth/me')).rejects.toEqual(
      new ApiError(0, 'Sin conexión con el servidor. Verifique su red.'),
    );

    // Caso 5: Atajos apiClient.get / post / put
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ ok: true }),
      }),
    );
    await expect(apiClient.get<{ ok: boolean }>('/api/health')).resolves.toEqual({ ok: true });
    await expect(
      apiClient.post<{ ok: boolean }>('/api/finanzas/tasa', { tasa_usd_ves: '36.50' }),
    ).resolves.toEqual({
      ok: true,
    });
    await expect(apiClient.put<{ ok: boolean }>('/api/pagos/1/aprobar', {})).resolves.toEqual({
      ok: true,
    });
  });

  it('sincroniza CSRF desde cookie o cabecera y realiza refresh single-flight ante HTTP 401 concurrente', async () => {
    document.cookie = 'csrf_token=csrf-cookie-xyz';
    setCsrfToken('csrf-client-initialized');
    expect(getCsrfToken()).toBe('csrf-cookie-xyz');

    let protectedCalls = 0;
    let refreshCalls = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === '/api/auth/refresh') {
        refreshCalls += 1;
        return {
          ok: true,
          status: 200,
          headers: new Headers({
            'content-type': 'application/json',
            'x-csrf-token': 'csrf-rotado-nuevo',
          }),
          json: async () => ({ message: 'Sesión renovada', csrf_token: 'csrf-rotado-nuevo' }),
        } as Response;
      }
      protectedCalls += 1;
      if (protectedCalls <= 2) {
        return {
          ok: false,
          status: 401,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ detail: 'Token expirado' }),
        } as Response;
      }
      return {
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ items: ['ok'] }),
      } as Response;
    });
    vi.stubGlobal('fetch', fetchMock);

    const [r1, r2] = await Promise.all([
      apiClient.get<{ items: string[] }>('/api/finanzas/resumen'),
      apiClient.get<{ items: string[] }>('/api/finanzas/tasa'),
    ]);

    expect(r1.items).toEqual(['ok']);
    expect(r2.items).toEqual(['ok']);
    expect(refreshCalls).toBe(1);
    expect(getCsrfToken()).toBe('csrf-rotado-nuevo');

    // Si /api/auth/refresh falla, propaga ApiError(401, ..., true) sin loop infinito
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        status: 401,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ detail: 'Sesión expirada' }),
      })),
    );
    await expect(apiClient.get('/api/finanzas/resumen')).rejects.toMatchObject({
      status: 401,
      refreshAttempted: true,
    });

    // Sincroniza csrf_token desde cuerpo JSON, rotaciones en document.cookie y fallos de red en /refresh
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url === '/api/auth/refresh') {
          throw new Error('ECONNRESET');
        }
        if (url === '/api/finanzas/tasa') {
          return {
            ok: true,
            status: 200,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: async () => ({ ok: true, csrf_token: 'csrf-body-rotado' }),
          } as Response;
        }
        return {
          ok: false,
          status: 401,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ detail: 'Token vencido' }),
        } as Response;
      }),
    );
    await expect(apiClient.get('/api/finanzas/tasa')).resolves.toMatchObject({ ok: true });
    expect(getCsrfToken()).toBe('csrf-body-rotado');

    document.cookie = 'csrf_token=csrf-cookie-nueva';
    expect(getCsrfToken()).toBe('csrf-cookie-nueva');

    await expect(apiClient.get('/api/pagos/revision')).rejects.toMatchObject({
      status: 401,
      refreshAttempted: true,
    });

    document.cookie = 'csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT';
    document.cookie = 'otra_cookie=solo_prueba';
    expect(readCsrfCookie()).toBeNull();
  });

  it('cubre fronteras estrictas de GET sin mutación, cookies CSRF, detail[] vacío y reutilización post-refresh', async () => {
    // 1. Nombre exacto de ApiError y bordes de extractErrorDetail
    const customErr = new ApiError(400, 'Detalle');
    expect(customErr.name).toBe('ApiError');

    document.cookie = '  csrf_token=abc=def=123 ';
    expect(readCsrfCookie()).toBe('abc=def=123');
    document.cookie = 'csrf_token=';
    expect(readCsrfCookie()).toBeNull();

    // 2. GET sin opciones: no adjunta Content-Type, X-CSRF-Token ni Idempotency-Key
    const getFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({
        'content-type': 'application/json',
        'x-csrf-token': '  csrf-trimmed-header  ',
      }),
      json: async () => ({ status: 'healthy', csrf_token: '   ' }),
    });
    vi.stubGlobal('fetch', getFetch);

    await apiRequest<{ status: string }>('/api/health');
    expect(getFetch).toHaveBeenCalledWith('/api/health', {
      method: 'GET',
      credentials: 'include',
      headers: { Accept: 'application/json' },
      body: undefined,
    });
    expect(getCsrfToken()).toBe('csrf-trimmed-header');

    // Body con csrf_token en blanco NO sobreescribe el token activo ni acepta msg no-string
    setCsrfToken('csrf-estable');
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce({
          ok: false,
          status: 422,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ detail: [], csrf_token: '   ' }),
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 422,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ detail: [{ msg: 404 }], csrf_token: '  csrf-body-trimmed  ' }),
        }),
    );
    await expect(apiRequest('/api/test')).rejects.toMatchObject({ detail: 'Error HTTP 422' });
    expect(getCsrfToken()).toBe('csrf-estable');
    await expect(apiRequest('/api/test')).rejects.toMatchObject({ detail: 'Error HTTP 422' });
    expect(getCsrfToken()).toBe('csrf-body-trimmed');

    // 3. Verifica argumentos exactos de POST /api/auth/refresh y reinicio de inflightRefresh en ciclos secuenciales
    setCsrfToken('csrf-para-refresh');
    let phase = 0;
    const seqFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === '/api/auth/refresh') {
        expect(init).toEqual({
          method: 'POST',
          credentials: 'include',
          headers: {
            Accept: 'application/json',
            'X-CSRF-Token': 'csrf-para-refresh',
          },
        });
        return {
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ ok: true }),
        } as Response;
      }
      phase += 1;
      if (phase % 2 === 1) {
        return {
          ok: false,
          status: 401,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ detail: 'Expirado' }),
        } as Response;
      }
      return {
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ ok: true }),
      } as Response;
    });
    vi.stubGlobal('fetch', seqFetch);

    await expect(apiClient.get('/api/finanzas/resumen')).resolves.toEqual({ ok: true });
    await expect(apiClient.get('/api/finanzas/resumen')).resolves.toEqual({ ok: true });
    const refreshCalls = seqFetch.mock.calls.filter(([u]) => u === '/api/auth/refresh');
    expect(refreshCalls).toHaveLength(2);
  });
});
