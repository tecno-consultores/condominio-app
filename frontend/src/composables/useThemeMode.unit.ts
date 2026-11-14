// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  THEME_STORAGE_KEY,
  initThemeMode,
  resetThemeListenersForTests,
  useThemeMode,
} from './useThemeMode';

function createMemoryStorage(): Storage {
  const store = new Map<string, string>();
  return {
    get length() {
      return store.size;
    },
    clear: () => {
      store.clear();
    },
    getItem: (key: string) => store.get(key) ?? null,
    key: (index: number) => Array.from(store.keys())[index] ?? null,
    removeItem: (key: string) => {
      store.delete(key);
    },
    setItem: (key: string, value: string) => {
      store.set(key, String(value));
    },
  };
}

describe('useThemeMode.ts (Sistema de Temas OKLCH + light-dark)', () => {
  let mediaListener: ((e: MediaQueryListEvent) => void) | null = null;
  let currentMatches = false;
  let memoryStorage: Storage;

  beforeEach(() => {
    memoryStorage = createMemoryStorage();
    Object.defineProperty(window, 'localStorage', {
      writable: true,
      configurable: true,
      value: memoryStorage,
    });
    document.head.innerHTML = '';
    document.documentElement.className = '';
    currentMatches = false;
    mediaListener = null;

    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      configurable: true,
      value: vi.fn().mockImplementation(() => ({
        get matches() {
          return currentMatches;
        },
        addEventListener: (_event: string, cb: (e: MediaQueryListEvent) => void) => {
          mediaListener = cb;
        },
        removeEventListener: vi.fn(),
      })),
    });
    resetThemeListenersForTests();
  });

  afterEach(() => {
    resetThemeListenersForTests();
    vi.restoreAllMocks();
  });

  it('inicializa siguiendo preferencia del sistema y regresa a system al coincidir con el sistema operativo', () => {
    initThemeMode();
    const { themePreference, resolvedTheme, toggleThemeMode } = useThemeMode();

    expect(themePreference.value).toBe('system');
    expect(resolvedTheme.value).toBe('light');
    expect(document.querySelector('meta[name="color-scheme"]')?.getAttribute('content')).toBe(
      'light dark',
    );

    // Primer toggle en sistema claro -> diverge a 'dark' y persiste
    toggleThemeMode();
    expect(themePreference.value).toBe('dark');
    expect(resolvedTheme.value).toBe('dark');
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark');
    expect(document.documentElement.classList.contains('theme-dark')).toBe(true);
    expect(document.querySelector('meta[name="color-scheme"]')?.getAttribute('content')).toBe(
      'dark',
    );

    // Segundo toggle -> vuelve a coincidir con sistema claro -> elimina clave y usa 'system'
    toggleThemeMode();
    expect(themePreference.value).toBe('system');
    expect(resolvedTheme.value).toBe('light');
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBeNull();
    expect(document.documentElement.classList.contains('theme-dark')).toBe(false);
    expect(document.querySelector('meta[name="color-scheme"]')?.getAttribute('content')).toBe(
      'light dark',
    );
  });

  it('inicializa desde localStorage ("light" / "dark") y sincroniza eventos storage y matchMedia sin borrar override', () => {
    currentMatches = true;
    window.localStorage.setItem(THEME_STORAGE_KEY, 'light');

    initThemeMode();
    const { themePreference, resolvedTheme, toggleThemeMode } = useThemeMode();

    expect(themePreference.value).toBe('light');
    expect(resolvedTheme.value).toBe('light');
    expect(document.documentElement.classList.contains('theme-light')).toBe(true);

    // Cambio de matchMedia del sistema operativo NO borra la preferencia explícita guardada
    mediaListener?.({ matches: false } as MediaQueryListEvent);
    expect(themePreference.value).toBe('light');
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe('light');

    // Simular evento storage en otra pestaña
    window.localStorage.setItem(THEME_STORAGE_KEY, 'dark');
    window.dispatchEvent(new StorageEvent('storage', { key: THEME_STORAGE_KEY }));
    expect(themePreference.value).toBe('dark');

    // Evento de otra clave no altera tema
    window.localStorage.setItem(THEME_STORAGE_KEY, 'light');
    window.dispatchEvent(new StorageEvent('storage', { key: 'otra_clave' }));
    expect(themePreference.value).toBe('dark');

    // Evento storage con key === null (clear() en otra pestaña) resetea a system
    memoryStorage.clear();
    window.dispatchEvent(new StorageEvent('storage', { key: null }));
    expect(themePreference.value).toBe('system');

    // Toggle con systemPrefersDark en true y storage previamente fijado
    mediaListener?.({ matches: true } as MediaQueryListEvent);
    expect(resolvedTheme.value).toBe('dark');
    toggleThemeMode();
    expect(themePreference.value).toBe('light');

    // Coincide con oscuro nuevamente -> vuelve a system
    toggleThemeMode();
    expect(themePreference.value).toBe('system');
  });

  it('funciona de forma segura cuando matchMedia falta (JSDOM) o localStorage lanza error', () => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      configurable: true,
      value: undefined,
    });
    const getItemSpy = vi.spyOn(memoryStorage, 'getItem').mockImplementation(() => {
      throw new Error('Storage denied');
    });
    const setItemSpy = vi.spyOn(memoryStorage, 'setItem').mockImplementation(() => {
      throw new Error('Storage denied');
    });

    initThemeMode();
    const { themePreference, setThemeMode } = useThemeMode();
    expect(themePreference.value).toBe('system');

    setThemeMode('dark');
    expect(themePreference.value).toBe('dark');
    expect(getItemSpy).toHaveBeenCalled();
    expect(setItemSpy).toHaveBeenCalled();
  });
});
