import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient, ApiError } from '../../services/apiClient';
import { useAuthStore } from '../../stores/authStore';
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

  it('lista tareas del conserje, respeta RBAC y notifica el cierre automático de incidencia', async () => {
    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 4,
      nombre: 'Pedro Conserje',
      cedula: 'V-4',
      correo: 'conserje@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'CONSERJE',
    });

    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue([
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
    expect(wrapper.find('#directive-tasks-panel').exists()).toBe(false);

    await wrapper.find('#chk-task-51').trigger('change');
    await flushPromises();
    expect(wrapper.text()).toContain('La incidencia vinculada fue cerrada automáticamente');
    expect(wrapper.text()).not.toContain('Tarea #51');

    await wrapper.find('#chk-task-52').trigger('change');
    await flushPromises();
    expect(wrapper.text()).toContain('Tarea marcada como completada');

    vi.spyOn(apiClient, 'put').mockRejectedValueOnce(new ApiError(500, 'Fallo al guardar tarea'));
    wrapper.findComponent({ name: 'TaskChecklistItem' }).vm.$emit('complete', 52);
    await flushPromises();
    expect(wrapper.find('.banner--error').exists()).toBe(true);

    await wrapper.find('#btn-dual-refresh').trigger('click');
    await flushPromises();
    expect(getSpy).toHaveBeenCalledTimes(2);
  });

  it('habilita gestión directiva de plantillas y tareas diarias solo para PRESIDENTE/VICEPRESIDENTE', async () => {
    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 1,
      nombre: 'Presidente',
      cedula: 'V-1',
      correo: 'pres@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PRESIDENTE',
    });

    vi.spyOn(apiClient, 'get').mockResolvedValue([]);
    const postSpy = vi
      .spyOn(apiClient, 'post')
      .mockResolvedValueOnce({
        id: 1,
        titulo: 'Revisión de Bombas',
        area: 'Sala de Máquinas',
        frecuencia: 'DIARIA',
        activa: true,
      })
      .mockResolvedValueOnce({ tareas_generadas: 2 })
      .mockResolvedValueOnce({
        id: 60,
        plantilla_id: null,
        incidencia_id: null,
        titulo: 'Limpiar canaletas',
        area: 'Azotea',
        fecha: '2026-10-30',
        completada: false,
        url_evidencia: null,
      });

    const wrapper = mount(OperationsTasksView);
    await flushPromises();
    expect(wrapper.find('#directive-tasks-panel').exists()).toBe(true);

    await wrapper.find('#input-plantilla-titulo').setValue('Revisión de Bombas');
    await wrapper.find('#input-plantilla-area').setValue('Sala de Máquinas');
    await wrapper.find('#form-crear-plantilla').trigger('submit.prevent');
    await flushPromises();
    expect(postSpy).toHaveBeenCalledWith(
      '/api/tareas/plantillas',
      expect.objectContaining({ titulo: 'Revisión de Bombas' }),
      expect.objectContaining({ idempotencyKey: expect.any(String) }),
    );

    await wrapper.find('#btn-generar-tareas-diarias').trigger('click');
    await flushPromises();
    expect(postSpy).toHaveBeenCalledWith(
      '/api/tareas/generar-diarias',
      {},
      expect.objectContaining({ idempotencyKey: expect.any(String) }),
    );

    await wrapper.find('#input-tarea-titulo').setValue('Limpiar canaletas');
    await wrapper.find('#input-tarea-area').setValue('Azotea');
    await wrapper.find('#form-crear-tarea-diaria').trigger('submit.prevent');
    await flushPromises();
    expect(postSpy).toHaveBeenCalledWith(
      '/api/tareas/diarias',
      expect.objectContaining({ titulo: 'Limpiar canaletas' }),
      expect.objectContaining({ idempotencyKey: expect.any(String) }),
    );
    expect(wrapper.findAll('#chk-task-60')).toHaveLength(1);

    // Validaciones cortas, select frecuencia y captura de errores en acciones directivas
    await wrapper.find('#select-plantilla-frecuencia').setValue('SEMANAL');
    await wrapper.find('#input-plantilla-titulo').setValue('ab');
    await wrapper.find('#form-crear-plantilla').trigger('submit.prevent');
    expect(wrapper.find('.banner--error').text()).toContain('al menos 3 caracteres');

    await wrapper.find('#input-tarea-titulo').setValue('xy');
    await wrapper.find('#form-crear-tarea-diaria').trigger('submit.prevent');
    expect(wrapper.find('.banner--error').text()).toContain('al menos 3 caracteres');

    vi.spyOn(apiClient, 'post')
      .mockRejectedValueOnce(new ApiError(500, 'Error plantilla'))
      .mockRejectedValueOnce(new ApiError(500, 'Error generar'))
      .mockRejectedValueOnce(new ApiError(500, 'Error tarea'));

    await wrapper.find('#input-plantilla-titulo').setValue('Limpieza semanal');
    await wrapper.find('#form-crear-plantilla').trigger('submit.prevent');
    await flushPromises();
    expect(wrapper.find('.banner--error').text()).toContain('Error plantilla');

    await wrapper.find('#btn-generar-tareas-diarias').trigger('click');
    await flushPromises();
    expect(wrapper.find('.banner--error').text()).toContain('Error generar');

    await wrapper.find('#input-tarea-titulo').setValue('Barrer patio');
    await wrapper.find('#form-crear-tarea-diaria').trigger('submit.prevent');
    await flushPromises();
    expect(wrapper.find('.banner--error').text()).toContain('Error tarea');

    // Guard RBAC si un PROPIETARIO dispara evento complete desde TaskChecklistItem
    authStore.setProfileForTesting({
      id: 9,
      nombre: 'Residente',
      cedula: 'V-9',
      correo: 'res@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PROPIETARIO',
    });
    await flushPromises();
    wrapper.findComponent({ name: 'TaskChecklistItem' }).vm.$emit('complete', 60);
    await flushPromises();
    expect(wrapper.find('.banner--error').text()).toContain('Solo Conserjería o Directiva');
  });
});
