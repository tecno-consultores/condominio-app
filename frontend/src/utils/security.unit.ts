import { describe, expect, it, vi } from 'vitest';
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
});
