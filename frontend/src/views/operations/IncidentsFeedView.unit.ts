import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient, ApiError } from '../../services/apiClient';
import IncidentsFeedView from './IncidentsFeedView.vue';

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ path: '/incidencias' }),
}));

describe('IncidentsFeedView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
  });

  it('lista incidencias abiertas, sube evidencia opcional, crea nueva falla y suma adhesiones', async () => {
    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue([
      {
        id: 1,
        usuario_creador_id: 2,
        area: 'Ascensores',
        descripcion: 'Botón de PB no ilumina',
        url_foto: null,
        estado: 'ABIERTO',
        adhesiones_count: 2,
      },
    ]);

    const postSpy = vi
      .spyOn(apiClient, 'post')
      .mockResolvedValueOnce({
        url: 's3://condominio/incidencias/foto-1.webp',
        mime_origen: 'image/png',
        formato_destino: 'webp',
        bytes_recibidos: 512,
        estado: 'ENCOLADO',
      })
      .mockResolvedValueOnce({
        id: 2,
        usuario_creador_id: 3,
        area: 'Bombas de Agua',
        descripcion: 'Presión baja en pisos altos',
        url_foto: 's3://condominio/incidencias/foto-1.webp',
        estado: 'ABIERTO',
        adhesiones_count: 1,
      })
      .mockResolvedValueOnce({
        id: 1,
        usuario_creador_id: 2,
        area: 'Ascensores',
        descripcion: 'Botón de PB no ilumina',
        url_foto: null,
        estado: 'ABIERTO',
        adhesiones_count: 3,
      })
      .mockRejectedValueOnce(new ApiError(409, 'Ya te sumaste a esta incidencia.'));

    const wrapper = mount(IncidentsFeedView);
    await flushPromises();

    expect(wrapper.findAll('.incident-card')).toHaveLength(1);

    // Abrir formulario y probar validación corta
    await wrapper.find('#btn-open-new-incident').trigger('click');
    await wrapper.find('#input-inc-descripcion').setValue('abc');
    await wrapper.find('#new-incident-form').trigger('submit.prevent');
    expect(wrapper.find('.banner--error').text()).toContain('al menos 5 caracteres');

    // Adjuntar evidencia válida y crear incidencia
    const fileInput = wrapper.find('#input-inc-evidencia');
    const validFile = new File([new Uint8Array(512)], 'bomba.png', { type: 'image/png' });
    Object.defineProperty(fileInput.element, 'files', {
      value: [validFile],
      configurable: true,
    });
    await fileInput.trigger('change');
    expect(wrapper.text()).toContain('Evidencia validada: bomba.png');

    await wrapper.find('#input-inc-area').setValue('Bombas de Agua');
    await wrapper.find('#input-inc-descripcion').setValue('Presión baja en pisos altos');
    await wrapper.find('#new-incident-form').trigger('submit.prevent');
    await flushPromises();
    expect(postSpy).toHaveBeenNthCalledWith(
      1,
      '/api/evidencias/subir?categoria=incidencias',
      expect.any(FormData),
      expect.objectContaining({ idempotencyKey: expect.any(String) }),
    );
    expect(wrapper.text()).toContain('Incidencia reportada');

    // Adherirse a incidencia
    await wrapper.findAll('.btn-me-sumo')[1]?.trigger('click');
    await flushPromises();
    expect(wrapper.text()).toContain('Te sumaste a la incidencia reportada');
    expect(wrapper.text()).not.toContain('incidencia #1');

    // Error al adherirse dos veces
    await wrapper.findAll('.btn-me-sumo')[0]?.trigger('click');
    await flushPromises();
    expect(wrapper.find('.banner--error').text()).toContain('Ya te sumaste');

    // Refresco manual
    await wrapper.find('#btn-dual-refresh').trigger('click');
    await flushPromises();
    expect(getSpy).toHaveBeenCalledTimes(2);
  });

  it('valida archivos de evidencia inválidos/vacíos y renderiza estado vacío interactivo', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue([]);
    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(new ApiError(500, 'Falla temporal'));

    const wrapper = mount(IncidentsFeedView);
    await flushPromises();

    // Botón de acción del estado vacío abre el formulario
    expect(wrapper.find('.empty-state').exists()).toBe(true);
    await wrapper.find('.empty-state button').trigger('click');
    expect(wrapper.find('#new-incident-form').exists()).toBe(true);

    const fileInput = wrapper.find('#input-inc-evidencia');
    const oversized = new File([new Uint8Array(2_200_000)], 'grande.jpg', { type: 'image/jpeg' });
    Object.defineProperty(fileInput.element, 'files', { value: [oversized], configurable: true });
    await fileInput.trigger('change');
    expect(wrapper.find('.banner--error').exists()).toBe(true);

    Object.defineProperty(fileInput.element, 'files', { value: [], configurable: true });
    await fileInput.trigger('change');

    await wrapper.find('#input-inc-area').setValue('Tanque');
    await wrapper.find('#input-inc-descripcion').setValue('Fuga leve en válvula principal');
    await wrapper.find('#new-incident-form').trigger('submit.prevent');
    await flushPromises();
    expect(wrapper.find('.banner--error').text()).toContain('Falla temporal');
  });
});
