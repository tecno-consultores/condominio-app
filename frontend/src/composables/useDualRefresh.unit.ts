import { defineComponent } from 'vue';
import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useDualRefresh } from './useDualRefresh';

describe('useDualRefresh — Polling dual setInterval/clearInterval + refresco manual', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('inicia intervalo periódico en mount, permite refresco manual y ejecuta clearInterval al desmontar', async () => {
    const fetcher = vi.fn().mockResolvedValue(undefined);
    const Host = defineComponent({
      setup() {
        return useDualRefresh(fetcher, 5_000);
      },
      template:
        '<button id="btn-dual-refresh" type="button" @click="triggerRefresh">Refrescar</button>',
    });

    const wrapper = mount(Host);
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
});
