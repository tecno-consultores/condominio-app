import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { useGovernanceStore } from './governanceStore';
import * as apiClient from '../services/apiClient';

vi.mock('../services/apiClient', () => ({
  apiRequest: vi.fn(),
}));

describe('useGovernanceStore (Cartas Consulta Art. 23 LPH y Catch No Destructivo)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('carga consultas, sanitiza texto y preserva estado previo (isStale=true) ante fallo de red', async () => {
    const store = useGovernanceStore();
    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce([
      {
        id: 1,
        titulo: 'Carta Consulta <b>#01</b>',
        descripcion_legal: 'Impermeabilización Torre A',
        tipo_consulta: 'CARTA_CONSULTA_1RA',
        regla_quorum: 'DOS_TERCIOS',
        quorum_minimo_alicuota: '66.6700',
        participacion_alicuota: '35.0000',
        alicuota_aprobatoria: '35.0000',
        total_votos: 1,
        fecha_apertura: '2026-10-01T00:00:00Z',
        fecha_cierre: '2026-10-30T23:59:00Z',
        estado: 'ABIERTA',
        creada_por_id: 1,
        acta_bitacora_id: null,
        ya_voto_usuario: false,
      },
    ]);

    const res = await store.fetchConsultas();
    expect(res).toHaveLength(1);
    expect(store.consultas[0].titulo).toContain('&lt;b&gt;#01&lt;/b&gt;');
    expect(store.isStale).toBe(false);

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new Error('Fallo de red'));
    const fallback = await store.fetchConsultas();
    expect(fallback).toHaveLength(1);
    expect(store.isStale).toBe(true);
    expect(store.error).toBe('Fallo de red');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('string-err');
    await store.fetchConsultas();
    expect(store.error).toBe('Error al cargar las Cartas Consulta');
  });

  it('crea consulta, obtiene detalle, emite voto firmado y cierra consulta actualizando estado', async () => {
    const store = useGovernanceStore();
    const detalleMock = {
      id: 4,
      titulo: 'Carta Consulta #04',
      descripcion_legal: 'Mantenimiento ascensor',
      tipo_consulta: 'CARTA_CONSULTA_1RA' as const,
      regla_quorum: 'DOS_TERCIOS' as const,
      quorum_minimo_alicuota: '66.6700',
      participacion_alicuota: '0.0000',
      alicuota_aprobatoria: '0.0000',
      total_votos: 0,
      fecha_apertura: '2026-10-01T00:00:00Z',
      fecha_cierre: '2026-10-30T23:59:00Z',
      estado: 'ABIERTA' as const,
      creada_por_id: 1,
      acta_bitacora_id: null,
      ya_voto_usuario: false,
      opciones: [
        {
          id: 10,
          etiqueta: 'APROBAR',
          es_opcion_aprobatoria: true,
          votos_cantidad: 0,
          alicuota_acumulada: '0.0000',
        },
      ],
      mi_voto: null,
    };

    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce(detalleMock);
    const creada = await store.crearConsulta({
      titulo: 'Carta Consulta #04',
      descripcion_legal: 'Mantenimiento ascensor',
      tipo_consulta: 'CARTA_CONSULTA_1RA',
      regla_quorum: 'DOS_TERCIOS',
      fecha_cierre: '2026-10-30T23:59:00Z',
      opciones: [{ etiqueta: 'APROBAR', es_opcion_aprobatoria: true }],
    });
    expect(creada.id).toBe(4);
    expect(store.consultas).toHaveLength(1);

    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce({
      ...detalleMock,
      mi_voto: {
        voto_id: 9,
        unidad_id: 2,
        identificador_unidad: 'A-02',
        opcion_id: 10,
        opcion_etiqueta: 'APROBAR',
        alicuota_capturada: '25.0000',
        fecha_voto: '2026-10-02T12:00:00Z',
        firma_hmac: 'f'.repeat(64),
      },
    });
    const det = await store.fetchConsultaDetalle(4);
    expect(det.mi_voto?.identificador_unidad).toBe('A-02');

    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce({
      voto_id: 12,
      consulta_id: 4,
      titulo_consulta: 'Carta Consulta #04',
      unidad_id: 2,
      identificador_unidad: 'A-02',
      usuario_id: 3,
      opcion_id: 10,
      opcion_etiqueta: 'APROBAR',
      alicuota_capturada: '70.0000',
      participacion_total_alicuota: '70.0000',
      quorum_minimo_alicuota: '66.6700',
      fecha_voto: '2026-10-02T12:00:00Z',
      ip_hash: 'a'.repeat(64),
      firma_hmac: 'b'.repeat(64),
      mensaje_verificacion: 'VOTO|v1|4|2|10|70.0000|2026-10-02T12:00:00Z',
    });
    const recibo = await store.votarConsulta(4, { unidad_id: 2, opcion_id: 10 });
    expect(recibo.voto_id).toBe(12);
    expect(store.consultaActual?.ya_voto_usuario).toBe(true);
    expect(store.consultaActual?.participacion_alicuota).toBe('70.0000');

    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce({
      consulta_id: 4,
      titulo: 'Carta Consulta #04',
      estado: 'CERRADA_APROBADA',
      regla_quorum: 'DOS_TERCIOS',
      quorum_minimo_alicuota: '66.6700',
      participacion_alicuota: '70.0000',
      alicuota_aprobatoria: '70.0000',
      total_votos: 1,
      acta_bitacora_id: 88,
      hash_global_escrutinio: 'c'.repeat(64),
    });
    const cierre = await store.cerrarConsulta(4);
    expect(cierre.estado).toBe('CERRADA_APROBADA');
    expect(store.consultaActual?.acta_bitacora_id).toBe(88);
    expect(store.consultas[0].estado).toBe('CERRADA_APROBADA');
  });

  it('maneja errores en fetchConsultaDetalle, crearConsulta, votarConsulta y cerrarConsulta', async () => {
    const store = useGovernanceStore();

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new Error('err-det-msg'));
    await expect(store.fetchConsultaDetalle(99)).rejects.toThrow('err-det-msg');
    expect(store.error).toBe('err-det-msg');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('err-det');
    await expect(store.fetchConsultaDetalle(99)).rejects.toBe('err-det');
    expect(store.isStale).toBe(true);

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new Error('err-create-msg'));
    await expect(
      store.crearConsulta({
        titulo: 'T',
        descripcion_legal: 'D',
        tipo_consulta: 'CARTA_CONSULTA_1RA',
        regla_quorum: 'DOS_TERCIOS',
        fecha_cierre: '2026-12-31T00:00:00Z',
        opciones: [],
      }),
    ).rejects.toThrow('err-create-msg');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('err-create');
    await expect(
      store.crearConsulta({
        titulo: 'T',
        descripcion_legal: 'D',
        tipo_consulta: 'CARTA_CONSULTA_1RA',
        regla_quorum: 'DOS_TERCIOS',
        fecha_cierre: '2026-12-31T00:00:00Z',
        opciones: [],
      }),
    ).rejects.toBe('err-create');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new Error('err-vote-msg'));
    await expect(store.votarConsulta(1, { unidad_id: 1, opcion_id: 1 })).rejects.toThrow(
      'err-vote-msg',
    );

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('err-vote');
    await expect(store.votarConsulta(1, { unidad_id: 1, opcion_id: 1 })).rejects.toBe('err-vote');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new Error('err-close-msg'));
    await expect(store.cerrarConsulta(1)).rejects.toThrow('err-close-msg');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('err-close');
    await expect(store.cerrarConsulta(1)).rejects.toBe('err-close');
  });
});
