import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient, ApiError } from '../../services/apiClient';
import OperationsTasksView from './OperationsTasksView.vue';

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ path: '/operaciones/tareas' }),
}));

describe('OperationsTasksView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
  });

  it('lista tareas del conserje y al completar una vinculada notifica el cierre automático de la incidencia', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValueOnce([
      {
        id: 51,
        plantilla_id: 1,
        incidencia_id: 9,
        titulo: 'Ajustar brazo hidráulico del portón',
        area: 'Acceso Principal',
        fecha: '2026-10-30',
        completada: false,
        url_evidencia: null,
      },
      {
        id: 52,
        plantilla_id: 2,
        incidencia_id: null,
        titulo: 'Desinfectar ascensor par',
        area: 'Torre A',
        fecha: '2026-10-30',
        completada: false,
        url_evidencia: null,
      },
    ]);

    vi.spyOn(apiClient, 'put')
      .mockResolvedValueOnce({
        id: 51,
        plantilla_id: 1,
        incidencia_id: 9,
        titulo: 'Ajustar brazo hidráulico del portón',
        area: 'Acceso Principal',
        fecha: '2026-10-30',
        completada: true,
        url_evidencia: null,
      })
      .mockResolvedValueOnce({
        id: 52,
        plantilla_id: 2,
        incidencia_id: null,
        titulo: 'Desinfectar ascensor par',
        area: 'Torre A',
        fecha: '2026-10-30',
        completada: true,
        url_evidencia: null,
      });

    const wrapper = mount(OperationsTasksView);
    await flushPromises();

    await wrapper.find('#chk-task-51').trigger('change');
    await flushPromises();
    expect(wrapper.text()).toContain('Incidencia vinculada #9 cerrada automáticamente');

    await wrapper.find('#chk-task-52').trigger('change');
    await flushPromises();
    expect(wrapper.text()).toContain('Tarea #52 marcada como completada');

    vi.spyOn(apiClient, 'put').mockRejectedValueOnce(new ApiError(500, 'Fallo al guardar tarea'));
    // Forzar evento directo para cubrir catch
    wrapper.findComponent({ name: 'TaskChecklistItem' }).vm.$emit('complete', 52);
    await flushPromises();
    expect(wrapper.find('.banner--error').exists()).toBe(true);
  });
});
