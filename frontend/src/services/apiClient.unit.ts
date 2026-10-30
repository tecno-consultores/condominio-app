import { afterEach, describe, expect, it, vi } from 'vitest';
import { apiClient, ApiError, apiRequest, getCsrfToken, setCsrfToken } from './apiClient';

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
});
