import { ref, type Ref } from 'vue';
import { generateIdempotencyKey } from '../utils/security';

export interface UseIdempotencyReturn {
  currentKey: Ref<string>;
  isSubmitting: Ref<boolean>;
  rotateKey: () => string;
  executeWithIdempotency: <T>(operation: (key: string) => Promise<T>) => Promise<T>;
}

/**
 * Composable de Idempotencia Nivel 11X:
 * - Genera un Idempotency-Key único al iniciar el formulario.
 * - Bloquea ejecuciones concurrentes mientras `isSubmitting === true`.
 * - Si la operación falla por red/timeout, conserva la MISMA clave para que el reintento
 *   sea deduplicado en KeyDB. Solo rota la clave cuando la operación tiene éxito o el
 *   usuario modifica los datos del formulario (`rotateKey()`).
 */
export function useIdempotency(): UseIdempotencyReturn {
  const currentKey = ref<string>(generateIdempotencyKey());
  const isSubmitting = ref<boolean>(false);

  function rotateKey(): string {
    currentKey.value = generateIdempotencyKey();
    return currentKey.value;
  }

  async function executeWithIdempotency<T>(operation: (key: string) => Promise<T>): Promise<T> {
    if (isSubmitting.value) {
      throw new Error('Operación en curso. Evitando envío duplicado.');
    }
    isSubmitting.value = true;
    try {
      const result = await operation(currentKey.value);
      rotateKey();
      return result;
    } finally {
      isSubmitting.value = false;
    }
  }

  return {
    currentKey,
    isSubmitting,
    rotateKey,
    executeWithIdempotency,
  };
}
