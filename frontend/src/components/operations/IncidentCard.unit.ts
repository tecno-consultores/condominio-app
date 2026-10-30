import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import IncidentCard from './IncidentCard.vue';

describe('IncidentCard.vue', () => {
  it('renderiza área, contador de vecinos, badge AVIF y emite adherir al pulsar ¡Me sumo!', async () => {
    const wrapper = mount(IncidentCard, {
      props: {
        incident: {
          id: 14,
          usuario_creador_id: 2,
          area: 'Cuarto de Bombas',
          descripcion: 'Fuga en válvula check principal',
          url_foto: 'https://cdn.condominio.test/inc/14.avif',
          estado: 'ABIERTO',
          adhesiones_count: 6,
        },
      },
    });

    expect(wrapper.text()).toContain('Cuarto de Bombas');
    expect(wrapper.text()).toContain('🔥 6 vecinos');
    expect(wrapper.text()).toContain('Evidencia AVIF optimizada');

    await wrapper.find('.btn-me-sumo').trigger('click');
    expect(wrapper.emitted('adherir')?.[0]).toEqual([14]);
  });

  it('deshabilita el botón ¡Me sumo! cuando la incidencia está CERRADO', () => {
    const wrapper = mount(IncidentCard, {
      props: {
        incident: {
          id: 15,
          usuario_creador_id: 2,
          area: 'Pasillo PB',
          descripcion: 'Luminaria reemplazada',
          url_foto: null,
          estado: 'CERRADO',
          adhesiones_count: 3,
        },
      },
    });

    expect((wrapper.find('.btn-me-sumo').element as HTMLButtonElement).disabled).toBe(true);
  });
});
