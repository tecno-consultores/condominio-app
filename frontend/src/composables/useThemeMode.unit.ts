// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  THEME_STORAGE_KEY,
  applyThemeToDom,
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
    vi.unstubAllGlobals();
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

  it('detecta preferencia oscura, valida matchMedia y tolera window o matchMedia ausentes', () => {
    currentMatches = true;
    const matchMediaMock = vi.fn((query: string) => ({
      matches: query === '(prefers-color-scheme: dark)' && currentMatches,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      configurable: true,
      value: matchMediaMock,
    });

    initThemeMode();
    const { systemPrefersDark, resolvedTheme } = useThemeMode();
    expect(matchMediaMock).toHaveBeenCalledWith('(prefers-color-scheme: dark)');
    expect(systemPrefersDark.value).toBe(true);
    expect(resolvedTheme.value).toBe('dark');

    // Si matchMedia deja de existir tras haber detectado oscuro, vuelve a false
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      configurable: true,
      value: undefined,
    });
    initThemeMode();
    expect(systemPrefersDark.value).toBe(false);
    expect(resolvedTheme.value).toBe('light');

    // Con listenersRegistered=false y window=undefined (SSR) retorna sin lanzar error
    resetThemeListenersForTests();
    systemPrefersDark.value = true;
    vi.stubGlobal('window', undefined);
    try {
      initThemeMode();
    } finally {
      vi.unstubAllGlobals();
    }
    expect(systemPrefersDark.value).toBe(false);
  });

  it('evita duplicar listeners, sincroniza DOM en eventos y tolera MediaQueryList parcial', () => {
    const addWinSpy = vi.spyOn(window, 'addEventListener');
    let capturedChangeCb: ((e: MediaQueryListEvent) => void) | null = null;
    const addMqlSpy = vi.fn((event: string, cb: (e: MediaQueryListEvent) => void) => {
      if (event === 'change') {
        capturedChangeCb = cb;
      }
    });

    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      configurable: true,
      value: vi.fn((query: string) => ({
        matches: false,
        addEventListener: query === '(prefers-color-scheme: dark)' ? addMqlSpy : undefined,
        removeEventListener: vi.fn(),
      })),
    });

    initThemeMode();
    initThemeMode();

    const storageAdds = addWinSpy.mock.calls.filter(([name]) => name === 'storage');
    expect(storageAdds).toHaveLength(1);
    expect(addMqlSpy).toHaveBeenCalledTimes(1);
    expect(addMqlSpy).toHaveBeenCalledWith('change', expect.any(Function));
    expect(capturedChangeCb).toBeTypeOf('function');

    // Evento storage actualiza clases y meta color-scheme en el DOM
    const { systemPrefersDark, resolvedTheme } = useThemeMode();
    window.localStorage.setItem(THEME_STORAGE_KEY, 'dark');
    window.dispatchEvent(new StorageEvent('storage', { key: THEME_STORAGE_KEY }));
    expect(document.documentElement.classList.contains('theme-dark')).toBe(true);
    expect(document.querySelector('meta[name="color-scheme"]')?.getAttribute('content')).toBe(
      'dark',
    );

    // Al volver a system, handleMediaChange actualiza systemPrefersDark y restaura meta en DOM
    memoryStorage.clear();
    window.dispatchEvent(new StorageEvent('storage', { key: null }));
    document.head.innerHTML = '';
    document.documentElement.classList.add('theme-dark');

    (capturedChangeCb as unknown as (e: MediaQueryListEvent) => void)({
      matches: true,
    } as MediaQueryListEvent);
    expect(systemPrefersDark.value).toBe(true);
    expect(resolvedTheme.value).toBe('dark');
    expect(document.documentElement.classList.contains('theme-dark')).toBe(false);
    expect(document.querySelector('meta[name="color-scheme"]')?.getAttribute('content')).toBe(
      'light dark',
    );

    // MediaQueryList sin addEventListener ni removeEventListener no lanza error
    resetThemeListenersForTests();
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      configurable: true,
      value: vi.fn().mockReturnValue({ matches: false }),
    });
    initThemeMode();
    resetThemeListenersForTests();
  });

  it('limpia listeners, estado y DOM en resetThemeListenersForTests incluso en SSR', () => {
    const removeWinSpy = vi.spyOn(window, 'removeEventListener');
    const removeMqlSpy = vi.fn();
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      configurable: true,
      value: vi.fn().mockReturnValue({
        matches: true,
        addEventListener: vi.fn(),
        removeEventListener: removeMqlSpy,
      }),
    });

    initThemeMode();
    const { themePreference, systemPrefersDark, setThemeMode } = useThemeMode();
    setThemeMode('dark');
    expect(systemPrefersDark.value).toBe(true);
    expect(document.documentElement.classList.contains('theme-dark')).toBe(true);

    resetThemeListenersForTests();
    expect(removeWinSpy).toHaveBeenCalledTimes(1);
    expect(removeWinSpy).toHaveBeenCalledWith('storage', expect.any(Function));
    expect(removeMqlSpy).toHaveBeenCalledTimes(1);
    expect(removeMqlSpy).toHaveBeenCalledWith('change', expect.any(Function));
    expect(themePreference.value).toBe('system');
    expect(systemPrefersDark.value).toBe(false);
    expect(document.documentElement.classList.contains('theme-dark')).toBe(false);
    expect(document.querySelector('meta[name="color-scheme"]')?.getAttribute('content')).toBe(
      'light dark',
    );

    // El listener eliminado no vuelve a reaccionar ante StorageEvent
    window.localStorage.setItem(THEME_STORAGE_KEY, 'dark');
    window.dispatchEvent(new StorageEvent('storage', { key: THEME_STORAGE_KEY }));
    expect(themePreference.value).toBe('system');

    // Segunda invocación sin listeners activos no vuelve a remover ni falla
    removeWinSpy.mockClear();
    removeMqlSpy.mockClear();
    resetThemeListenersForTests();
    expect(removeWinSpy).not.toHaveBeenCalled();
    expect(removeMqlSpy).not.toHaveBeenCalled();

    // Con listeners activos en entorno simulado, reset con window/document undefined no falla
    const fakeRemoveWin = vi.fn();
    vi.stubGlobal('window', {
      addEventListener: vi.fn(),
      removeEventListener: fakeRemoveWin,
      localStorage: memoryStorage,
      matchMedia: vi.fn().mockReturnValue({
        matches: false,
        addEventListener: vi.fn(),
        removeEventListener: removeMqlSpy,
      }),
    });
    initThemeMode();
    vi.stubGlobal('window', undefined);
    vi.stubGlobal('document', undefined);
    try {
      resetThemeListenersForTests();
    } finally {
      vi.unstubAllGlobals();
    }
    expect(fakeRemoveWin).not.toHaveBeenCalled();
    expect(removeMqlSpy).toHaveBeenCalledTimes(1);
  });

  it('maneja document undefined y document.head null de forma segura en applyThemeToDom', () => {
    const { setThemeMode } = useThemeMode();
    setThemeMode('light');

    vi.stubGlobal('document', undefined);
    try {
      applyThemeToDom();
    } finally {
      vi.unstubAllGlobals();
    }

    document.head.innerHTML = '';
    const ownHeadDesc = Object.getOwnPropertyDescriptor(document, 'head');
    Object.defineProperty(document, 'head', { configurable: true, value: null });
    try {
      document.documentElement.className = '';
      setThemeMode('dark');
      expect(document.documentElement.classList.contains('theme-dark')).toBe(true);
    } finally {
      if (ownHeadDesc) {
        Object.defineProperty(document, 'head', ownHeadDesc);
      } else {
        Reflect.deleteProperty(document, 'head');
      }
    }
  });
});
