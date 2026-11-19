import { defineComponent } from 'vue';
import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useDualRefresh } from './useDualRefresh';

function mountDualRefreshHost(fetcher: () => Promise<unknown>, intervalMs = 5_000) {
  let state!: ReturnType<typeof useDualRefresh>;
  const Host = defineComponent({
    setup() {
      state = useDualRefresh(fetcher, intervalMs);
      return state;
    },
    template:
      '<button id="btn-dual-refresh" type="button" @click="triggerRefresh">Refrescar</button>',
  });
  const wrapper = mount(Host);
  return { wrapper, state };
}

describe('useDualRefresh — Polling dual setInterval/clearInterval + refresco manual', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('inicia intervalo periódico en mount, permite refresco manual y ejecuta clearInterval al desmontar', async () => {
    const fetcher = vi.fn().mockResolvedValue(undefined);
    const { wrapper } = mountDualRefreshHost(fetcher, 5_000);
    expect(fetcher).not.toHaveBeenCalled();

    // Avanza timer con documento visible
    await vi.advanceTimersByTimeAsync(5_000);
    await flushPromises();
    expect(fetcher).toHaveBeenCalledTimes(1);

    // Trigger manual ejecuta una nueva sincronización
    await wrapper.find('#btn-dual-refresh').trigger('click');
    await flushPromises();
    expect(fetcher).toHaveBeenCalledTimes(2);

    // Omite tick automático cuando la pestaña está oculta
    const visSpy = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden');
    await vi.advanceTimersByTimeAsync(5_000);
    await flushPromises();
    expect(fetcher).toHaveBeenCalledTimes(2);
    visSpy.mockRestore();

    // Al desmontar limpia el intervalo y no vuelve a disparar
    wrapper.unmount();
    await vi.advanceTimersByTimeAsync(10_000);
    await flushPromises();
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it('mantiene isRefreshing en true y evita ejecuciones concurrentes', async () => {
    let resolveFetch!: () => void;
    const pendingFetch = new Promise<void>((resolve) => {
      resolveFetch = resolve;
    });
    const fetcher = vi.fn().mockReturnValue(pendingFetch);
    const { wrapper, state } = mountDualRefreshHost(fetcher);

    const first = state.triggerRefresh();
    expect(state.isRefreshing.value).toBe(true);

    const second = state.triggerRefresh();
    expect(fetcher).toHaveBeenCalledTimes(1);

    resolveFetch();
    await Promise.all([first, second]);
    expect(state.isRefreshing.value).toBe(false);
    wrapper.unmount();
  });

  it('omite clearInterval sin temporizador y reemplaza intervalo al reiniciar', async () => {
    const clearIntervalSpy = vi.spyOn(globalThis, 'clearInterval');
    const fetcher = vi.fn().mockResolvedValue(undefined);
    const { wrapper, state } = mountDualRefreshHost(fetcher);

    // startPolling() inicial en mount llama stopPolling() con timerId === null
    expect(clearIntervalSpy).not.toHaveBeenCalled();

    // Reiniciar polling limpia el intervalo previo sin duplicar ticks
    state.startPolling();
    expect(clearIntervalSpy).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(5_000);
    await flushPromises();
    expect(fetcher).toHaveBeenCalledTimes(1);

    // Detener una vez limpia; detener de nuevo con timerId === null no llama clearInterval
    state.stopPolling();
    expect(clearIntervalSpy).toHaveBeenCalledTimes(2);
    state.stopPolling();
    expect(clearIntervalSpy).toHaveBeenCalledTimes(2);

    wrapper.unmount();
  });

  it('ejecuta el polling si document es undefined en entorno SSR', async () => {
    const fetcher = vi.fn().mockResolvedValue(undefined);
    const { wrapper } = mountDualRefreshHost(fetcher);

    vi.stubGlobal('document', undefined);
    try {
      vi.advanceTimersByTime(5_000);
    } finally {
      vi.unstubAllGlobals();
    }
    await flushPromises();
    expect(fetcher).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });
});
