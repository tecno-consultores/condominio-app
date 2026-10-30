import { describe, expect, it } from 'vitest';
import { useIdempotency } from './useIdempotency';

describe('Composable useIdempotency', () => {
  it('reutiliza la misma clave ante fallos de red y rota la clave al completarse con éxito', async () => {
    const { currentKey, isSubmitting, executeWithIdempotency, rotateKey } = useIdempotency();
    const initialKey = currentKey.value;
    expect(isSubmitting.value).toBe(false);

    // Simular fallo de red: la clave debe conservarse intacta para el reintento
    await expect(
      executeWithIdempotency(async (key) => {
        expect(key).toBe(initialKey);
        expect(isSubmitting.value).toBe(true);
        throw new Error('Network timeout');
      }),
    ).rejects.toThrow('Network timeout');

    expect(isSubmitting.value).toBe(false);
    expect(currentKey.value).toBe(initialKey);

    // Segundo intento exitoso: usa initialKey y luego rota a una nueva
    const response = await executeWithIdempotency(async (key) => {
      expect(key).toBe(initialKey);
      return 'OK';
    });
    expect(response).toBe('OK');
    expect(currentKey.value).not.toBe(initialKey);

    const beforeManualRotate = currentKey.value;
    const rotated = rotateKey();
    expect(rotated).not.toBe(beforeManualRotate);
  });

  it('bloquea envíos concurrentes mientras isSubmitting es true', async () => {
    const { executeWithIdempotency } = useIdempotency();
    let resolveFirst!: (val: string) => void;
    const firstPromise = executeWithIdempotency(
      () =>
        new Promise<string>((resolve) => {
          resolveFirst = resolve;
        }),
    );

    await expect(executeWithIdempotency(async () => 'second')).rejects.toThrow(
      'Operación en curso. Evitando envío duplicado.',
    );

    resolveFirst('first');
    await expect(firstPromise).resolves.toBe('first');
  });
});
