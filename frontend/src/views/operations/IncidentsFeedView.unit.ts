import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient, ApiError } from '../../services/apiClient';
import IncidentsFeedView from './IncidentsFeedView.vue';

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ path: '/incidencias' }),
}));

describe('IncidentsFeedView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
  });

  it('lista incidencias abiertas, permite crear una nueva de forma idempotente y sumarse con ¡Me sumo!', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValueOnce([
      {
        id: 1,
        usuario_creador_id: 2,
        area: 'Ascensores',
        descripcion: 'Botón de PB no ilumina',
        url_foto: null,
        estado: 'ABIERTO',
        adhesiones_count: 2,
      },
    ]);

    vi.spyOn(apiClient, 'post')
      .mockResolvedValueOnce({
        id: 2,
        usuario_creador_id: 3,
        area: 'Bombas de Agua',
        descripcion: 'Presión baja en pisos altos',
        url_foto: null,
        estado: 'ABIERTO',
        adhesiones_count: 1,
      })
      .mockResolvedValueOnce({
        id: 1,
        usuario_creador_id: 2,
        area: 'Ascensores',
        descripcion: 'Botón de PB no ilumina',
        url_foto: null,
        estado: 'ABIERTO',
        adhesiones_count: 3,
      })
      .mockRejectedValueOnce(new ApiError(409, 'Ya te sumaste a esta incidencia.'));

    const wrapper = mount(IncidentsFeedView);
    await flushPromises();

    expect(wrapper.findAll('.incident-card')).toHaveLength(1);

    // Abrir formulario y probar validación corta
    await wrapper.find('#btn-open-new-incident').trigger('click');
    await wrapper.find('#input-inc-descripcion').setValue('abc');
    await wrapper.find('#new-incident-form').trigger('submit.prevent');
    expect(wrapper.find('.banner--error').text()).toContain('al menos 5 caracteres');

    // Crear incidencia válida
    await wrapper.find('#input-inc-area').setValue('Bombas de Agua');
    await wrapper.find('#input-inc-descripcion').setValue('Presión baja en pisos altos');
    await wrapper.find('#new-incident-form').trigger('submit.prevent');
    await flushPromises();
    expect(wrapper.text()).toContain('Incidencia reportada');

    // Adherirse a incidencia
    await wrapper.findAll('.btn-me-sumo')[1]?.trigger('click');
    await flushPromises();
    expect(wrapper.text()).toContain('Te sumaste a la incidencia #1');

    // Error al adherirse dos veces
    await wrapper.findAll('.btn-me-sumo')[0]?.trigger('click');
    await flushPromises();
    expect(wrapper.find('.banner--error').text()).toContain('Ya te sumaste');
  });
});
