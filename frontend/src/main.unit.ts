// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

import { vi } from 'vitest';

const appMock = {
  use: vi.fn(),
  mount: vi.fn(),
};
appMock.use.mockReturnValue(appMock);

const createAppMock = vi.fn(() => appMock);
const createPiniaMock = vi.fn(() => ({ __pinia: true }));
const initThemeModeMock = vi.fn();
const buildAppRouterMock = vi.fn(() => ({ __router: true }));

vi.mock('vue', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue')>();
  return {
    ...actual,
    createApp: createAppMock,
  };
});

vi.mock('pinia', async (importOriginal) => {
  const actual = await importOriginal<typeof import('pinia')>();
  return {
    ...actual,
    createPinia: createPiniaMock,
  };
});

vi.mock('./App.vue', () => ({
  default: { name: 'AppStub' },
}));

vi.mock('./composables/useThemeMode', () => ({
  initThemeMode: initThemeModeMock,
}));

vi.mock('./router', () => ({
  buildAppRouter: buildAppRouterMock,
}));

describe('main.ts', () => {
  it('inicializa el tema, registra Pinia/Router y monta la aplicación en #app', async () => {
    vi.resetModules();
    await import('./main');

    expect(initThemeModeMock).toHaveBeenCalledTimes(1);
    expect(createAppMock).toHaveBeenCalledTimes(1);
    expect(createPiniaMock).toHaveBeenCalledTimes(1);
    expect(buildAppRouterMock).toHaveBeenCalledTimes(1);
    expect(appMock.use).toHaveBeenCalledTimes(2);
    expect(appMock.mount).toHaveBeenCalledWith('#app');
  });
});
