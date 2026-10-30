import { beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import AdminStructureView from './AdminStructureView.vue';
import { useOperationsStore } from '../../stores/operationsStore';

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ path: '/admin/estructura' }),
}));

describe('AdminStructureView.vue — Generador de Estructura Física', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('valida campos requeridos y genera estructura anexando las unidades creadas', async () => {
    const store = useOperationsStore();
    vi.spyOn(store, 'fetchAdminData').mockResolvedValue();
    const genSpy = vi.spyOn(store, 'generarEstructura').mockResolvedValue({
      estructura_id: 9,
      nombre: 'Torre Sur',
      tipo: 'TORRE',
      unidades_creadas: 2,
      unidades: [
        { id: 21, identificador: 'Apto S-1', estructura_id: 9 },
        { id: 22, identificador: 'Apto S-2', estructura_id: 9 },
      ],
    });

    const wrapper = mount(AdminStructureView);
    await flushPromises();

    await wrapper.find('#form-generar-estructura').trigger('submit.prevent');
    expect(wrapper.find('#estructura-validation-error').exists()).toBe(true);

    await wrapper.find('#input-est-nombre').setValue('Torre Sur');
    await wrapper.find('#select-est-tipo').setValue('TORRE');
    await wrapper.find('#input-est-identificadores').setValue('Apto S-1, Apto S-2');
    await wrapper.find('#form-generar-estructura').trigger('submit.prevent');
    await flushPromises();

    expect(genSpy).toHaveBeenCalledWith(
      {
        nombre: 'Torre Sur',
        tipo: 'TORRE',
        identificadores: ['Apto S-1', 'Apto S-2'],
      },
      expect.any(String),
    );
    expect(wrapper.find('#estructura-success-banner').text()).toContain('Torre Sur');
  });

  it('muestra banner de caché cuando isStale está activo o falla generarEstructura', async () => {
    const store = useOperationsStore();
    vi.spyOn(store, 'fetchAdminData').mockResolvedValue();
    store.isStale = true;
    store.errorMessage = 'Caché administrativa activa';
    vi.spyOn(store, 'generarEstructura').mockRejectedValue(new Error('Fallo red'));

    const wrapper = mount(AdminStructureView);
    await flushPromises();
    expect(wrapper.find('#estructura-stale-banner').text()).toContain('Caché administrativa');

    await wrapper.find('#input-est-nombre').setValue('Bloque B');
    await wrapper.find('#input-est-identificadores').setValue('PB-1');
    await wrapper.find('#form-generar-estructura').trigger('submit.prevent');
    await flushPromises();
    expect(wrapper.find('#estructura-success-banner').exists()).toBe(false);
  });

  it('valida y actualiza la alícuota y cuota fija de una unidad', async () => {
    const store = useOperationsStore();
    store.data.unidades = [
      {
        id: 1,
        identificador: 'Apto 1-A',
        estructura_id: 1,
        alicuota: '10.0000',
        cuota_fija_usd: null,
      },
    ];
    vi.spyOn(store, 'fetchAdminData').mockResolvedValue();
    const alicuotaSpy = vi.spyOn(store, 'actualizarAlicuotaUnidad').mockResolvedValue({
      id: 1,
      identificador: 'Apto 1-A',
      estructura_id: 1,
      alicuota: '25.0000',
      cuota_fija_usd: '30.00',
    });

    const wrapper = mount(AdminStructureView);
    await flushPromises();

    await wrapper.find('#select-alicuota-unidad').setValue('1');
    await wrapper.find('#input-alicuota-valor').setValue('150');
    await wrapper.find('#form-actualizar-alicuota').trigger('submit.prevent');
    expect(wrapper.find('#estructura-validation-error').text()).toContain('alícuota');

    await wrapper.find('#input-alicuota-valor').setValue('25.0000');
    await wrapper.find('#input-cuota-fija-unidad').setValue('30.00');
    await wrapper.find('#form-actualizar-alicuota').trigger('submit.prevent');
    await flushPromises();
    expect(alicuotaSpy).toHaveBeenCalledOnce();
    expect(wrapper.find('#estructura-success-banner').text()).toContain('Apto 1-A');

    // Actualización con cuota fija vacía y manejo de error de red
    alicuotaSpy.mockResolvedValueOnce({
      id: 1,
      identificador: 'Apto 1-A',
      estructura_id: 1,
    });
    await wrapper.find('#input-cuota-fija-unidad').setValue('');
    await wrapper.find('#form-actualizar-alicuota').trigger('submit.prevent');
    await flushPromises();

    alicuotaSpy.mockRejectedValueOnce(new Error('Fallo red'));
    await wrapper.find('#form-actualizar-alicuota').trigger('submit.prevent');
    await flushPromises();
  });
});
