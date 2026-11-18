import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient, ApiError } from '../../services/apiClient';
import { useAuthStore } from '../../stores/authStore';
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

  it('lista actas de bitácora, oculta formularios a PROPIETARIO y permite a SECRETARIO asentar actas y comunicados', async () => {
    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 2,
      nombre: 'Ana Propietaria',
      cedula: 'V-2',
      correo: 'ana@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PROPIETARIO',
    });

    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue([]);
    const readonlyWrapper = mount(SecretaryLogbookView);
    await flushPromises();
    expect(readonlyWrapper.find('.acta-form').exists()).toBe(false);
    expect(readonlyWrapper.find('#form-publicar-comunicado').exists()).toBe(false);

    authStore.setProfileForTesting({
      id: 3,
      nombre: 'Carlos Secretario',
      cedula: 'V-3',
      correo: 'sec@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'SECRETARIO',
    });

    const postSpy = vi
      .spyOn(apiClient, 'post')
      .mockResolvedValueOnce({
        id: 1,
        fecha: '2026-10-30',
        hora: '19:30',
        ubicacion: 'Salón de Usos Múltiples',
        contenido: 'Aprobada contratación de empresa de ascensores.',
        autor_id: 3,
      })
      .mockResolvedValueOnce({
        id: 8,
        titulo: 'Jornada de Fumigación',
        contenido: 'Sábado 8:00 AM en áreas verdes.',
        enlace_externo: '/consultas',
      })
      .mockRejectedValueOnce(new ApiError(403, 'Solo Secretaría o Presidencia'));

    const wrapper = mount(SecretaryLogbookView);
    await flushPromises();
    expect(wrapper.find('.empty-state').exists()).toBe(true);

    // Validación de contenido muy corto
    await wrapper.find('#input-acta-contenido').setValue('abc');
    await wrapper.find('.acta-form').trigger('submit.prevent');
    expect(wrapper.find('.banner--error').text()).toContain('al menos 5 caracteres');

    // Registro exitoso de acta sin exponer Acta #1
    await wrapper.find('#input-acta-fecha').setValue('2026-10-31');
    await wrapper.find('#input-acta-hora').setValue('20:00');
    await wrapper.find('#input-acta-ubicacion').setValue('Lobby Principal');
    await wrapper
      .find('#input-acta-contenido')
      .setValue('Aprobada contratación de empresa de ascensores.');
    await wrapper.find('.acta-form').trigger('submit.prevent');
    await flushPromises();
    expect(wrapper.text()).toContain('Acta oficial registrada');
    expect(wrapper.findAll('.acta-card')).toHaveLength(1);
    expect(wrapper.text()).not.toContain('Acta #1');

    // Publicar comunicado oficial
    await wrapper.find('#input-comunicado-titulo').setValue('Jornada de Fumigación');
    await wrapper.find('#input-comunicado-contenido').setValue('Sábado 8:00 AM en áreas verdes.');
    await wrapper.find('#input-comunicado-enlace').setValue('/consultas');
    await wrapper.find('#form-publicar-comunicado').trigger('submit.prevent');
    await flushPromises();
    expect(postSpy).toHaveBeenCalledWith(
      '/api/comunicados',
      expect.objectContaining({ titulo: 'Jornada de Fumigación', enlace_externo: '/consultas' }),
      expect.objectContaining({ idempotencyKey: expect.any(String) }),
    );
    expect(wrapper.text()).toContain('Comunicado oficial publicado');

    // Error del servidor
    await wrapper.find('#input-acta-contenido').setValue('Segunda acta de prueba');
    await wrapper.find('.acta-form').trigger('submit.prevent');
    await flushPromises();
    expect(wrapper.find('.banner--error').text()).toContain('Solo Secretaría o Presidencia');

    // Validaciones y fallo en publicación de comunicado
    await wrapper.find('#input-comunicado-titulo').setValue('ab');
    await wrapper.find('#form-publicar-comunicado').trigger('submit.prevent');
    expect(wrapper.find('.banner--error').text()).toContain('Indica un título');

    await wrapper.find('#input-comunicado-titulo').setValue('Aviso Corte de Agua');
    await wrapper.find('#input-comunicado-contenido').setValue('Mantenimiento general el viernes.');
    await wrapper.find('#input-comunicado-enlace').setValue('http://inseguro.example/test');
    await wrapper.find('#form-publicar-comunicado').trigger('submit.prevent');
    expect(wrapper.find('.banner--error').text()).toContain('URL HTTPS segura');

    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(new ApiError(500, 'Error comunicado'));
    await wrapper.find('#input-comunicado-enlace').setValue('https://condominio.local/aviso');
    await wrapper.find('#form-publicar-comunicado').trigger('submit.prevent');
    await flushPromises();
    expect(wrapper.find('.banner--error').text()).toContain('Error comunicado');

    await wrapper.find('#btn-dual-refresh').trigger('click');
    await flushPromises();
    expect(getSpy.mock.calls.length).toBeGreaterThanOrEqual(4);
  });
});
