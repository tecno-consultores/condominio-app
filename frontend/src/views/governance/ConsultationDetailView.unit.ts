import { beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import ConsultationDetailView from './ConsultationDetailView.vue';
import { useAuthStore } from '../../stores/authStore';
import { useGovernanceStore } from '../../stores/governanceStore';
import { useOperationsStore } from '../../stores/operationsStore';

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: '4' } }),
}));

describe('ConsultationDetailView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('carga detalle de consulta, permite emitir voto con recibo modal y cerrar consulta generando acta', async () => {
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

    const opsStore = useOperationsStore();
    opsStore.data.unidades = [
      {
        id: 7,
        identificador: 'A-07',
        estructura_id: 1,
        alicuota: '35.0000',
        cuota_fija_usd: null,
        credito_disponible_usd: '0.00',
      },
    ];

    const govStore = useGovernanceStore();
    const detalleInicial = {
      id: 4,
      titulo: 'Carta Consulta #04: Impermeabilización',
      descripcion_legal: 'Sustento legal Art. 23 LPH',
      tipo_consulta: 'CARTA_CONSULTA_1RA' as const,
      regla_quorum: 'DOS_TERCIOS' as const,
      quorum_minimo_alicuota: '66.6700',
      participacion_alicuota: '35.0000',
      alicuota_aprobatoria: '35.0000',
      total_votos: 1,
      fecha_apertura: '2026-10-01T00:00:00Z',
      fecha_cierre: '2026-10-30T23:59:00Z',
      estado: 'ABIERTA' as const,
      creada_por_id: 1,
      acta_bitacora_id: null,
      ya_voto_usuario: false,
      opciones: [
        {
          id: 10,
          etiqueta: 'APROBAR PRESUPUESTO',
          es_opcion_aprobatoria: true,
          votos_cantidad: 1,
          alicuota_acumulada: '35.0000',
        },
        {
          id: 11,
          etiqueta: 'RECHAZAR',
          es_opcion_aprobatoria: false,
          votos_cantidad: 0,
          alicuota_acumulada: '0.0000',
        },
      ],
      mi_voto: null,
    };

    govStore.consultaActual = detalleInicial;
    vi.spyOn(govStore, 'fetchConsultaDetalle').mockResolvedValue(detalleInicial);

    const reciboMock = {
      voto_id: 22,
      consulta_id: 4,
      titulo_consulta: 'Carta Consulta #04: Impermeabilización',
      unidad_id: 7,
      identificador_unidad: 'A-07',
      usuario_id: 1,
      opcion_id: 10,
      opcion_etiqueta: 'APROBAR PRESUPUESTO',
      alicuota_capturada: '35.0000',
      participacion_total_alicuota: '70.0000',
      quorum_minimo_alicuota: '66.6700',
      fecha_voto: '2026-10-30T12:00:00Z',
      ip_hash: 'a'.repeat(64),
      firma_hmac: 'b'.repeat(64),
      mensaje_verificacion: 'VOTO|v1|4|7|10|35.0000|2026-10-30T12:00:00Z',
    };
    vi.spyOn(govStore, 'votarConsulta').mockImplementation(async () => {
      govStore.ultimoReciboVoto = reciboMock;
      govStore.consultaActual = {
        ...detalleInicial,
        participacion_alicuota: '70.0000',
        ya_voto_usuario: true,
      };
      return reciboMock;
    });

    vi.spyOn(govStore, 'cerrarConsulta').mockImplementation(async () => {
      govStore.consultaActual = {
        ...govStore.consultaActual!,
        estado: 'CERRADA_APROBADA',
        acta_bitacora_id: 91,
      };
      return {
        consulta_id: 4,
        titulo: 'Carta Consulta #04: Impermeabilización',
        estado: 'CERRADA_APROBADA',
        regla_quorum: 'DOS_TERCIOS',
        quorum_minimo_alicuota: '66.6700',
        participacion_alicuota: '70.0000',
        alicuota_aprobatoria: '70.0000',
        total_votos: 2,
        acta_bitacora_id: 91,
        hash_global_escrutinio: 'd'.repeat(64),
      };
    });

    const wrapper = mount(ConsultationDetailView);
    await flushPromises();

    expect(wrapper.find('#quorum-progress-bar').exists()).toBe(true);
    expect(wrapper.findAll('.option-radio-card')).toHaveLength(2);

    await wrapper.find('#radio-opcion-10').setValue();
    await wrapper.find('#select-vote-unidad').setValue('7');
    await wrapper.find('#form-emitir-voto').trigger('submit.prevent');
    await flushPromises();

    expect(govStore.votarConsulta).toHaveBeenCalledWith(4, { unidad_id: 7, opcion_id: 10 });
    expect(wrapper.find('#modal-vote-receipt').exists()).toBe(true);

    await wrapper.find('#btn-close-vote-receipt').trigger('click');
    expect(wrapper.find('#modal-vote-receipt').exists()).toBe(false);

    await wrapper.find('#btn-open-vote-receipt').trigger('click');
    expect(wrapper.find('#modal-vote-receipt').exists()).toBe(true);

    await wrapper.find('#btn-close-consultation').trigger('click');
    await flushPromises();

    expect(govStore.cerrarConsulta).toHaveBeenCalledWith(4);
    expect(wrapper.find('#banner-consulta-cerrada').text()).toContain('CERRADA_APROBADA');
    expect(wrapper.find('#badge-acta-generada').text()).toContain('Bitácora #91');
  });
});
