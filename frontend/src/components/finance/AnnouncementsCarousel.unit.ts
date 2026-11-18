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

  it('navega entre comunicados y renderiza solo enlaces externos seguros', async () => {
    const wrapper = mount(AnnouncementsCarousel, {
      props: {
        items: [
          {
            id: 1,
            titulo: 'Corte programado & mantenimiento',
            contenido: 'Limpieza de tanque subterráneo.',
            enlace_externo: 'https://condominio.example/acta.pdf',
          },
          {
            id: 2,
            titulo: 'Asamblea Extraordinaria',
            contenido: 'Viernes 7:00 PM en PB.',
            enlace_externo: 'javascript:alert(1)',
          },
        ],
      },
    });

    expect(wrapper.text()).toContain('Corte programado & mantenimiento');
    const link = wrapper.find('#carousel-external-link');
    expect(link.exists()).toBe(true);
    expect(link.attributes('href')).toBe('https://condominio.example/acta.pdf');

    await wrapper.find('#btn-carousel-next').trigger('click');
    expect(wrapper.text()).toContain('Asamblea Extraordinaria');
    expect(wrapper.find('#carousel-external-link').exists()).toBe(false);

    await wrapper.find('#btn-carousel-prev').trigger('click');
    expect(wrapper.text()).toContain('Corte programado & mantenimiento');
  });
});
