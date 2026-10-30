import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import AnnouncementsCarousel from './AnnouncementsCarousel.vue';

describe('AnnouncementsCarousel.vue', () => {
  it('renderiza mensaje vacío cuando no existen comunicados', () => {
    const wrapper = mount(AnnouncementsCarousel, {
      props: { items: [] },
    });
    expect(wrapper.text()).toContain('No hay comunicados oficiales publicados hoy.');
  });

  it('navega entre comunicados sanitizando texto dinámico', async () => {
    const wrapper = mount(AnnouncementsCarousel, {
      props: {
        items: [
          { id: 1, titulo: 'Corte programado', contenido: 'Limpieza de tanque subterráneo.' },
          { id: 2, titulo: 'Asamblea Extraordinaria', contenido: 'Viernes 7:00 PM en PB.' },
        ],
      },
    });

    expect(wrapper.text()).toContain('Corte programado');
    await wrapper.find('#btn-carousel-next').trigger('click');
    expect(wrapper.text()).toContain('Asamblea Extraordinaria');
    await wrapper.find('#btn-carousel-prev').trigger('click');
    expect(wrapper.text()).toContain('Corte programado');
  });
});
