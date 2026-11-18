import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient, ApiError } from '../../services/apiClient';
import { useAuthStore } from '../../stores/authStore';
import SpokespersonGalleryView from './SpokespersonGalleryView.vue';

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ path: '/voceros/galeria' }),
}));

describe('SpokespersonGalleryView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
  });

  it('muestra cuota X/30, oculta subida a residentes, renderiza <img> y bloquea en 30 fotos/mes', async () => {
    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 4,
      nombre: 'Luis Vocero',
      cedula: 'V-4',
      correo: 'vocero@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'VOCERO',
    });

    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue({
      periodo: '2026-10',
      fotos_usadas_mes: 29,
      limite_mensual: 30,
      fotos: [],
    });

    const postSpy = vi
      .spyOn(apiClient, 'post')
      .mockResolvedValueOnce({
        url: 'https://cdn.condominio.local/voceros/evidencia.avif',
        mime_origen: 'image/png',
        formato_destino: 'webp',
        bytes_recibidos: 512,
        estado: 'ENCOLADO',
      })
      .mockResolvedValueOnce({
        id: 30,
        usuario_id: 4,
        periodo: '2026-10',
        area: 'Cuarto de Bombas',
        comentario: 'Manómetro calibrado en 45 PSI',
        url_foto: 'https://cdn.condominio.local/voceros/evidencia.avif',
      });

    const wrapper = mount(SpokespersonGalleryView);
    await flushPromises();

    expect(wrapper.find('#photo-quota-badge').text()).toContain('29 / 30 fotos');

    const fileInput = wrapper.find('#input-vocero-archivo');
    const validFile = new File([new Uint8Array(512)], 'inspeccion.png', { type: 'image/png' });
    Object.defineProperty(fileInput.element, 'files', {
      value: [validFile],
      configurable: true,
    });
    await fileInput.trigger('change');

    await wrapper.find('#input-vocero-area').setValue('Cuarto de Bombas');
    await wrapper.find('#input-vocero-comentario').setValue('Manómetro calibrado en 45 PSI');
    await wrapper.find('form').trigger('submit.prevent');
    await flushPromises();

    expect(postSpy).toHaveBeenNthCalledWith(
      1,
      '/api/evidencias/subir?categoria=voceros',
      expect.any(FormData),
      expect.objectContaining({ idempotencyKey: expect.any(String) }),
    );
    expect(wrapper.find('.gallery-card__image').attributes('src')).toBe(
      'https://cdn.condominio.local/voceros/evidencia.avif',
    );
    expect(wrapper.text()).toContain('30 / 30 fotos');
    expect(wrapper.text()).toContain('Cuota de 30 Fotos Agotada');

    // Intento adicional con cuota agotada
    await wrapper.find('form').trigger('submit.prevent');
    expect(wrapper.find('.banner--error').text()).toContain('30 fotografías alcanzado');

    await wrapper.find('#btn-dual-refresh').trigger('click');
    await flushPromises();
    expect(getSpy).toHaveBeenCalledTimes(2);

    // Propietario solo lectura
    authStore.setProfileForTesting({
      id: 2,
      nombre: 'Residente',
      cedula: 'V-2',
      correo: 'res@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PROPIETARIO',
    });
    await flushPromises();
    expect(wrapper.find('.upload-form').exists()).toBe(false);
  });

  it('muestra error del servidor si falla la carga', async () => {
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
    vi.spyOn(apiClient, 'get').mockResolvedValueOnce({
      periodo: '2026-10',
      fotos_usadas_mes: 5,
      limite_mensual: 30,
      fotos: [],
    });
    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(new ApiError(403, 'Rol no autorizado'));

    const wrapper = mount(SpokespersonGalleryView);
    await flushPromises();
    await wrapper.find('#input-vocero-comentario').setValue('Prueba');
    await wrapper
      .find('#input-vocero-url')
      .setValue('https://cdn.condominio.local/voceros/test.avif');
    await wrapper.find('form').trigger('submit.prevent');
    await flushPromises();

    expect(wrapper.find('.banner--error').text()).toContain('Rol no autorizado');
  });

  it('valida archivos inválidos/vacíos, falta de origen y renders s3:// en proceso', async () => {
    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 4,
      nombre: 'Luis Vocero',
      cedula: 'V-4',
      correo: 'vocero@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'VOCERO',
    });

    vi.spyOn(apiClient, 'get').mockResolvedValue({
      periodo: '2026-10',
      fotos_usadas_mes: 1,
      limite_mensual: 30,
      fotos: [
        {
          id: 99,
          usuario_id: 4,
          periodo: '2026-10',
          area: 'Azotea',
          comentario: 'Imagen optimizándose',
          url_foto: 's3://condominio/voceros/99.avif',
        },
      ],
    });

    const wrapper = mount(SpokespersonGalleryView);
    await flushPromises();

    expect(wrapper.find('.gallery-card__processing').exists()).toBe(true);

    // Enviar sin archivo ni URL
    await wrapper.find('#input-vocero-area').setValue('Azotea');
    await wrapper.find('#input-vocero-comentario').setValue('Revisión sin imagen');
    await wrapper.find('form').trigger('submit.prevent');
    expect(wrapper.find('.banner--error').text()).toContain('Selecciona un archivo de imagen');

    // Archivo demasiado grande (> 2 MB) y luego lista de archivos vacía
    const fileInput = wrapper.find('#input-vocero-archivo');
    const badFile = new File([new Uint8Array(2_200_000)], 'pesada.png', { type: 'image/png' });
    Object.defineProperty(fileInput.element, 'files', { value: [badFile], configurable: true });
    await fileInput.trigger('change');
    expect(wrapper.find('.banner--error').exists()).toBe(true);

    Object.defineProperty(fileInput.element, 'files', { value: [], configurable: true });
    await fileInput.trigger('change');
    expect(wrapper.text()).not.toContain('Archivo validado:');
  });
});
