import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import {
  useAccessAmenitiesStore,
  type AreaSocialDTO,
  type PaqueteDTO,
  type PaseVisitaDTO,
  type ReservaAreaDTO,
  type VerificarPaseQRResponseDTO,
} from './accessAmenitiesStore';
import { useAuthStore } from './authStore';
import * as apiClient from '../services/apiClient';
import * as storeErrors from './storeErrors';

vi.mock('../services/apiClient', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services/apiClient')>();
  return {
    ...actual,
    apiRequest: vi.fn(),
    apiClient: {
      ...actual.apiClient,
      delete: vi.fn(),
    },
  };
});

vi.mock('./storeErrors', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./storeErrors')>();
  return {
    ...actual,
    resolveStoreError: vi.fn((...args: Parameters<typeof actual.resolveStoreError>) =>
      actual.resolveStoreError(...args),
    ),
  };
});

function createDeferred<T>(): { promise: Promise<T>; resolve: (value: T) => void } {
  let resolveFn: (value: T) => void = () => undefined;
  const promise = new Promise<T>((resolve) => {
    resolveFn = resolve;
  });
  return { promise, resolve: resolveFn };
}

function makePase(overrides: Partial<PaseVisitaDTO> = {}): PaseVisitaDTO {
  return {
    id: 1,
    jti: 'jti-001',
    unidad_id: 1,
    identificador_unidad: 'PB-01',
    creado_por_id: 2,
    nombre_visitante: 'Carlos Visitante',
    cedula_visitante: 'V-19888777',
    placa_vehiculo: null,
    modalidad: 'UNICO_USO',
    valido_desde: '2026-10-30T10:00:00Z',
    valido_hasta: '2026-10-31T10:00:00Z',
    estado: 'ACTIVO',
    usado_en: null,
    verificado_por_id: null,
    firma_hmac: 'a'.repeat(64),
    qr_token: 'payload.sig',
    ...overrides,
  };
}

function makeVerifyResponse(
  overrides: Partial<VerificarPaseQRResponseDTO> = {},
): VerificarPaseQRResponseDTO {
  return {
    autorizado: true,
    pase_id: 6,
    jti: 'jti-006',
    unidad_id: 1,
    identificador_unidad: '1-A',
    nombre_visitante: 'Técnico Fibra',
    cedula_visitante: 'V-15000111',
    placa_vehiculo: 'XYZ-999',
    modalidad: 'UNICO_USO',
    estado: 'USADO',
    usado_en: '2026-10-30T12:00:00Z',
    verificado_por_id: 5,
    mensaje: 'Acceso autorizado',
    ...overrides,
  };
}

function makePaquete(overrides: Partial<PaqueteDTO> = {}): PaqueteDTO {
  return {
    id: 12,
    unidad_id: 1,
    identificador_unidad: '2-B',
    recibido_por_id: 5,
    empresa_envio: 'ZOOM',
    descripcion: 'Caja mediana',
    url_foto_evidencia: null,
    estado: 'EN_GARITA',
    fecha_recepcion: '2026-10-30T10:00:00Z',
    fecha_entrega: null,
    retirado_por_id: null,
    ...overrides,
  };
}

function makeAreaSocial(overrides: Partial<AreaSocialDTO> = {}): AreaSocialDTO {
  return {
    id: 1,
    nombre: 'Salón de Fiestas',
    aforo_maximo: 80,
    costo_uso_usd: '35.00',
    deposito_garantia_usd: '100.00',
    requiere_solvencia_estricta: true,
    es_activa: true,
    ...overrides,
  };
}

function makeReserva(overrides: Partial<ReservaAreaDTO> = {}): ReservaAreaDTO {
  return {
    id: 10,
    area_id: 1,
    nombre_area: 'Salón de Fiestas',
    unidad_id: 2,
    identificador_unidad: 'PB-02',
    solicitante_id: 4,
    fecha_evento: '2026-12-20',
    motivo_evento: 'Cumpleaños infantil',
    estado: 'CONFIRMADA',
    tarea_inspeccion_id: 99,
    observaciones_inspeccion: null,
    creado_en: '2026-10-30T10:00:00Z',
    ...overrides,
  };
}

describe('useAccessAmenitiesStore (Pases QR HMAC-SHA256, Anti-Replay y Paquetería)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('carga pases de visita, sanitiza campos y preserva estado (isStale=true) ante fallo de red', async () => {
    const store = useAccessAmenitiesStore();
    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce([
      {
        id: 1,
        jti: 'jti-001',
        unidad_id: 1,
        identificador_unidad: 'PB-01',
        creado_por_id: 2,
        nombre_visitante: 'Carlos <b>Visitante</b>',
        cedula_visitante: 'V-19888777',
        placa_vehiculo: 'AB123CD',
        modalidad: 'UNICO_USO',
        valido_desde: '2026-10-30T10:00:00Z',
        valido_hasta: '2026-10-31T10:00:00Z',
        estado: 'ACTIVO',
        usado_en: null,
        verificado_por_id: null,
        firma_hmac: 'a'.repeat(64),
        qr_token: 'payload.sig',
      },
    ]);

    const pases = await store.fetchMisPases();
    expect(pases).toHaveLength(1);
    expect(store.pases[0].nombre_visitante).toBe('Carlos <b>Visitante</b>');
    expect(store.isStale).toBe(false);

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new Error('Fallo de red pases'));
    const fallback = await store.fetchMisPases();
    expect(fallback).toHaveLength(1);
    expect(store.isStale).toBe(true);
    expect(store.error).toBe('Fallo de red pases');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('raw-err');
    await store.fetchMisPases();
    expect(store.error).toBe('Error al cargar los pases de visita QR');
  });

  it('emite pase QR, revoca pase y verifica token en garita', async () => {
    const store = useAccessAmenitiesStore();
    const paseMock = {
      id: 5,
      jti: 'jti-005',
      unidad_id: 1,
      identificador_unidad: '1-A',
      creado_por_id: 2,
      nombre_visitante: 'Ana López',
      cedula_visitante: 'V-20111222',
      placa_vehiculo: null,
      modalidad: 'UNICO_USO' as const,
      valido_desde: '2026-10-30T10:00:00Z',
      valido_hasta: '2026-10-31T10:00:00Z',
      estado: 'ACTIVO' as const,
      usado_en: null,
      verificado_por_id: null,
      firma_hmac: 'b'.repeat(64),
      qr_token: 'b64.sig',
    };

    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce(paseMock);
    const creado = await store.crearPaseVisita({
      unidad_id: 1,
      nombre_visitante: 'Ana López',
      cedula_visitante: 'V-20111222',
      modalidad: 'UNICO_USO',
      horas_validez: 24,
    });
    expect(creado.id).toBe(5);
    expect(store.ultimoPaseCreado?.id).toBe(5);

    vi.mocked(apiClient.apiClient.delete).mockResolvedValueOnce({
      ...paseMock,
      estado: 'REVOCADO',
    });
    const revocado = await store.revocarPaseVisita(5);
    expect(revocado.estado).toBe('REVOCADO');
    expect(store.pases[0].estado).toBe('REVOCADO');
    expect(store.ultimoPaseCreado?.estado).toBe('REVOCADO');

    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce({
      autorizado: true,
      pase_id: 6,
      jti: 'jti-006',
      unidad_id: 1,
      identificador_unidad: '1-A',
      nombre_visitante: 'Técnico Fibra',
      cedula_visitante: 'V-15000111',
      placa_vehiculo: 'XYZ-999',
      modalidad: 'UNICO_USO',
      estado: 'USADO',
      usado_en: '2026-10-30T12:00:00Z',
      verificado_por_id: 5,
      mensaje: 'Acceso autorizado a Unidad 1-A',
    });
    const scan = await store.verificarPaseQR('b64.sig');
    expect(scan.autorizado).toBe(true);
    expect(store.ultimoEscaneo?.placa_vehiculo).toBe('XYZ-999');

    // Escaneo sin placa
    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce({
      autorizado: true,
      pase_id: 7,
      jti: 'jti-007',
      unidad_id: 1,
      identificador_unidad: '1-A',
      nombre_visitante: 'Peatón',
      cedula_visitante: 'V-15000222',
      placa_vehiculo: null,
      modalidad: 'UNICO_USO',
      estado: 'USADO',
      usado_en: '2026-10-30T12:05:00Z',
      verificado_por_id: 5,
      mensaje: 'Acceso peatonal autorizado',
    });
    const scanPeaton = await store.verificarPaseQR('b64_peaton.sig');
    expect(scanPeaton.placa_vehiculo).toBeNull();
  });

  it('gestiona paquetería (fetchPaqueteria, registrarPaquete, confirmarEntregaPaquete) y errores', async () => {
    const store = useAccessAmenitiesStore();
    const paqueteMock = {
      id: 12,
      unidad_id: 1,
      identificador_unidad: '2-B',
      recibido_por_id: 5,
      empresa_envio: 'ZOOM',
      descripcion: 'Caja mediana',
      url_foto_evidencia: null,
      estado: 'EN_GARITA' as const,
      fecha_recepcion: '2026-10-30T10:00:00Z',
      fecha_entrega: null,
      retirado_por_id: null,
    };

    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce([paqueteMock]);
    const lista = await store.fetchPaqueteria();
    expect(lista).toHaveLength(1);

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new Error('Err red paq'));
    const fallback = await store.fetchPaqueteria();
    expect(fallback).toHaveLength(1);
    expect(store.isStale).toBe(true);

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('raw-paq');
    await store.fetchPaqueteria();
    expect(store.error).toBe('Error al cargar la paquetería en garita');

    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce(paqueteMock);
    const reg = await store.registrarPaquete({
      unidad_id: 1,
      empresa_envio: 'ZOOM',
      descripcion: 'Caja mediana',
    });
    expect(reg.id).toBe(12);

    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce({
      ...paqueteMock,
      estado: 'ENTREGADO',
      fecha_entrega: '2026-10-30T14:00:00Z',
      retirado_por_id: 2,
    });
    const ent = await store.confirmarEntregaPaquete(12);
    expect(ent.estado).toBe('ENTREGADO');
    expect(store.paquetes[0].estado).toBe('ENTREGADO');

    // Errores en mutaciones
    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new Error('err-crear-pase'));
    await expect(
      store.crearPaseVisita({
        unidad_id: 1,
        nombre_visitante: 'X',
        cedula_visitante: 'V-1',
        modalidad: 'UNICO_USO',
        horas_validez: 12,
      }),
    ).rejects.toThrow('err-crear-pase');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('raw-crear-pase');
    await expect(
      store.crearPaseVisita({
        unidad_id: 1,
        nombre_visitante: 'X',
        cedula_visitante: 'V-1',
        modalidad: 'UNICO_USO',
        horas_validez: 12,
      }),
    ).rejects.toBe('raw-crear-pase');

    vi.mocked(apiClient.apiClient.delete).mockRejectedValueOnce(new Error('err-revocar'));
    await expect(store.revocarPaseVisita(1)).rejects.toThrow('err-revocar');
    expect(store.isStale).toBe(false);

    vi.mocked(apiClient.apiClient.delete).mockRejectedValueOnce('raw-revocar');
    await expect(store.revocarPaseVisita(1)).rejects.toBe('raw-revocar');
    expect(store.isStale).toBe(false);

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new Error('err-scan'));
    await expect(store.verificarPaseQR('bad.sig')).rejects.toThrow('err-scan');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('raw-scan');
    await expect(store.verificarPaseQR('bad.sig')).rejects.toBe('raw-scan');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new Error('err-reg-paq'));
    await expect(
      store.registrarPaquete({ unidad_id: 1, empresa_envio: 'MRW', descripcion: 'Sobre' }),
    ).rejects.toThrow('err-reg-paq');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('raw-reg-paq');
    await expect(
      store.registrarPaquete({ unidad_id: 1, empresa_envio: 'MRW', descripcion: 'Sobre' }),
    ).rejects.toBe('raw-reg-paq');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new Error('err-ent-paq'));
    await expect(store.confirmarEntregaPaquete(12)).rejects.toThrow('err-ent-paq');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('raw-ent-paq');
    await expect(store.confirmarEntregaPaquete(12)).rejects.toBe('raw-ent-paq');
  });

  it('gestiona áreas sociales, reservas con solvencia e inspección post-evento (Hito 13)', async () => {
    const store = useAccessAmenitiesStore();
    const areaMock = {
      id: 1,
      nombre: 'Salón de <b>Fiestas</b>',
      aforo_maximo: 80,
      costo_uso_usd: '35.00',
      deposito_garantia_usd: '100.00',
      requiere_solvencia_estricta: true,
      es_activa: true,
    };

    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce([areaMock]);
    const areas = await store.fetchAreasSociales();
    expect(areas).toHaveLength(1);
    expect(store.areasSociales[0].nombre).toBe('Salón de <b>Fiestas</b>');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new Error('Err areas'));
    const areasFallback = await store.fetchAreasSociales();
    expect(areasFallback).toHaveLength(1);
    expect(store.isStale).toBe(true);

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('raw-areas');
    await store.fetchAreasSociales();
    expect(store.error).toBe('Error al cargar las áreas sociales');

    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce(areaMock);
    const creada = await store.crearAreaSocial({
      nombre: 'Salón de Fiestas',
      aforo_maximo: 80,
      costo_uso_usd: '35.00',
      deposito_garantia_usd: '100.00',
      requiere_solvencia_estricta: true,
    });
    expect(creada.id).toBe(1);

    const reservaMock = {
      id: 10,
      area_id: 1,
      nombre_area: 'Salón de Fiestas',
      unidad_id: 2,
      identificador_unidad: 'PB-02',
      solicitante_id: 4,
      fecha_evento: '2026-12-20',
      motivo_evento: 'Cumpleaños <i>infantil</i>',
      estado: 'CONFIRMADA' as const,
      tarea_inspeccion_id: 99,
      observaciones_inspeccion: null,
      creado_en: '2026-10-30T10:00:00Z',
    };

    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce([reservaMock]);
    const reservas = await store.fetchReservas();
    expect(reservas).toHaveLength(1);
    expect(store.reservas[0].motivo_evento).toBe('Cumpleaños <i>infantil</i>');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new Error('Err reservas'));
    await store.fetchReservas();
    expect(store.isStale).toBe(true);

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('raw-reservas');
    await store.fetchReservas();
    expect(store.error).toBe('Error al cargar el calendario de reservas');

    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce(reservaMock);
    const solicitada = await store.solicitarReservaArea({
      area_id: 1,
      unidad_id: 2,
      fecha_evento: '2026-12-20',
      motivo_evento: 'Cumpleaños infantil',
    });
    expect(solicitada.id).toBe(10);

    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce({
      ...reservaMock,
      estado: 'FINALIZADA_SIN_DANOS',
      observaciones_inspeccion: 'Entrega limpia y sin daños',
    });
    const inspeccionada = await store.inspeccionarReserva(10, {
      estado: 'FINALIZADA_SIN_DANOS',
      observaciones_inspeccion: 'Entrega limpia y sin daños',
    });
    expect(inspeccionada.estado).toBe('FINALIZADA_SIN_DANOS');
    expect(store.reservas[0].observaciones_inspeccion).toBe('Entrega limpia y sin daños');

    // Errores en mutaciones Hito 13
    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new Error('err-crear-area'));
    await expect(
      store.crearAreaSocial({
        nombre: 'X',
        aforo_maximo: 10,
        costo_uso_usd: '0.00',
        deposito_garantia_usd: '0.00',
        requiere_solvencia_estricta: true,
      }),
    ).rejects.toThrow('err-crear-area');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('raw-crear-area');
    await expect(
      store.crearAreaSocial({
        nombre: 'X',
        aforo_maximo: 10,
        costo_uso_usd: '0.00',
        deposito_garantia_usd: '0.00',
        requiere_solvencia_estricta: true,
      }),
    ).rejects.toBe('raw-crear-area');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new Error('err-solicitar-reserva'));
    await expect(
      store.solicitarReservaArea({
        area_id: 1,
        unidad_id: 2,
        fecha_evento: '2026-12-20',
        motivo_evento: 'Evento',
      }),
    ).rejects.toThrow('err-solicitar-reserva');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('raw-solicitar-reserva');
    await expect(
      store.solicitarReservaArea({
        area_id: 1,
        unidad_id: 2,
        fecha_evento: '2026-12-20',
        motivo_evento: 'Evento',
      }),
    ).rejects.toBe('raw-solicitar-reserva');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new Error('err-inspeccion'));
    await expect(
      store.inspeccionarReserva(10, {
        estado: 'FINALIZADA_CON_DANOS',
        observaciones_inspeccion: 'Daño',
      }),
    ).rejects.toThrow('err-inspeccion');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('raw-inspeccion');
    await expect(
      store.inspeccionarReserva(10, {
        estado: 'FINALIZADA_CON_DANOS',
        observaciones_inspeccion: 'Daño',
      }),
    ).rejects.toBe('raw-inspeccion');

    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce({
      ...reservaMock,
      estado: 'CANCELADA',
    });
    const cancelada = await store.cancelarReserva(10, 'idem-cancel-001');
    expect(cancelada.estado).toBe('CANCELADA');
    expect(store.reservas[0].estado).toBe('CANCELADA');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new Error('err-cancelar'));
    await expect(store.cancelarReserva(10)).rejects.toThrow('err-cancelar');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('raw-cancelar');
    await expect(store.cancelarReserva(10)).rejects.toBe('raw-cancelar');

    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 2,
      nombre: 'Residente QR',
      cedula: 'V-2',
      correo: 'qr@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PROPIETARIO',
    });
    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new apiClient.ApiError(401, 'Expirada'));
    await store.fetchMisPases();
    expect(store.isStale).toBe(false);
    expect(authStore.isAuthenticated).toBe(false);
  });

  it('conserva elementos no modificados al actualizar mapas de pases, paquetes y reservas', async () => {
    const store = useAccessAmenitiesStore();
    const otroPase = {
      id: 901,
      jti: 'jti-901',
      unidad_id: 2,
      identificador_unidad: '2-B',
      creado_por_id: 2,
      nombre_visitante: 'Otro',
      cedula_visitante: 'V-901',
      placa_vehiculo: null,
      modalidad: 'UNICO_USO' as const,
      valido_desde: '2026-10-30T10:00:00Z',
      valido_hasta: '2026-10-31T10:00:00Z',
      estado: 'ACTIVO' as const,
      usado_en: null,
      verificado_por_id: null,
      firma_hmac: 'a'.repeat(64),
      qr_token: 'otro.sig',
    };
    const otroPaq = {
      id: 902,
      unidad_id: 2,
      identificador_unidad: '2-B',
      recibido_por_id: 5,
      empresa_envio: 'MRW',
      descripcion: 'Sobre',
      url_foto_evidencia: null,
      estado: 'EN_GARITA' as const,
      fecha_recepcion: '2026-10-30T10:00:00Z',
      fecha_entrega: null,
      retirado_por_id: null,
    };
    const otraReserva = {
      id: 903,
      area_id: 1,
      nombre_area: 'Salón',
      unidad_id: 2,
      identificador_unidad: '2-B',
      solicitante_id: 4,
      fecha_evento: '2026-12-25',
      motivo_evento: 'Cena',
      estado: 'CONFIRMADA' as const,
      tarea_inspeccion_id: null,
      observaciones_inspeccion: null,
      creado_en: '2026-10-30T10:00:00Z',
    };

    store.pases = [{ ...otroPase, id: 10 }, otroPase];
    store.ultimoPaseCreado = otroPase;
    store.paquetes = [{ ...otroPaq, id: 20 }, otroPaq];
    store.reservas = [{ ...otraReserva, id: 30 }, otraReserva];

    vi.mocked(apiClient.apiClient.delete).mockResolvedValueOnce({
      ...otroPase,
      id: 10,
      estado: 'REVOCADO',
    });
    await store.revocarPaseVisita(10);
    expect(store.pases[1].estado).toBe('ACTIVO');
    expect(store.ultimoPaseCreado?.estado).toBe('ACTIVO');

    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce({
      ...otroPaq,
      id: 20,
      estado: 'ENTREGADO',
    });
    await store.confirmarEntregaPaquete(20);
    expect(store.paquetes[1].estado).toBe('EN_GARITA');

    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce({
      ...otraReserva,
      id: 30,
      estado: 'FINALIZADA_SIN_DANOS',
    });
    await store.inspeccionarReserva(30, {
      estado: 'FINALIZADA_SIN_DANOS',
      observaciones_inspeccion: 'OK',
    });
    expect(store.reservas[1].estado).toBe('CONFIRMADA');

    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce({
      ...otraReserva,
      id: 30,
      estado: 'CANCELADA',
    });
    await store.cancelarReserva(30);
    expect(store.reservas[1].estado).toBe('CONFIRMADA');
  });

  it('inicializa estado limpio y resetState restaura todas las colecciones y banderas', () => {
    const store = useAccessAmenitiesStore();

    expect(store.pases).toEqual([]);
    expect(store.ultimoPaseCreado).toBeNull();
    expect(store.ultimoEscaneo).toBeNull();
    expect(store.paquetes).toEqual([]);
    expect(store.areasSociales).toEqual([]);
    expect(store.reservas).toEqual([]);
    expect(store.isLoading).toBe(false);
    expect(store.isStale).toBe(false);
    expect(store.error).toBeNull();

    store.pases = [makePase()];
    store.ultimoPaseCreado = makePase();
    store.ultimoEscaneo = makeVerifyResponse();
    store.paquetes = [makePaquete()];
    store.areasSociales = [makeAreaSocial()];
    store.reservas = [makeReserva()];
    store.isLoading = true;
    store.isStale = true;
    store.error = 'Error previo';

    store.resetState();

    expect(store.pases).toEqual([]);
    expect(store.ultimoPaseCreado).toBeNull();
    expect(store.ultimoEscaneo).toBeNull();
    expect(store.paquetes).toEqual([]);
    expect(store.areasSociales).toEqual([]);
    expect(store.reservas).toEqual([]);
    expect(store.isLoading).toBe(false);
    expect(store.isStale).toBe(false);
    expect(store.error).toBeNull();
  });

  it('verifica endpoints GET, ciclo isLoading/isStale y caché vacía en pases y paquetería', async () => {
    const store = useAccessAmenitiesStore();

    store.isStale = true;
    const deferredPases = createDeferred<PaseVisitaDTO[]>();
    vi.mocked(apiClient.apiRequest).mockReturnValueOnce(deferredPases.promise);
    const pasesReq = store.fetchMisPases();
    expect(store.isLoading).toBe(true);
    deferredPases.resolve([makePase()]);
    await pasesReq;
    expect(store.isLoading).toBe(false);
    expect(store.isStale).toBe(false);
    expect(apiClient.apiRequest).toHaveBeenLastCalledWith('/api/accesos/pases/mios');

    store.pases = [];
    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new Error('Sin red pases vacío'));
    const emptyPases = await store.fetchMisPases();
    expect(emptyPases).toEqual([]);
    expect(store.isStale).toBe(false);
    expect(store.isLoading).toBe(false);
    expect(storeErrors.resolveStoreError).toHaveBeenLastCalledWith(
      expect.any(Error),
      'Error al cargar los pases de visita QR',
      { isGetOperation: true, hasCachedData: false, useNativeErrorMessage: true },
    );

    store.isStale = true;
    const deferredPaquetes = createDeferred<PaqueteDTO[]>();
    vi.mocked(apiClient.apiRequest).mockReturnValueOnce(deferredPaquetes.promise);
    const paqReq = store.fetchPaqueteria();
    expect(store.isLoading).toBe(true);
    deferredPaquetes.resolve([makePaquete()]);
    await paqReq;
    expect(store.isLoading).toBe(false);
    expect(store.isStale).toBe(false);
    expect(apiClient.apiRequest).toHaveBeenLastCalledWith('/api/paqueteria');

    store.paquetes = [];
    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new Error('Sin red paquetería vacío'));
    const emptyPaq = await store.fetchPaqueteria();
    expect(emptyPaq).toEqual([]);
    expect(store.isStale).toBe(false);
    expect(store.isLoading).toBe(false);
  });

  it('verifica endpoints GET, ciclo isLoading/isStale y caché vacía en áreas sociales y reservas', async () => {
    const store = useAccessAmenitiesStore();

    store.isStale = true;
    const deferredAreas = createDeferred<AreaSocialDTO[]>();
    vi.mocked(apiClient.apiRequest).mockReturnValueOnce(deferredAreas.promise);
    const areasReq = store.fetchAreasSociales();
    expect(store.isLoading).toBe(true);
    deferredAreas.resolve([makeAreaSocial()]);
    await areasReq;
    expect(store.isLoading).toBe(false);
    expect(store.isStale).toBe(false);
    expect(apiClient.apiRequest).toHaveBeenLastCalledWith('/api/reservas/areas');

    store.areasSociales = [];
    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new Error('Sin red áreas vacío'));
    const emptyAreas = await store.fetchAreasSociales();
    expect(emptyAreas).toEqual([]);
    expect(store.isStale).toBe(false);
    expect(store.isLoading).toBe(false);

    store.isStale = true;
    const deferredReservas = createDeferred<ReservaAreaDTO[]>();
    vi.mocked(apiClient.apiRequest).mockReturnValueOnce(deferredReservas.promise);
    const reservasReq = store.fetchReservas();
    expect(store.isLoading).toBe(true);
    deferredReservas.resolve([makeReserva()]);
    await reservasReq;
    expect(store.isLoading).toBe(false);
    expect(store.isStale).toBe(false);
    expect(apiClient.apiRequest).toHaveBeenLastCalledWith('/api/reservas');

    store.reservas = [];
    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new Error('Sin red reservas vacío'));
    const emptyReservas = await store.fetchReservas();
    expect(emptyReservas).toEqual([]);
    expect(store.isStale).toBe(false);
    expect(store.isLoading).toBe(false);
  });

  it('verifica endpoints, deduplicación, trim, isLoading, isStale y errores fallback en pases QR', async () => {
    const store = useAccessAmenitiesStore();
    store.pases = [
      makePase({ id: 5, nombre_visitante: 'Previo' }),
      makePase({ id: 99, nombre_visitante: 'Conservado' }),
    ];

    const payloadPase = {
      unidad_id: 1,
      nombre_visitante: 'Ana Nueva',
      cedula_visitante: 'V-20111222',
      modalidad: 'UNICO_USO' as const,
      horas_validez: 24,
    };
    store.isStale = true;
    const deferredCrear = createDeferred<PaseVisitaDTO>();
    vi.mocked(apiClient.apiRequest).mockReturnValueOnce(deferredCrear.promise);
    const crearReq = store.crearPaseVisita(payloadPase, 'idem-pase-5');
    expect(store.isLoading).toBe(true);
    deferredCrear.resolve(makePase({ id: 5, nombre_visitante: 'Ana Nueva' }));
    await crearReq;
    expect(store.isLoading).toBe(false);
    expect(store.isStale).toBe(false);
    expect(apiClient.apiRequest).toHaveBeenLastCalledWith('/api/accesos/pases', {
      method: 'POST',
      body: payloadPase,
      idempotencyKey: 'idem-pase-5',
    });
    expect(store.pases.map((p) => p.id)).toEqual([5, 99]);
    expect(store.pases[0].nombre_visitante).toBe('Ana Nueva');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('raw-crear-pase');
    await expect(store.crearPaseVisita(payloadPase)).rejects.toBe('raw-crear-pase');
    expect(store.error).toBe('Error al emitir el pase de visita QR');
    expect(store.isLoading).toBe(false);
    expect(storeErrors.resolveStoreError).toHaveBeenLastCalledWith(
      'raw-crear-pase',
      'Error al emitir el pase de visita QR',
      { isGetOperation: false, hasCachedData: false, useNativeErrorMessage: true },
    );

    store.isStale = true;
    const deferredRevocar = createDeferred<PaseVisitaDTO>();
    vi.mocked(apiClient.apiClient.delete).mockReturnValueOnce(deferredRevocar.promise);
    const revocarReq = store.revocarPaseVisita(5, 'idem-rev-5');
    expect(store.isLoading).toBe(true);
    deferredRevocar.resolve(makePase({ id: 5, estado: 'REVOCADO' }));
    await revocarReq;
    expect(store.isLoading).toBe(false);
    expect(store.isStale).toBe(false);
    expect(apiClient.apiClient.delete).toHaveBeenLastCalledWith('/api/accesos/pases/5', {
      idempotencyKey: 'idem-rev-5',
    });

    vi.mocked(apiClient.apiClient.delete).mockRejectedValueOnce('raw-revocar');
    await expect(store.revocarPaseVisita(5)).rejects.toBe('raw-revocar');
    expect(store.error).toBe('Error al revocar el pase de visita');
    expect(store.isLoading).toBe(false);

    store.isStale = true;
    const deferredVerificar = createDeferred<VerificarPaseQRResponseDTO>();
    vi.mocked(apiClient.apiRequest).mockReturnValueOnce(deferredVerificar.promise);
    const verificarReq = store.verificarPaseQR('  qr-token-123.sig  ', 'idem-qr-1');
    expect(store.isLoading).toBe(true);
    deferredVerificar.resolve(makeVerifyResponse());
    await verificarReq;
    expect(store.isLoading).toBe(false);
    expect(store.isStale).toBe(false);
    expect(apiClient.apiRequest).toHaveBeenLastCalledWith('/api/accesos/verificar-qr', {
      method: 'POST',
      body: { qr_token: 'qr-token-123.sig' },
      idempotencyKey: 'idem-qr-1',
    });

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('raw-scan');
    await expect(store.verificarPaseQR('bad.sig')).rejects.toBe('raw-scan');
    expect(store.error).toBe('Error al verificar el código QR');
    expect(store.isLoading).toBe(false);
  });

  it('verifica endpoints, deduplicación, isLoading, isStale y errores fallback en paquetería', async () => {
    const store = useAccessAmenitiesStore();
    store.paquetes = [
      makePaquete({ id: 12, descripcion: 'Antigua' }),
      makePaquete({ id: 88, descripcion: 'Conservada' }),
    ];

    const payloadPaq = {
      unidad_id: 1,
      empresa_envio: 'ZOOM',
      descripcion: 'Caja actualizada',
    };
    store.isStale = true;
    const deferredReg = createDeferred<PaqueteDTO>();
    vi.mocked(apiClient.apiRequest).mockReturnValueOnce(deferredReg.promise);
    const regReq = store.registrarPaquete(payloadPaq, 'idem-paq-12');
    expect(store.isLoading).toBe(true);
    deferredReg.resolve(makePaquete({ id: 12, descripcion: 'Caja actualizada' }));
    await regReq;
    expect(store.isLoading).toBe(false);
    expect(store.isStale).toBe(false);
    expect(apiClient.apiRequest).toHaveBeenLastCalledWith('/api/paqueteria/registrar', {
      method: 'POST',
      body: payloadPaq,
      idempotencyKey: 'idem-paq-12',
    });
    expect(store.paquetes.map((p) => p.id)).toEqual([12, 88]);
    expect(store.paquetes[0].descripcion).toBe('Caja actualizada');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('raw-reg-paq');
    await expect(store.registrarPaquete(payloadPaq)).rejects.toBe('raw-reg-paq');
    expect(store.error).toBe('Error al registrar la encomienda en garita');
    expect(store.isLoading).toBe(false);

    store.isStale = true;
    const deferredEnt = createDeferred<PaqueteDTO>();
    vi.mocked(apiClient.apiRequest).mockReturnValueOnce(deferredEnt.promise);
    const entReq = store.confirmarEntregaPaquete(12, 'idem-ent-12');
    expect(store.isLoading).toBe(true);
    deferredEnt.resolve(makePaquete({ id: 12, estado: 'ENTREGADO' }));
    await entReq;
    expect(store.isLoading).toBe(false);
    expect(store.isStale).toBe(false);
    expect(apiClient.apiRequest).toHaveBeenLastCalledWith('/api/paqueteria/12/entregar', {
      method: 'PUT',
      idempotencyKey: 'idem-ent-12',
    });

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('raw-ent-paq');
    await expect(store.confirmarEntregaPaquete(12)).rejects.toBe('raw-ent-paq');
    expect(store.error).toBe('Error al confirmar la entrega del paquete');
    expect(store.isLoading).toBe(false);
  });

  it('verifica endpoints, deduplicación, isLoading, isStale y fallbacks al crear área y solicitar reserva', async () => {
    const store = useAccessAmenitiesStore();
    store.areasSociales = [
      makeAreaSocial({ id: 1, nombre: 'Salón Viejo' }),
      makeAreaSocial({ id: 2, nombre: 'Parrillera' }),
    ];

    const payloadArea = {
      nombre: 'Salón Renovado',
      aforo_maximo: 90,
      costo_uso_usd: '40.00',
      deposito_garantia_usd: '120.00',
      requiere_solvencia_estricta: true,
    };
    store.isStale = true;
    const deferredArea = createDeferred<AreaSocialDTO>();
    vi.mocked(apiClient.apiRequest).mockReturnValueOnce(deferredArea.promise);
    const areaReq = store.crearAreaSocial(payloadArea, 'idem-area-1');
    expect(store.isLoading).toBe(true);
    deferredArea.resolve(makeAreaSocial({ id: 1, nombre: 'Salón Renovado' }));
    await areaReq;
    expect(store.isLoading).toBe(false);
    expect(store.isStale).toBe(false);
    expect(apiClient.apiRequest).toHaveBeenLastCalledWith('/api/reservas/areas', {
      method: 'POST',
      body: payloadArea,
      idempotencyKey: 'idem-area-1',
    });
    expect(store.areasSociales.map((a) => a.id)).toEqual([2, 1]);
    expect(store.areasSociales[1].nombre).toBe('Salón Renovado');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('raw-crear-area');
    await expect(store.crearAreaSocial(payloadArea)).rejects.toBe('raw-crear-area');
    expect(store.error).toBe('Error al crear el área social');
    expect(store.isLoading).toBe(false);

    store.reservas = [
      makeReserva({ id: 10, motivo_evento: 'Motivo Viejo' }),
      makeReserva({ id: 77, motivo_evento: 'Otra' }),
    ];
    const payloadRes = {
      area_id: 1,
      unidad_id: 2,
      fecha_evento: '2026-12-20',
      motivo_evento: 'Graduación',
    };
    store.isStale = true;
    const deferredRes = createDeferred<ReservaAreaDTO>();
    vi.mocked(apiClient.apiRequest).mockReturnValueOnce(deferredRes.promise);
    const resReq = store.solicitarReservaArea(payloadRes, 'idem-res-10');
    expect(store.isLoading).toBe(true);
    deferredRes.resolve(makeReserva({ id: 10, motivo_evento: 'Graduación' }));
    await resReq;
    expect(store.isLoading).toBe(false);
    expect(store.isStale).toBe(false);
    expect(apiClient.apiRequest).toHaveBeenLastCalledWith('/api/reservas/solicitar', {
      method: 'POST',
      body: payloadRes,
      idempotencyKey: 'idem-res-10',
    });
    expect(store.reservas.map((r) => r.id)).toEqual([10, 77]);
    expect(store.reservas[0].motivo_evento).toBe('Graduación');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('raw-solicitar-reserva');
    await expect(store.solicitarReservaArea(payloadRes)).rejects.toBe('raw-solicitar-reserva');
    expect(store.error).toBe('Error al solicitar la reserva del área social');
    expect(store.isLoading).toBe(false);
  });

  it('verifica endpoints, isLoading, isStale y errores fallback al inspeccionar y cancelar reserva', async () => {
    const store = useAccessAmenitiesStore();
    store.reservas = [makeReserva({ id: 10 })];

    const payloadInsp = {
      estado: 'FINALIZADA_SIN_DANOS' as const,
      observaciones_inspeccion: 'Sin novedades',
    };
    store.isStale = true;
    const deferredInsp = createDeferred<ReservaAreaDTO>();
    vi.mocked(apiClient.apiRequest).mockReturnValueOnce(deferredInsp.promise);
    const inspReq = store.inspeccionarReserva(10, payloadInsp, 'idem-insp-10');
    expect(store.isLoading).toBe(true);
    deferredInsp.resolve(
      makeReserva({
        id: 10,
        estado: 'FINALIZADA_SIN_DANOS',
        observaciones_inspeccion: 'Sin novedades',
      }),
    );
    await inspReq;
    expect(store.isLoading).toBe(false);
    expect(store.isStale).toBe(false);
    expect(apiClient.apiRequest).toHaveBeenLastCalledWith('/api/reservas/10/inspeccionar', {
      method: 'PUT',
      body: payloadInsp,
      idempotencyKey: 'idem-insp-10',
    });

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('raw-inspeccion');
    await expect(store.inspeccionarReserva(10, payloadInsp)).rejects.toBe('raw-inspeccion');
    expect(store.error).toBe('Error al registrar la inspección post-evento del área social');
    expect(store.isLoading).toBe(false);

    store.isStale = true;
    const deferredCancel = createDeferred<ReservaAreaDTO>();
    vi.mocked(apiClient.apiRequest).mockReturnValueOnce(deferredCancel.promise);
    const cancelReq = store.cancelarReserva(10, 'idem-cancel-001');
    expect(store.isLoading).toBe(true);
    deferredCancel.resolve(makeReserva({ id: 10, estado: 'CANCELADA' }));
    await cancelReq;
    expect(store.isLoading).toBe(false);
    expect(store.isStale).toBe(false);
    expect(apiClient.apiRequest).toHaveBeenLastCalledWith('/api/reservas/10/cancelar', {
      method: 'PUT',
      body: {},
      idempotencyKey: 'idem-cancel-001',
    });

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('raw-cancelar');
    await expect(store.cancelarReserva(10)).rejects.toBe('raw-cancelar');
    expect(store.error).toBe('Error al cancelar la reserva del área social');
    expect(store.isLoading).toBe(false);
  });
});
