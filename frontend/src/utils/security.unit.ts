import { describe, expect, it, vi } from 'vitest';
import {
  escapeHtml,
  generateIdempotencyKey,
  isSafeRedirectUrl,
  MAX_UPLOAD_BYTES,
  sanitizeObject,
  sanitizeUntrustedText,
  validateProofFileUpload,
} from './security';

describe('Utilidades de Seguridad Cliente Nivel 11X (security.ts)', () => {
  it('escapa caracteres peligrosos XSS y limpia caracteres de control', () => {
    expect(escapeHtml('<script>alert("xss" & \'1\')</script>')).toBe(
      '&lt;script&gt;alert(&quot;xss&quot; &amp; &#39;1&#39;)&lt;/script&gt;',
    );
    expect(sanitizeUntrustedText('  Hola\u0000\u0007 <b>Mundo</b>  ')).toBe(
      'Hola &lt;b&gt;Mundo&lt;/b&gt;',
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

  it('valida redirecciones internas seguras y bloquea Open Redirects', () => {
    expect(isSafeRedirectUrl('/dashboard')).toBe(true);
    expect(isSafeRedirectUrl('/finanzas/reportar-pago?recibo=1')).toBe(true);
    expect(isSafeRedirectUrl(null)).toBe(false);
    expect(isSafeRedirectUrl('')).toBe(false);
    expect(isSafeRedirectUrl('https://evil.com')).toBe(false);
    expect(isSafeRedirectUrl('//evil.com')).toBe(false);
    expect(isSafeRedirectUrl('/\\evil.com')).toBe(false);
    expect(isSafeRedirectUrl('/javascript:alert(1)')).toBe(false);
    expect(isSafeRedirectUrl('/data:text/html,xss')).toBe(false);
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

  it('genera claves de idempotencia con randomUUID y con fallback determinista', () => {
    const key1 = generateIdempotencyKey();
    expect(key1.length).toBeGreaterThan(10);

    const spy = vi
      .spyOn(crypto, 'randomUUID')
      .mockImplementation((() => undefined) as unknown as typeof crypto.randomUUID);
    const originalRandomUUID = crypto.randomUUID;
    Object.defineProperty(crypto, 'randomUUID', { value: undefined, configurable: true });
    const fallbackKey = generateIdempotencyKey();
    expect(fallbackKey.startsWith('idemp-')).toBe(true);
    Object.defineProperty(crypto, 'randomUUID', { value: originalRandomUUID, configurable: true });
    spy.mockRestore();
  });
});
