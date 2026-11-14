import { beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import ConsultationsListView from './ConsultationsListView.vue';
import { useAuthStore } from '../../stores/authStore';
import { useGovernanceStore } from '../../stores/governanceStore';

const pushMock = vi.fn();
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
}));

describe('ConsultationsListView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    pushMock.mockReset();
  });

  it('muestra listado con barra <progress> de quórum, permite crear consulta a PRESIDENTE y navegar al detalle', async () => {
    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 1,
      nombre: 'Presidente',
      cedula: 'V-1',
      correo: 'pres@test.com',
      telefono: '+584140000000',
      rol: 'PRESIDENTE',
      es_activo: true,
    });

    const govStore = useGovernanceStore();
    vi.spyOn(govStore, 'fetchConsultas').mockResolvedValue([
      {
        id: 4,
        titulo: 'Carta Consulta #04: Impermeabilización',
        descripcion_legal: 'Sustento legal Art. 23 LPH',
        tipo_consulta: 'CARTA_CONSULTA_1RA',
        regla_quorum: 'DOS_TERCIOS',
        quorum_minimo_alicuota: '66.6700',
        participacion_alicuota: '45.0000',
        alicuota_aprobatoria: '45.0000',
        total_votos: 2,
        fecha_apertura: '2026-10-01T00:00:00Z',
        fecha_cierre: '2026-10-30T23:59:00Z',
        estado: 'ABIERTA',
        creada_por_id: 1,
        acta_bitacora_id: null,
        ya_voto_usuario: false,
      },
      {
        id: 6,
        titulo: 'Asamblea #06: Portón Norte',
        descripcion_legal: 'Cierre certificado',
        tipo_consulta: 'CARTA_CONSULTA_2DA',
        regla_quorum: 'MAYORIA_SIMPLE',
        quorum_minimo_alicuota: '50.0100',
        participacion_alicuota: '60.0000',
        alicuota_aprobatoria: '60.0000',
        total_votos: 3,
        fecha_apertura: '2026-09-01T00:00:00Z',
        fecha_cierre: '2026-09-30T23:59:00Z',
        estado: 'CERRADA_APROBADA',
        creada_por_id: 1,
        acta_bitacora_id: 12,
        ya_voto_usuario: true,
      },
    ]);
    govStore.consultas = [
      {
        id: 4,
        titulo: 'Carta Consulta #04: Impermeabilización',
        descripcion_legal: 'Sustento legal Art. 23 LPH',
        tipo_consulta: 'CARTA_CONSULTA_1RA',
        regla_quorum: 'DOS_TERCIOS',
        quorum_minimo_alicuota: '66.6700',
        participacion_alicuota: '45.0000',
        alicuota_aprobatoria: '45.0000',
        total_votos: 2,
        fecha_apertura: '2026-10-01T00:00:00Z',
        fecha_cierre: '2026-10-30T23:59:00Z',
        estado: 'ABIERTA',
        creada_por_id: 1,
        acta_bitacora_id: null,
        ya_voto_usuario: false,
      },
      {
        id: 6,
        titulo: 'Asamblea #06: Portón Norte',
        descripcion_legal: 'Cierre certificado',
        tipo_consulta: 'CARTA_CONSULTA_2DA',
        regla_quorum: 'MAYORIA_SIMPLE',
        quorum_minimo_alicuota: '50.0100',
        participacion_alicuota: '60.0000',
        alicuota_aprobatoria: '60.0000',
        total_votos: 3,
        fecha_apertura: '2026-09-01T00:00:00Z',
        fecha_cierre: '2026-09-30T23:59:00Z',
        estado: 'CERRADA_APROBADA',
        creada_por_id: 1,
        acta_bitacora_id: 12,
        ya_voto_usuario: true,
      },
    ];

    vi.spyOn(govStore, 'crearConsulta').mockResolvedValue({
      ...govStore.consultas[0],
      id: 5,
      titulo: 'Carta Consulta #05: Bombas',
      opciones: [],
      mi_voto: null,
    });

    const wrapper = mount(ConsultationsListView);
    await flushPromises();

    expect(wrapper.find('#form-crear-consulta').exists()).toBe(true);
    expect(wrapper.find('#quorum-progress-bar').exists()).toBe(true);
    expect(wrapper.find('#quorum-progress-bar-6').exists()).toBe(true);
    expect(wrapper.findAll('.consultation-card')).toHaveLength(2);
    expect(wrapper.text()).toContain('✔ Voto de su unidad registrado');

    await wrapper.find('#input-consulta-titulo').setValue('Carta Consulta #05: Bombas');
    await wrapper.find('#select-tipo-consulta').setValue('CARTA_CONSULTA_2DA');
    await wrapper.find('#select-regla-quorum').setValue('MAYORIA_SIMPLE');
    await wrapper.find('#input-fecha-cierre').setValue('2026-12-31T23:59:00Z');
    await wrapper.find('#input-opcion-afirmativa').setValue('APROBAR');
    await wrapper.find('#input-opcion-negativa').setValue('RECHAZAR');
    await wrapper.find('#input-consulta-descripcion').setValue('Descripción legal completa');
    await wrapper.find('#form-crear-consulta').trigger('submit.prevent');
    await flushPromises();

    expect(govStore.crearConsulta).toHaveBeenCalled();
    expect(wrapper.find('#banner-consulta-creada').text()).toContain('Carta Consulta #05: Bombas');

    await wrapper.find('#btn-open-consulta-4').trigger('click');
    expect(pushMock).toHaveBeenCalledWith('/consultas/4');
  });

  it('oculta formulario de creación para PROPIETARIO y muestra estado vacío cuando no hay consultas', async () => {
    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 2,
      nombre: 'Vecino',
      cedula: 'V-2',
      correo: 'vecino@test.com',
      telefono: '+584140000001',
      rol: 'PROPIETARIO',
      es_activo: true,
    });

    const govStore = useGovernanceStore();
    govStore.error = 'No se pudieron sincronizar consultas';
    govStore.isLoading = true;
    vi.spyOn(govStore, 'fetchConsultas').mockResolvedValue([]);

    const wrapper = mount(ConsultationsListView);
    expect(wrapper.find('.banner--error').text()).toContain('No se pudieron sincronizar');
    expect(wrapper.find('[aria-busy="true"]').exists()).toBe(true);

    govStore.isLoading = false;
    await flushPromises();

    expect(wrapper.find('#form-crear-consulta').exists()).toBe(false);
    expect(wrapper.text()).toContain('No existen Cartas Consulta');
  });
});
