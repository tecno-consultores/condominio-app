import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import TaskChecklistItem from './TaskChecklistItem.vue';

describe('TaskChecklistItem.vue', () => {
  it('renderiza tarea pendiente con incidencia vinculada y emite complete al marcar casilla', async () => {
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
    expect(wrapper.text()).toContain('Cierra Incidencia #14');
    expect(wrapper.text()).toContain('PENDIENTE');

    await wrapper.find('#chk-task-31').trigger('change');
    expect(wrapper.emitted('complete')?.[0]).toEqual([31]);
  });

  it('muestra estado COMPLETADA y deshabilita el checkbox cuando ya fue ejecutada', () => {
    const wrapper = mount(TaskChecklistItem, {
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

    expect(wrapper.text()).toContain('COMPLETADA');
    expect((wrapper.find('#chk-task-32').element as HTMLInputElement).disabled).toBe(true);
  });
});
