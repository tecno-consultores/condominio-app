import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  escapeHtml,
  generateIdempotencyKey,
  isSafeMediaUrl,
  isSafeRedirectUrl,
  MAX_UPLOAD_BYTES,
  sanitizeObject,
  sanitizeUntrustedText,
  validateProofFileUpload,
} from './security';

describe('Utilidades de Seguridad Cliente Nivel 11X (security.ts)', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });
  it('escapa caracteres peligrosos XSS con escapeHtml y limpia controles sin doble-escapar en sanitizeUntrustedText', () => {
    expect(escapeHtml('<script>alert("xss" & \'1\')</script>')).toBe(
      '&lt;script&gt;alert(&quot;xss&quot; &amp; &#39;1&#39;)&lt;/script&gt;',
    );
    expect(sanitizeUntrustedText('  Hola\u0000\u0007 "Mundo" & <tag>  ')).toBe(
      'Hola "Mundo" & <tag>',
    );
  });

  it('neutraliza Prototype Pollution eliminando __proto__, constructor y prototype', () => {
    const raw = JSON.parse(
      '{"nombre":"Vecino","__proto__":{"isAdmin":true},"constructor":{"prototype":{"pwn":true}},"items":[{"ok":1,"prototype":"bad"}]}',
    ) as Record<string, unknown>;
    const sanitized = sanitizeObject(raw);
    expect(sanitized.nombre).toBe('Vecino');
    expect(Object.prototype.hasOwnProperty.call(sanitized, '__proto__')).toBe(false);
    expect(Object.prototype.hasOwnProperty.call(sanitized, 'constructor')).toBe(false);
    expect(Array.isArray(sanitized.items)).toBe(true);
    expect(sanitizeObject(null)).toBeNull();
    expect(sanitizeObject(42)).toBe(42);
  });

  it('valida redirecciones internas seguras y bloquea Open Redirects incluyendo caracteres de control', () => {
    expect(isSafeRedirectUrl('/dashboard')).toBe(true);
    expect(isSafeRedirectUrl('/finanzas/reportar-pago?recibo=1')).toBe(true);
    expect(isSafeRedirectUrl(null)).toBe(false);
    expect(isSafeRedirectUrl('')).toBe(false);
    expect(isSafeRedirectUrl('https://evil.com')).toBe(false);
    expect(isSafeRedirectUrl('//evil.com')).toBe(false);
    expect(isSafeRedirectUrl('/\\evil.com')).toBe(false);
    expect(isSafeRedirectUrl('/\t/evil.com')).toBe(false);
    expect(isSafeRedirectUrl('/\n/evil.com')).toBe(false);
    expect(isSafeRedirectUrl('/dashboard\r\n')).toBe(false);
    expect(isSafeRedirectUrl('/javascript:alert(1)')).toBe(false);
    expect(isSafeRedirectUrl('/data:text/html,xss')).toBe(false);
    expect(isSafeRedirectUrl('/vbscript:msgbox(1)')).toBe(false);
    expect(isSafeRedirectUrl('/file:///etc/passwd')).toBe(false);
  });

  it('valida URLs de medios seguras (isSafeMediaUrl)', () => {
    expect(isSafeMediaUrl('/api/evidencias/1.avif')).toBe(true);
    expect(isSafeMediaUrl('https://cdn.condominio.local/img.avif')).toBe(true);
    expect(isSafeMediaUrl('http://localhost:9000/bucket/img.png')).toBe(true);
    expect(isSafeMediaUrl('blob:http://localhost/123')).toBe(true);
    expect(isSafeMediaUrl(null)).toBe(false);
    expect(isSafeMediaUrl('   ')).toBe(false);
    expect(isSafeMediaUrl('/\t/evil.png')).toBe(false);
    expect(isSafeMediaUrl('s3://evidencias/pendiente.png')).toBe(false);
    expect(isSafeMediaUrl('javascript:alert(1)')).toBe(false);
    expect(isSafeMediaUrl('data:text/html,<script>1</script>')).toBe(false);
    expect(isSafeMediaUrl('not-a-valid-url')).toBe(false);
  });

  it('valida cuota máxima de 2 MB y tipos MIME permitidos para comprobantes', () => {
    expect(validateProofFileUpload(null)).toEqual({
      valid: false,
      error: 'Debe seleccionar un archivo de comprobante.',
    });
    expect(validateProofFileUpload({ name: 'vacio.png', size: 0, type: 'image/png' })).toEqual({
      valid: false,
      error: 'El archivo seleccionado está vacío.',
    });
    expect(
      validateProofFileUpload({
        name: 'pesado.png',
        size: MAX_UPLOAD_BYTES + 1,
        type: 'image/png',
      }),
    ).toEqual({
      valid: false,
      error: 'El archivo supera el límite máximo permitido de 2 MB.',
    });
    expect(
      validateProofFileUpload({
        name: 'script.exe',
        size: 1024,
        type: 'application/x-msdownload',
      }),
    ).toEqual({
      valid: false,
      error: 'Formato no permitido. Use imágenes (AVIF, WebP, PNG, JPG) o PDF.',
    });
    expect(
      validateProofFileUpload({
        name: 'comprobante.avif',
        size: 150_000,
        type: 'image/avif',
      }),
    ).toEqual({ valid: true });
  });

  it('genera claves de idempotencia con randomUUID y fallback criptográfico getRandomValues (sin Math.random)', () => {
    const key1 = generateIdempotencyKey();
    expect(key1.length).toBeGreaterThan(10);

    const mathSpy = vi.spyOn(Math, 'random');
    const originalRandomUUID = crypto.randomUUID;
    Object.defineProperty(crypto, 'randomUUID', { value: undefined, configurable: true });
    const fallbackKey = generateIdempotencyKey();
    expect(fallbackKey).toMatch(/^idemp-[0-9a-f]{32}$/);
    expect(mathSpy).not.toHaveBeenCalled();

    const originalGetRandomValues = crypto.getRandomValues;
    Object.defineProperty(crypto, 'getRandomValues', { value: undefined, configurable: true });
    expect(() => generateIdempotencyKey()).toThrow(
      'Generador criptográfico (Web Crypto API) no disponible.',
    );
    Object.defineProperty(crypto, 'getRandomValues', {
      value: originalGetRandomValues,
      configurable: true,
    });
    Object.defineProperty(crypto, 'randomUUID', { value: originalRandomUUID, configurable: true });
    mathSpy.mockRestore();
  });

  it('preserva tab y saltos mientras elimina DEL (127) en sanitizeUntrustedText', () => {
    expect(sanitizeUntrustedText('Linea1\tCol2\nLinea2\r\nLinea3\u007fFin')).toBe(
      'Linea1\tCol2\nLinea2\r\nLinea3Fin',
    );
    expect(sanitizeUntrustedText('\u0001\u001f')).toBe('');
  });

  it('acepta espacio (32) y bloquea DEL, no-strings, barras y fallos URL en redirecciones', () => {
    expect(isSafeRedirectUrl('  /dashboard?q=hola mundo  ')).toBe(true);
    expect(isSafeRedirectUrl('/dashboard\u007f')).toBe(false);
    expect(isSafeRedirectUrl(undefined)).toBe(false);
    expect(isSafeRedirectUrl(123 as unknown as string)).toBe(false);
    expect(isSafeRedirectUrl('dashboard')).toBe(false);
    expect(isSafeRedirectUrl('/ruta\\oculta')).toBe(false);
    expect(isSafeRedirectUrl('///evil.com')).toBe(false);
    expect(isSafeRedirectUrl('//condominio.internal/dashboard')).toBe(false);

    vi.stubGlobal(
      'URL',
      class {
        origin = 'https://evil.example';
      },
    );
    expect(isSafeRedirectUrl('/dashboard')).toBe(false);

    vi.stubGlobal(
      'URL',
      class {
        constructor() {
          throw new TypeError('Invalid URL');
        }
      },
    );
    expect(isSafeRedirectUrl('/dashboard')).toBe(false);
    vi.unstubAllGlobals();
  });

  it('valida espacio, DEL, no-strings y trim de rutas relativas en isSafeMediaUrl', () => {
    expect(isSafeMediaUrl('  /api/evidencias/foto 1.avif  ')).toBe(true);
    expect(isSafeMediaUrl('/api/evidencias/bad\u007f.png')).toBe(false);
    expect(isSafeMediaUrl(123 as unknown as string)).toBe(false);
    expect(isSafeMediaUrl(undefined)).toBe(false);
  });

  it('acepta el límite exacto MAX_UPLOAD_BYTES (2 MB), 1 byte y rechaza tamaño negativo', () => {
    expect(
      validateProofFileUpload({
        name: 'exacto.pdf',
        size: MAX_UPLOAD_BYTES,
        type: 'application/pdf',
      }),
    ).toEqual({ valid: true });
    expect(
      validateProofFileUpload({
        name: 'min.jpg',
        size: 1,
        type: 'image/jpeg',
      }),
    ).toEqual({ valid: true });
    expect(
      validateProofFileUpload({
        name: 'neg.png',
        size: -1,
        type: 'image/png',
      }),
    ).toEqual({
      valid: false,
      error: 'El archivo seleccionado está vacío.',
    });
  });

  it('verifica formato UUID, llamada real a getRandomValues y error sin crypto global', () => {
    const uuidSpy = vi.spyOn(crypto, 'randomUUID');
    const uuidKey = generateIdempotencyKey();
    expect(uuidSpy).toHaveBeenCalledTimes(1);
    expect(uuidKey).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);
    uuidSpy.mockRestore();

    const originalRandomUUID = crypto.randomUUID;
    Object.defineProperty(crypto, 'randomUUID', { value: undefined, configurable: true });
    const getRandomSpy = vi.spyOn(crypto, 'getRandomValues');
    try {
      const k1 = generateIdempotencyKey();
      const k2 = generateIdempotencyKey();
      expect(getRandomSpy).toHaveBeenCalledTimes(2);
      expect(k1).toMatch(/^idemp-[0-9a-f]{32}$/);
      expect(k1).not.toBe(`idemp-${'0'.repeat(32)}`);
      expect(k1).not.toBe(k2);
    } finally {
      getRandomSpy.mockRestore();
      Object.defineProperty(crypto, 'randomUUID', {
        value: originalRandomUUID,
        configurable: true,
      });
    }

    vi.stubGlobal('crypto', undefined);
    expect(() => generateIdempotencyKey()).toThrow(
      'Generador criptográfico (Web Crypto API) no disponible.',
    );
  });
});
