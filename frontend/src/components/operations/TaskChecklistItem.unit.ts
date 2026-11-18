import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import TaskChecklistItem from './TaskChecklistItem.vue';

describe('TaskChecklistItem.vue', () => {
  it('renderiza tarea pendiente con incidencia vinculada sin PK cruda y emite complete al marcar casilla', async () => {
    const wrapper = mount(TaskChecklistItem, {
      props: {
        task: {
          id: 31,
          plantilla_id: 1,
          incidencia_id: 14,
          titulo: 'Limpiar filtro de piscina',
          area: 'Área Social',
          fecha: '2026-10-30',
          completada: false,
          url_evidencia: null,
        },
      },
    });

    expect(wrapper.text()).toContain('Limpiar filtro de piscina');
    expect(wrapper.text()).toContain('Vinculada a incidencia vecinal');
    expect(wrapper.text()).toContain('PENDIENTE');

    await wrapper.find('#chk-task-31').trigger('change');
    expect(wrapper.emitted('complete')?.[0]).toEqual([31]);
  });

  it('deshabilita el checkbox cuando ya fue completada o canComplete es false', () => {
    const completedWrapper = mount(TaskChecklistItem, {
      props: {
        task: {
          id: 32,
          plantilla_id: 1,
          incidencia_id: null,
          titulo: 'Barrer estacionamiento sótano 1',
          area: 'Sótano 1',
          fecha: '2026-10-30',
          completada: true,
          url_evidencia: null,
        },
      },
    });
    expect(completedWrapper.text()).toContain('COMPLETADA');
    expect((completedWrapper.find('#chk-task-32').element as HTMLInputElement).disabled).toBe(true);

    const rbacDisabled = mount(TaskChecklistItem, {
      props: {
        canComplete: false,
        task: {
          id: 33,
          plantilla_id: 1,
          incidencia_id: null,
          titulo: 'Revisar bomba',
          area: 'Sótano',
          fecha: '2026-10-30',
          completada: false,
          url_evidencia: null,
        },
      },
    });
    expect((rbacDisabled.find('#chk-task-33').element as HTMLInputElement).disabled).toBe(true);
  });
});
