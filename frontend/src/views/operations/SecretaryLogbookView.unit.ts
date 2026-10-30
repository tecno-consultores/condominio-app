import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient, ApiError } from '../../services/apiClient';
import SecretaryLogbookView from './SecretaryLogbookView.vue';

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ path: '/secretaria/bitacora' }),
}));

describe('SecretaryLogbookView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
  });

  it('lista actas de la bitácora y permite registrar una nueva acta validando longitud mínima', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValueOnce([]);
    vi.spyOn(apiClient, 'post')
      .mockResolvedValueOnce({
        id: 1,
        fecha: '2026-10-30',
        hora: '19:30',
        ubicacion: 'Salón de Usos Múltiples',
        contenido: 'Aprobada contratación de empresa de ascensores.',
        autor_id: 2,
      })
      .mockRejectedValueOnce(new ApiError(403, 'Solo Secretaría o Presidencia'));

    const wrapper = mount(SecretaryLogbookView);
    await flushPromises();
    expect(wrapper.find('.empty-state').exists()).toBe(true);

    // Validación de contenido muy corto
    await wrapper.find('#input-acta-contenido').setValue('abc');
    await wrapper.find('form').trigger('submit.prevent');
    expect(wrapper.find('.banner--error').text()).toContain('al menos 5 caracteres');

    // Registro exitoso
    await wrapper.find('#input-acta-fecha').setValue('2026-10-31');
    await wrapper.find('#input-acta-hora').setValue('20:00');
    await wrapper.find('#input-acta-ubicacion').setValue('Lobby Principal');
    await wrapper
      .find('#input-acta-contenido')
      .setValue('Aprobada contratación de empresa de ascensores.');
    await wrapper.find('form').trigger('submit.prevent');
    await flushPromises();
    expect(wrapper.text()).toContain('Acta oficial registrada');
    expect(wrapper.findAll('.acta-card')).toHaveLength(1);

    // Error del servidor
    await wrapper.find('#input-acta-contenido').setValue('Segunda acta de prueba');
    await wrapper.find('form').trigger('submit.prevent');
    await flushPromises();
    expect(wrapper.find('.banner--error').text()).toContain('Solo Secretaría o Presidencia');
  });
});
