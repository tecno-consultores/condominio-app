import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import IncidentCard from './IncidentCard.vue';

describe('IncidentCard.vue', () => {
  it('renderiza imagen segura, área, contador de vecinos y emite adherir al pulsar ¡Me sumo!', async () => {
    const wrapper = mount(IncidentCard, {
      props: {
        incident: {
          id: 14,
          usuario_creador_id: 2,
          area: 'Cuarto de Bombas & Hidroneumático',
          descripcion: 'Fuga en válvula check principal',
          url_foto: 'https://cdn.condominio.test/inc/14.avif',
          estado: 'ABIERTO',
          adhesiones_count: 6,
        },
      },
    });

    expect(wrapper.text()).toContain('Cuarto de Bombas & Hidroneumático');
    expect(wrapper.text()).toContain('🔥 6 vecinos');
    expect(wrapper.text()).toContain('Evidencia fotográfica adjunta');
    const img = wrapper.find('img.incident-card__img');
    expect(img.exists()).toBe(true);
    expect(img.attributes('src')).toBe('https://cdn.condominio.test/inc/14.avif');

    await wrapper.find('.btn-me-sumo').trigger('click');
    expect(wrapper.emitted('adherir')?.[0]).toEqual([14]);
  });

  it('muestra aviso de procesamiento AVIF si URI es s3:// y deshabilita botón cuando está CERRADO', () => {
    const wrapper = mount(IncidentCard, {
      props: {
        incident: {
          id: 15,
          usuario_creador_id: 2,
          area: 'Pasillo PB',
          descripcion: 'Luminaria reemplazada',
          url_foto: 's3://condominio/incidencias/15.png',
          estado: 'CERRADO',
          adhesiones_count: 3,
        },
      },
    });

    expect(wrapper.find('img.incident-card__img').exists()).toBe(false);
    expect(wrapper.text()).toContain('Evidencia AVIF en procesamiento');
    expect((wrapper.find('.btn-me-sumo').element as HTMLButtonElement).disabled).toBe(true);
  });
});
