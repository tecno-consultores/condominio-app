/**
 * Utilidades de Seguridad Cliente Nivel 11X:
 * - Anti-XSS (escapeHtml, sanitizeUntrustedText, isSafeMediaUrl)
 * - Anti-Prototype Pollution (sanitizeObject)
 * - Anti-Open Redirect (isSafeRedirectUrl)
 * - Cuota de Carga de Archivos <= 2 MB (validateProofFileUpload)
 * - Generación criptográfica de Idempotency-Key (generateIdempotencyKey)
 */

const DANGEROUS_KEYS = new Set(['__proto__', 'constructor', 'prototype']);
const INTERNAL_ORIGIN = 'https://condominio.internal';
const FORBIDDEN_REDIRECT_SCHEMES = ['/javascript:', '/data:', '/vbscript:', '/file:'];
const SAFE_MEDIA_PROTOCOLS = new Set(['https:', 'http:', 'blob:']);

function hasControlChar(value: string): boolean {
  for (const ch of value) {
    const code = ch.charCodeAt(0);
    if (code < 32 || code === 127) {
      return true;
    }
  }
  return false;
}

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
  return Array.from(raw)
    .filter((ch) => {
      const code = ch.charCodeAt(0);
      return code === 9 || code === 10 || code === 13 || (code >= 32 && code !== 127);
    })
    .join('')
    .trim();
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
  if (!target || typeof target !== 'string' || hasControlChar(target)) {
    return false;
  }
  const trimmed = target.trim();
  if (!trimmed.startsWith('/') || trimmed.startsWith('//') || trimmed.includes('\\')) {
    return false;
  }
  const lower = trimmed.toLowerCase();
  if (FORBIDDEN_REDIRECT_SCHEMES.some((prefix) => lower.startsWith(prefix))) {
    return false;
  }
  try {
    return new URL(trimmed, INTERNAL_ORIGIN).origin === INTERNAL_ORIGIN;
  } catch {
    return false;
  }
}

export function isSafeMediaUrl(url: string | null | undefined): boolean {
  if (!url || typeof url !== 'string' || hasControlChar(url)) {
    return false;
  }
  const trimmed = url.trim();
  if (!trimmed) {
    return false;
  }
  if (trimmed.startsWith('/')) {
    return isSafeRedirectUrl(trimmed);
  }
  try {
    const parsed = new URL(trimmed);
    return SAFE_MEDIA_PROTOCOLS.has(parsed.protocol);
  } catch {
    return false;
  }
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
  if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
    return `idemp-${hex}`;
  }
  throw new Error('Generador criptográfico (Web Crypto API) no disponible.');
}
