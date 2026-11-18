import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  apiClient,
  ApiError,
  apiRequest,
  getCsrfToken,
  readCsrfCookie,
  registerUnauthorizedCallback,
  resetCsrfToken,
  setCsrfToken,
} from './apiClient';

describe('Cliente HTTP Resiliente (apiClient.ts)', () => {
  afterEach(() => {
    registerUnauthorizedCallback(null);
    resetCsrfToken();
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

  it('soporta FormData/Blob sin forzar Content-Type JSON, métodos patch/delete y respuesta JSON corrupta', async () => {
    setCsrfToken('csrf-form');
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 202,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ url: 's3://bucket/comprobante.avif', estado: 'ENCOLADO' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const formData = new FormData();
    formData.append('archivo', new Blob(['png-bytes'], { type: 'image/png' }), 'pago.png');

    await apiClient.post('/api/evidencias/subir?categoria=comprobantes', formData, {
      idempotencyKey: 'idemp-upload-1',
    });

    const [, firstInit] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(firstInit.body).toBe(formData);
    expect((firstInit.headers as Record<string, string>)['Content-Type']).toBeUndefined();
    expect((firstInit.headers as Record<string, string>)['Idempotency-Key']).toBe('idemp-upload-1');

    // Blob body directo también preserva binario
    const rawBlob = new Blob(['abc'], { type: 'application/octet-stream' });
    await apiClient.patch('/api/test', rawBlob);
    const [, patchInit] = fetchMock.mock.calls[1] as [string, RequestInit];
    expect(patchInit.method).toBe('PATCH');
    expect(patchInit.body).toBe(rawBlob);
    expect((patchInit.headers as Record<string, string>)['Idempotency-Key']).toBeTruthy();

    // DELETE adjunta Idempotency-Key automática y método DELETE
    await apiClient.delete('/api/accesos/pases/9');
    const [, delInit] = fetchMock.mock.calls[2] as [string, RequestInit];
    expect(delInit.method).toBe('DELETE');
    expect((delInit.headers as Record<string, string>)['Idempotency-Key']).toBeTruthy();

    // Respuesta con content-type application/json cuyo .json() falla (ej. body vacío) no lanza SyntaxError
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 204,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => {
          throw new SyntaxError('Unexpected end of JSON input');
        },
      }),
    );
    await expect(apiClient.get('/api/health')).resolves.toBeNull();
  });

  it('conserva exactamente la misma Idempotency-Key al reintentar tras refresh por HTTP 401 e invoca callback 401 si falla', async () => {
    setCsrfToken('csrf-retry');
    const capturedKeys: string[] = [];
    let attempt = 0;

    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        if (String(input) === '/api/auth/refresh') {
          return {
            ok: true,
            status: 200,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: async () => ({ message: 'ok', csrf_token: 'csrf-refreshed' }),
          } as Response;
        }
        attempt += 1;
        const headers = init?.headers as Record<string, string>;
        capturedKeys.push(headers['Idempotency-Key']);
        if (attempt === 1) {
          return {
            ok: false,
            status: 401,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: async () => ({ detail: 'Expirado' }),
          } as Response;
        }
        return {
          ok: true,
          status: 201,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ id: 99 }),
        } as Response;
      }),
    );

    const created = await apiClient.post<{ id: number }>('/api/incidencias/crear', {
      area: 'Ascensor',
      descripcion: 'Falla',
    });
    expect(created.id).toBe(99);
    expect(capturedKeys).toHaveLength(2);
    expect(capturedKeys[0]).toBe(capturedKeys[1]);
    expect(capturedKeys[0].length).toBeGreaterThanOrEqual(8);

    // Callback unauthorized + resetCsrfToken cuando el refresh falla en 401
    const unauthSpy = vi.fn();
    registerUnauthorizedCallback(unauthSpy);
    setCsrfToken('csrf-to-clear');
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        status: 401,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ detail: 'Token revocado' }),
      })),
    );
    await expect(apiClient.get('/api/finanzas/resumen')).rejects.toMatchObject({
      status: 401,
      refreshAttempted: true,
    });
    expect(unauthSpy).toHaveBeenCalledTimes(1);
    expect(getCsrfToken()).toBe('csrf-client-initialized');
  });

  it('transforma errores HTTP (detail string, detail array y sin JSON) y fallos de red en ApiError', async () => {
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

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        headers: new Headers({ 'content-type': 'text/plain' }),
      }),
    );
    await expect(apiRequest('/api/health')).rejects.toEqual(new ApiError(500, 'Error HTTP 500'));

    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network offline')));
    await expect(apiRequest('/api/auth/me')).rejects.toEqual(
      new ApiError(0, 'Sin conexión con el servidor. Verifique su red.'),
    );

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
    const customErr = new ApiError(400, 'Detalle');
    expect(customErr.name).toBe('ApiError');

    document.cookie = '  csrf_token=abc=def=123 ';
    expect(readCsrfCookie()).toBe('abc=def=123');
    document.cookie = 'csrf_token=';
    expect(readCsrfCookie()).toBeNull();

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
