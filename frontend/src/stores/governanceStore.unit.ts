import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { useAuthStore } from './authStore';
import {
  useGovernanceStore,
  type CerrarConsultaDTO,
  type ConsultaDetalleDTO,
  type ConsultaResumenDTO,
  type ReciboVotoDTO,
} from './governanceStore';
import * as apiClient from '../services/apiClient';
import * as storeErrors from './storeErrors';

vi.mock('../services/apiClient', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services/apiClient')>();
  return {
    ...actual,
    apiRequest: vi.fn(),
  };
});

vi.mock('./storeErrors', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./storeErrors')>();
  return {
    ...actual,
    resolveStoreError: vi.fn(actual.resolveStoreError),
  };
});

function resolveCheckingLoading<T>(store: { isLoading: boolean }, result: T): () => Promise<T> {
  return async () => {
    expect(store.isLoading).toBe(true);
    return result;
  };
}

function rejectCheckingLoading(store: { isLoading: boolean }, err: unknown): () => Promise<never> {
  return async () => {
    expect(store.isLoading).toBe(true);
    throw err;
  };
}

function buildResumen(overrides: Partial<ConsultaResumenDTO> = {}): ConsultaResumenDTO {
  return {
    id: 1,
    titulo: 'Carta Consulta #01',
    descripcion_legal: 'Descripción legal',
    tipo_consulta: 'CARTA_CONSULTA_1RA',
    regla_quorum: 'DOS_TERCIOS',
    quorum_minimo_alicuota: '66.6700',
    participacion_alicuota: '0.0000',
    alicuota_aprobatoria: '0.0000',
    total_votos: 0,
    fecha_apertura: '2026-10-01T00:00:00Z',
    fecha_cierre: '2026-10-30T23:59:00Z',
    estado: 'ABIERTA',
    creada_por_id: 1,
    acta_bitacora_id: null,
    ya_voto_usuario: false,
    ...overrides,
  };
}

function buildDetalle(overrides: Partial<ConsultaDetalleDTO> = {}): ConsultaDetalleDTO {
  return {
    ...buildResumen(overrides),
    opciones: overrides.opciones ?? [],
    mi_voto: overrides.mi_voto ?? null,
  };
}

function buildRecibo(overrides: Partial<ReciboVotoDTO> = {}): ReciboVotoDTO {
  return {
    voto_id: 12,
    consulta_id: 4,
    titulo_consulta: 'Carta Consulta #04',
    unidad_id: 2,
    identificador_unidad: 'A-02',
    usuario_id: 3,
    opcion_id: 10,
    opcion_etiqueta: 'APROBAR',
    alicuota_capturada: '35.0000',
    participacion_total_alicuota: '60.0000',
    quorum_minimo_alicuota: '66.6700',
    fecha_voto: '2026-10-02T12:00:00Z',
    ip_hash: 'a'.repeat(64),
    firma_hmac: 'f'.repeat(64),
    mensaje_verificacion: 'OK',
    ...overrides,
  };
}

function buildCierre(overrides: Partial<CerrarConsultaDTO> = {}): CerrarConsultaDTO {
  return {
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
    ...overrides,
  };
}

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
    expect(store.consultas[0].titulo).toBe('Carta Consulta <b>#01</b>');
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
    expect(store.isStale).toBe(false);

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

    // HTTP 401 no debe activar isStale=true sino delegar a authStore.handleUnauthorizedError
    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 1,
      nombre: 'Votante',
      cedula: 'V-1',
      correo: 'v@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PROPIETARIO',
    });
    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new apiClient.ApiError(401, 'Expirada'));
    await store.fetchConsultas();
    expect(store.isStale).toBe(false);
    expect(authStore.isAuthenticated).toBe(false);
  });

  it('conserva otras consultas y resiste votar/cerrar cuando consultaActual no coincide o recibo carece jti', async () => {
    const store = useGovernanceStore();
    store.consultas = [
      {
        id: 4,
        titulo: 'Consulta 4',
        descripcion_legal: 'Desc',
        tipo_consulta: 'CARTA_CONSULTA_1RA',
        regla_quorum: 'MAYORIA_SIMPLE',
        quorum_minimo_alicuota: '50.0000',
        participacion_alicuota: '50.0000',
        alicuota_aprobatoria: '50.0000',
        total_votos: 1,
        fecha_apertura: '2026-10-01T00:00:00Z',
        fecha_cierre: '2026-10-30T23:59:00Z',
        estado: 'ABIERTA',
        creada_por_id: 1,
        acta_bitacora_id: null,
        ya_voto_usuario: false,
      },
      {
        id: 99,
        titulo: 'Otra Consulta',
        descripcion_legal: 'Desc 99',
        tipo_consulta: 'CARTA_CONSULTA_1RA',
        regla_quorum: 'DOS_TERCIOS',
        quorum_minimo_alicuota: '66.6700',
        participacion_alicuota: '0.0000',
        alicuota_aprobatoria: '0.0000',
        total_votos: 0,
        fecha_apertura: '2026-10-01T00:00:00Z',
        fecha_cierre: '2026-10-30T23:59:00Z',
        estado: 'ABIERTA',
        creada_por_id: 1,
        acta_bitacora_id: null,
        ya_voto_usuario: false,
      },
    ];
    store.consultaActual = { ...store.consultas[1], opciones: [], mi_voto: null };

    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce({
      voto_id: 50,
      consulta_id: 4,
      titulo_consulta: 'Consulta 4',
      unidad_id: 1,
      identificador_unidad: 'A-1',
      usuario_id: 2,
      opcion_id: 1,
      opcion_etiqueta: 'SI',
      alicuota_capturada: '10.0000',
      participacion_total_alicuota: '10.0000',
      quorum_minimo_alicuota: '50.0000',
      fecha_voto: '2026-10-02T10:00:00Z',
      ip_hash: 'a'.repeat(64),
      firma_hmac: 'b'.repeat(64),
      mensaje_verificacion: 'OK',
    });
    await store.votarConsulta(4, { unidad_id: 1, opcion_id: 1 });
    expect(store.consultaActual?.id).toBe(99);

    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce({
      consulta_id: 4,
      titulo: 'Consulta 4',
      estado: 'CERRADA_APROBADA',
      regla_quorum: 'MAYORIA_SIMPLE',
      quorum_minimo_alicuota: '50.0000',
      participacion_alicuota: '10.0000',
      alicuota_aprobatoria: '10.0000',
      total_votos: 1,
      acta_bitacora_id: 77,
      hash_global_escrutinio: 'c'.repeat(64),
    });
    await store.cerrarConsulta(4);
    expect(store.consultas[0].estado).toBe('CERRADA_APROBADA');
    expect(store.consultas[1].estado).toBe('ABIERTA');
    expect(store.consultaActual?.estado).toBe('ABIERTA');
  });

  it('inicializa estado limpio y resetState restaura banderas isLoading e isStale', () => {
    const store = useGovernanceStore();
    expect(store.consultas).toEqual([]);
    expect(store.consultaActual).toBeNull();
    expect(store.ultimoReciboVoto).toBeNull();
    expect(store.ultimoCierre).toBeNull();
    expect(store.isLoading).toBe(false);
    expect(store.isStale).toBe(false);
    expect(store.error).toBeNull();

    store.consultas = [buildResumen()];
    store.consultaActual = buildDetalle();
    store.ultimoReciboVoto = buildRecibo();
    store.ultimoCierre = buildCierre();
    store.isLoading = true;
    store.isStale = true;
    store.error = 'err';

    store.resetState();
    expect(store.consultas).toEqual([]);
    expect(store.consultaActual).toBeNull();
    expect(store.ultimoReciboVoto).toBeNull();
    expect(store.ultimoCierre).toBeNull();
    expect(store.isLoading).toBe(false);
    expect(store.isStale).toBe(false);
    expect(store.error).toBeNull();
  });

  it('verifica endpoints, isLoading, isStale y sanitización de opciones en fetchConsultas y fetchConsultaDetalle', async () => {
    const store = useGovernanceStore();
    store.isStale = true;
    vi.mocked(apiClient.apiRequest).mockImplementationOnce(
      resolveCheckingLoading(store, [buildResumen({ id: 1 })]),
    );
    await store.fetchConsultas();
    expect(apiClient.apiRequest).toHaveBeenLastCalledWith('/api/consultas');
    expect(store.isLoading).toBe(false);
    expect(store.isStale).toBe(false);

    store.consultas = [];
    vi.mocked(apiClient.apiRequest).mockImplementationOnce(
      rejectCheckingLoading(store, new Error('Sin red')),
    );
    const emptyRes = await store.fetchConsultas();
    expect(emptyRes).toEqual([]);
    expect(store.isStale).toBe(false);
    expect(store.isLoading).toBe(false);
    expect(store.error).toBe('Sin red');

    store.consultas = [buildResumen({ id: 7 })];
    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(
      new apiClient.ApiError(404, 'No hallado'),
    );
    const preserved = await store.fetchConsultas();
    expect(preserved.map((c) => c.id)).toEqual([7]);
    expect(store.isStale).toBe(false);

    store.isStale = true;
    const rawDetalle = buildDetalle({
      id: 4,
      opciones: [
        {
          id: 10,
          etiqueta: '  \u0000APROBAR\u0007  ',
          es_opcion_aprobatoria: true,
          votos_cantidad: 2,
          alicuota_acumulada: '40.0000',
        },
      ],
    });
    vi.mocked(apiClient.apiRequest).mockImplementationOnce(
      resolveCheckingLoading(store, rawDetalle),
    );
    const det = await store.fetchConsultaDetalle(4);
    expect(apiClient.apiRequest).toHaveBeenLastCalledWith('/api/consultas/4');
    expect(store.isLoading).toBe(false);
    expect(store.isStale).toBe(false);
    expect(det.opciones).toEqual([
      {
        id: 10,
        etiqueta: 'APROBAR',
        es_opcion_aprobatoria: true,
        votos_cantidad: 2,
        alicuota_acumulada: '40.0000',
      },
    ]);
    expect(store.consultaActual?.opciones).toEqual(det.opciones);

    vi.mocked(apiClient.apiRequest).mockImplementationOnce(
      rejectCheckingLoading(store, new Error('Red detalle')),
    );
    await expect(store.fetchConsultaDetalle(4)).rejects.toThrow('Red detalle');
    expect(store.isStale).toBe(true);
    expect(store.isLoading).toBe(false);

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('raw-det');
    await expect(store.fetchConsultaDetalle(4)).rejects.toBe('raw-det');
    expect(store.error).toBe('Error al cargar el detalle de la consulta');
    expect(store.isLoading).toBe(false);

    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 1,
      nombre: 'Votante',
      cedula: 'V-1',
      correo: 'v@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PROPIETARIO',
    });
    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new apiClient.ApiError(401, 'Expirada'));
    await expect(store.fetchConsultaDetalle(4)).rejects.toThrow('Expirada');
    expect(store.isStale).toBe(false);
    expect(store.consultaActual).toBeNull();
    expect(store.isLoading).toBe(false);
  });

  it('verifica crearConsulta, deduplicación en lista, errores y defaults de handleStoreError', async () => {
    const store = useGovernanceStore();
    store.consultas = [
      buildResumen({ id: 4, titulo: 'Antigua 4' }),
      buildResumen({ id: 10, titulo: 'Otra 10' }),
    ];
    store.isStale = true;

    const payloadCreate = {
      titulo: 'Nueva 4',
      descripcion_legal: 'Legal',
      tipo_consulta: 'CARTA_CONSULTA_1RA' as const,
      regla_quorum: 'DOS_TERCIOS' as const,
      fecha_cierre: '2026-10-30T23:59:00Z',
      opciones: [{ etiqueta: 'SI', es_opcion_aprobatoria: true }],
    };
    vi.mocked(apiClient.apiRequest).mockImplementationOnce(
      resolveCheckingLoading(store, buildDetalle({ id: 4, titulo: 'Nueva 4' })),
    );
    await store.crearConsulta(payloadCreate, 'idemp-crear-1');
    expect(apiClient.apiRequest).toHaveBeenLastCalledWith('/api/consultas', {
      method: 'POST',
      body: payloadCreate,
      idempotencyKey: 'idemp-crear-1',
    });
    expect(store.consultas.map((c) => c.id)).toEqual([4, 10]);
    expect(store.consultas[0]?.titulo).toBe('Nueva 4');
    expect(store.isStale).toBe(false);
    expect(store.isLoading).toBe(false);

    vi.mocked(storeErrors.resolveStoreError).mockClear();
    vi.mocked(apiClient.apiRequest).mockImplementationOnce(
      rejectCheckingLoading(store, 'raw-create'),
    );
    await expect(store.crearConsulta(payloadCreate, 'idemp-crear-err')).rejects.toBe('raw-create');
    expect(store.error).toBe('Error al convocar la Carta Consulta');
    expect(store.isLoading).toBe(false);
    expect(storeErrors.resolveStoreError).toHaveBeenLastCalledWith(
      'raw-create',
      'Error al convocar la Carta Consulta',
      {
        isGetOperation: false,
        hasCachedData: false,
        useNativeErrorMessage: true,
      },
    );
  });

  it('verifica votarConsulta y cerrarConsulta en bordes de consultaActual, total_votos, jti y errores', async () => {
    const store = useGovernanceStore();
    const votePayload = { unidad_id: 2, opcion_id: 10 };
    store.consultaActual = null;
    store.isStale = true;
    vi.mocked(apiClient.apiRequest).mockImplementationOnce(
      resolveCheckingLoading(store, buildRecibo({ consulta_id: 4, jti: 'jti-0' })),
    );
    await store.votarConsulta(4, votePayload, 'idemp-vote-1');
    expect(apiClient.apiRequest).toHaveBeenLastCalledWith('/api/consultas/4/votar', {
      method: 'POST',
      body: votePayload,
      idempotencyKey: 'idemp-vote-1',
    });
    expect(store.consultaActual).toBeNull();
    expect(store.isStale).toBe(false);
    expect(store.isLoading).toBe(false);

    store.consultaActual = buildDetalle({
      id: 99,
      total_votos: 0,
      ya_voto_usuario: false,
      mi_voto: null,
    });
    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce(buildRecibo({ consulta_id: 4 }));
    await store.votarConsulta(4, votePayload, 'idemp-vote-2');
    expect(store.consultaActual?.id).toBe(99);
    expect(store.consultaActual?.total_votos).toBe(0);
    expect(store.consultaActual?.ya_voto_usuario).toBe(false);
    expect(store.consultaActual?.mi_voto).toBeNull();

    store.consultaActual = buildDetalle({ id: 4, total_votos: 2 });
    const reciboConJti = buildRecibo({
      consulta_id: 4,
      jti: 'jti-xyz',
      voto_id: 12,
      unidad_id: 2,
      identificador_unidad: 'A-02',
      opcion_id: 10,
      opcion_etiqueta: 'APROBAR',
      alicuota_capturada: '35.0000',
      participacion_total_alicuota: '60.0000',
      fecha_voto: '2026-10-02T12:00:00Z',
      firma_hmac: 'f'.repeat(64),
    });
    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce(reciboConJti);
    await store.votarConsulta(4, votePayload, 'idemp-vote-3');
    expect(store.consultaActual?.total_votos).toBe(3);
    expect(store.consultaActual?.mi_voto).toEqual({
      voto_id: 12,
      jti: 'jti-xyz',
      unidad_id: 2,
      identificador_unidad: 'A-02',
      opcion_id: 10,
      opcion_etiqueta: 'APROBAR',
      alicuota_capturada: '35.0000',
      fecha_voto: '2026-10-02T12:00:00Z',
      firma_hmac: 'f'.repeat(64),
    });

    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce(buildRecibo({ consulta_id: 4 }));
    await store.votarConsulta(4, votePayload, 'idemp-vote-4');
    expect(store.consultaActual?.mi_voto?.jti).toBe('');

    vi.mocked(apiClient.apiRequest).mockImplementationOnce(
      rejectCheckingLoading(store, 'raw-vote'),
    );
    await expect(store.votarConsulta(4, votePayload, 'idemp-vote-err')).rejects.toBe('raw-vote');
    expect(store.error).toBe('Error al registrar el voto');
    expect(store.isLoading).toBe(false);

    store.isStale = true;
    store.consultas = [buildResumen({ id: 4 }), buildResumen({ id: 9 })];
    store.consultaActual = buildDetalle({ id: 4 });
    const cierreRes = buildCierre({
      consulta_id: 4,
      estado: 'CERRADA_APROBADA',
      acta_bitacora_id: 88,
    });
    vi.mocked(apiClient.apiRequest).mockImplementationOnce(
      resolveCheckingLoading(store, cierreRes),
    );
    await store.cerrarConsulta(4, 'idemp-close-1');
    expect(apiClient.apiRequest).toHaveBeenLastCalledWith('/api/consultas/4/cerrar', {
      method: 'POST',
      idempotencyKey: 'idemp-close-1',
    });
    expect(store.isStale).toBe(false);
    expect(store.isLoading).toBe(false);
    expect(store.ultimoCierre?.acta_bitacora_id).toBe(88);

    vi.mocked(apiClient.apiRequest).mockImplementationOnce(
      rejectCheckingLoading(store, 'raw-close'),
    );
    await expect(store.cerrarConsulta(4, 'idemp-close-err')).rejects.toBe('raw-close');
    expect(store.error).toBe('Error al cerrar la Carta Consulta');
    expect(store.isLoading).toBe(false);
  });
});
