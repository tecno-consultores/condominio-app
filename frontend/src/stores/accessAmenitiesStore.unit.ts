import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { useAccessAmenitiesStore } from './accessAmenitiesStore';
import * as apiClient from '../services/apiClient';

vi.mock('../services/apiClient', () => ({
  apiRequest: vi.fn(),
}));

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
    expect(store.pases[0].nombre_visitante).toContain('&lt;b&gt;Visitante&lt;/b&gt;');
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

    vi.mocked(apiClient.apiRequest).mockResolvedValueOnce({
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

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce(new Error('err-revocar'));
    await expect(store.revocarPaseVisita(1)).rejects.toThrow('err-revocar');

    vi.mocked(apiClient.apiRequest).mockRejectedValueOnce('raw-revocar');
    await expect(store.revocarPaseVisita(1)).rejects.toBe('raw-revocar');

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
    expect(store.areasSociales[0].nombre).toContain('&lt;b&gt;Fiestas&lt;/b&gt;');

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
    expect(store.reservas[0].motivo_evento).toContain('&lt;i&gt;infantil&lt;/i&gt;');

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
  });
});
