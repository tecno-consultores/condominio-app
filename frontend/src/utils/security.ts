/**
 * Utilidades de Seguridad Cliente Nivel 11X:
 * - Anti-XSS (escapeHtml, sanitizeUntrustedText)
 * - Anti-Prototype Pollution (sanitizeObject)
 * - Anti-Open Redirect (isSafeRedirectUrl)
 * - Cuota de Carga de Archivos <= 2 MB (validateProofFileUpload)
 * - Generación criptográfica de Idempotency-Key (generateIdempotencyKey)
 */

const DANGEROUS_KEYS = new Set(['__proto__', 'constructor', 'prototype']);

export const MAX_UPLOAD_BYTES = 2 * 1024 * 1024; // 2 MB
export const ALLOWED_PROOF_MIME_TYPES = new Set([
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/avif',
  'application/pdf',
]);

export interface FileValidationResult {
  valid: boolean;
  error?: string;
}

export interface UploadableFileLike {
  name: string;
  size: number;
  type: string;
}

export function escapeHtml(raw: string): string {
  return raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function sanitizeUntrustedText(raw: string): string {
  const withoutControls = Array.from(raw)
    .filter((ch) => {
      const code = ch.charCodeAt(0);
      return code === 9 || code === 10 || code === 13 || (code >= 32 && code !== 127);
    })
    .join('')
    .trim();
  return escapeHtml(withoutControls);
}

export function sanitizeObject<T>(input: T): T {
  if (input === null || typeof input !== 'object') {
    return input;
  }
  if (Array.isArray(input)) {
    return input.map((item) => sanitizeObject(item)) as unknown as T;
  }
  const cleanObj = Object.create(null) as Record<string, unknown>;
  for (const [key, value] of Object.entries(input as Record<string, unknown>)) {
    if (DANGEROUS_KEYS.has(key)) {
      continue;
    }
    cleanObj[key] = sanitizeObject(value);
  }
  return cleanObj as T;
}

export function isSafeRedirectUrl(target: string | null | undefined): boolean {
  if (!target || typeof target !== 'string') {
    return false;
  }
  const trimmed = target.trim();
  if (!trimmed.startsWith('/') || trimmed.startsWith('//') || trimmed.includes('\\')) {
    return false;
  }
  const lower = trimmed.toLowerCase();
  return !lower.startsWith('/javascript:') && !lower.startsWith('/data:');
}

export function validateProofFileUpload(
  file: UploadableFileLike | null | undefined,
): FileValidationResult {
  if (!file) {
    return { valid: false, error: 'Debe seleccionar un archivo de comprobante.' };
  }
  if (file.size <= 0) {
    return { valid: false, error: 'El archivo seleccionado está vacío.' };
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return {
      valid: false,
      error: 'El archivo supera el límite máximo permitido de 2 MB.',
    };
  }
  if (!ALLOWED_PROOF_MIME_TYPES.has(file.type)) {
    return {
      valid: false,
      error: 'Formato no permitido. Use imágenes (AVIF, WebP, PNG, JPG) o PDF.',
    };
  }
  return { valid: true };
}

export function generateIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `idemp-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
}
