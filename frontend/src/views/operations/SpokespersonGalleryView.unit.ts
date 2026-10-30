import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient, ApiError } from '../../services/apiClient';
import SpokespersonGalleryView from './SpokespersonGalleryView.vue';

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ path: '/voceros/galeria' }),
}));

describe('SpokespersonGalleryView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
  });

  it('muestra cuota mensual X/30, permite subir foto y bloquea al alcanzar 30 fotos/mes', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValueOnce({
      periodo: '2026-10',
      fotos_usadas_mes: 29,
      limite_mensual: 30,
      fotos: [],
    });

    vi.spyOn(apiClient, 'post').mockResolvedValueOnce({
      id: 30,
      usuario_id: 4,
      periodo: '2026-10',
      area: 'Cuarto de Bombas',
      comentario: 'Manómetro calibrado en 45 PSI',
      url_foto: 'https://cdn.condominio.local/voceros/evidencia.avif',
    });

    const wrapper = mount(SpokespersonGalleryView);
    await flushPromises();

    expect(wrapper.find('#photo-quota-badge').text()).toContain('29 / 30 fotos');

    await wrapper.find('#input-vocero-area').setValue('Cuarto de Bombas');
    await wrapper.find('#input-vocero-comentario').setValue('Manómetro calibrado en 45 PSI');
    await wrapper
      .find('#input-vocero-url')
      .setValue('https://cdn.condominio.local/voceros/evidencia.avif');
    await wrapper.find('form').trigger('submit.prevent');
    await flushPromises();

    expect(wrapper.text()).toContain('30 / 30 fotos');
    expect(wrapper.text()).toContain('Cuota de 30 Fotos Agotada');

    // Intento adicional con cuota agotada
    await wrapper.find('form').trigger('submit.prevent');
    expect(wrapper.find('.banner--error').text()).toContain('30 fotografías alcanzado');
  });

  it('muestra error del servidor si falla la carga', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValueOnce({
      periodo: '2026-10',
      fotos_usadas_mes: 5,
      limite_mensual: 30,
      fotos: [],
    });
    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(new ApiError(403, 'Rol no autorizado'));

    const wrapper = mount(SpokespersonGalleryView);
    await flushPromises();
    await wrapper.find('#input-vocero-comentario').setValue('Prueba');
    await wrapper.find('form').trigger('submit.prevent');
    await flushPromises();

    expect(wrapper.find('.banner--error').text()).toContain('Rol no autorizado');
  });
});
