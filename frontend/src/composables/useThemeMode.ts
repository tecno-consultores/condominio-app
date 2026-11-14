// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

import { computed, ref } from 'vue';

export type ThemePreference = 'system' | 'light' | 'dark';
export type ResolvedTheme = 'light' | 'dark';

export const THEME_STORAGE_KEY = 'condominio_theme_mode';

const themePreference = ref<ThemePreference>('system');
const systemPrefersDark = ref<boolean>(false);

let listenersRegistered = false;

function readStoredPreference(): ThemePreference {
  try {
    const raw = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (raw === 'light' || raw === 'dark') {
      return raw;
    }
    return 'system';
  } catch {
    return 'system';
  }
}

function writeStoredPreference(mode: ThemePreference): void {
  try {
    if (mode === 'system') {
      window.localStorage.removeItem(THEME_STORAGE_KEY);
    } else {
      window.localStorage.setItem(THEME_STORAGE_KEY, mode);
    }
  } catch {
    // Modo privado o almacenamiento bloqueado: mantener solo estado reactivo
  }
}

function detectSystemPrefersDark(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return false;
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

function getOrCreateColorSchemeMeta(): HTMLMetaElement | null {
  if (typeof document === 'undefined' || !document.head) {
    return null;
  }
  let meta = document.querySelector<HTMLMetaElement>('meta[name="color-scheme"]');
  if (!meta) {
    meta = document.createElement('meta');
    meta.name = 'color-scheme';
    document.head.appendChild(meta);
  }
  return meta;
}

export function applyThemeToDom(): void {
  if (typeof document === 'undefined') {
    return;
  }
  const pref = themePreference.value;
  const meta = getOrCreateColorSchemeMeta();
  if (meta) {
    meta.content = pref === 'system' ? 'light dark' : pref;
  }
  const root = document.documentElement;
  root.classList.remove('theme-light', 'theme-dark');
  if (pref === 'light') {
    root.classList.add('theme-light');
  } else if (pref === 'dark') {
    root.classList.add('theme-dark');
  }
}

function handleStorageSync(event: StorageEvent): void {
  if (event.key !== null && event.key !== THEME_STORAGE_KEY) {
    return;
  }
  themePreference.value = readStoredPreference();
  applyThemeToDom();
}

function handleMediaChange(event: MediaQueryListEvent): void {
  // No eliminar la preferencia guardada del usuario al cambiar el sistema operativo
  systemPrefersDark.value = event.matches;
  applyThemeToDom();
}

function ensureGlobalListeners(): void {
  if (listenersRegistered || typeof window === 'undefined') {
    return;
  }
  listenersRegistered = true;
  window.addEventListener('storage', handleStorageSync);
  if (typeof window.matchMedia === 'function') {
    const mql = window.matchMedia('(prefers-color-scheme: dark)');
    if (typeof mql.addEventListener === 'function') {
      mql.addEventListener('change', handleMediaChange);
    }
  }
}

export function resetThemeListenersForTests(): void {
  if (typeof window !== 'undefined' && listenersRegistered) {
    window.removeEventListener('storage', handleStorageSync);
  }
  listenersRegistered = false;
  themePreference.value = 'system';
  systemPrefersDark.value = false;
  applyThemeToDom();
}

export function initThemeMode(): void {
  systemPrefersDark.value = detectSystemPrefersDark();
  themePreference.value = readStoredPreference();
  applyThemeToDom();
  ensureGlobalListeners();
}

export function useThemeMode() {
  const resolvedTheme = computed<ResolvedTheme>(() => {
    if (themePreference.value === 'light' || themePreference.value === 'dark') {
      return themePreference.value;
    }
    return systemPrefersDark.value ? 'dark' : 'light';
  });

  function setThemeMode(mode: ThemePreference): void {
    themePreference.value = mode;
    writeStoredPreference(mode);
    applyThemeToDom();
  }

  function toggleThemeMode(): void {
    const nextTheme: ResolvedTheme = resolvedTheme.value === 'dark' ? 'light' : 'dark';
    const systemTheme: ResolvedTheme = systemPrefersDark.value ? 'dark' : 'light';
    if (nextTheme === systemTheme) {
      setThemeMode('system');
      return;
    }
    setThemeMode(nextTheme);
  }

  return {
    themePreference,
    systemPrefersDark,
    resolvedTheme,
    initThemeMode,
    setThemeMode,
    toggleThemeMode,
  };
}
