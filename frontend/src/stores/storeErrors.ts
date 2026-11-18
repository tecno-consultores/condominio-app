import { ApiError } from '../services/apiClient';
import { useAuthStore } from './authStore';

export interface StoreErrorOptions {
  isGetOperation: boolean;
  hasCachedData: boolean;
  useNativeErrorMessage?: boolean;
}

export interface StoreErrorResolution {
  unauthorized: boolean;
  isStale: boolean;
  message: string;
}

function isClientHttpError(err: unknown): boolean {
  return err instanceof ApiError && err.status >= 400 && err.status < 500;
}

function extractStoreErrorMessage(
  err: unknown,
  fallbackMessage: string,
  useNativeErrorMessage: boolean,
): string {
  if (err instanceof ApiError) {
    return err.detail;
  }
  if (useNativeErrorMessage && err instanceof Error && err.message.trim().length > 0) {
    return err.message;
  }
  return fallbackMessage;
}

export async function resolveStoreError(
  err: unknown,
  fallbackMessage: string,
  options: StoreErrorOptions,
): Promise<StoreErrorResolution> {
  if (err instanceof ApiError && err.status === 401) {
    await useAuthStore().handleUnauthorizedError(err);
    return {
      unauthorized: true,
      isStale: false,
      message: err.detail,
    };
  }

  const shouldMarkStale =
    options.isGetOperation && options.hasCachedData && !isClientHttpError(err);

  return {
    unauthorized: false,
    isStale: shouldMarkStale,
    message: extractStoreErrorMessage(err, fallbackMessage, Boolean(options.useNativeErrorMessage)),
  };
}
