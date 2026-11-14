// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

import type { Page, Route } from '@playwright/test';

export type ProfileKey =
  | 'PROPIETARIO'
  | 'TESORERO'
  | 'PRESIDENTE'
  | 'VICEPRESIDENTE'
  | 'SECRETARIO'
  | 'VOCERO'
  | 'CONSERJE'
  | 'FANTASMA';

export interface MockUserProfile {
  id: number;
  nombre: string;
  cedula: string;
  correo: string;
  telefono: string;
  es_activo: boolean;
  rol: ProfileKey;
  unidad_activa_id: number | null;
}

export interface CondominioMockOptions {
  initialProfile?: ProfileKey | null;
  closingActive?: boolean;
  strictSolvencyBlock?: boolean;
}

interface PagoState {
  id: number;
  recibo_id: number;
  monto: string;
  moneda: string;
  tasa_cambio: string;
  monto_usd: string;
  metodo_pago: string;
  numero_referencia: string | null;
  estado: string;
}

interface PaseState {
  id: number;
  unidad_id: number;
  identificador_unidad: string;
  jti: string;
  qr_token: string;
  nombre_visitante: string;
  cedula_visitante: string;
  placa_vehiculo: string | null;
  modalidad: string;
  estado: string;
  fecha_expiracion: string;
}

interface ReservaState {
  id: number;
  area_id: number;
  nombre_area: string;
  unidad_id: number;
  identificador_unidad: string;
  fecha_evento: string;
  motivo_evento: string;
  estado: string;
  tarea_inspeccion_id: number | null;
  observaciones_inspeccion: string | null;
}

export interface CondominioMockState {
  currentUser: MockUserProfile | null;
  closingActive: boolean;
  strictSolvencyBlock: boolean;
  tasaUsdVes: string;
  capturedIdempotencyKeys: string[];
  unidades: Array<{
    id: number;
    identificador: string;
    estructura_id: number;
    alicuota: string;
    cuota_fija_usd: string | null;
  }>;
  recibos: Array<{
    recibo_id: number;
    unidad_id: number;
    identificador_unidad: string;
    periodo: string;
    monto_usd: string;
    estado: string;
    saldo_usd: string;
  }>;
  pagos: PagoState[];
  fondos: Array<{
    id: number;
    nombre: string;
    tipo: string;
    porcentaje_recargo: string;
    saldo_actual_usd: string;
  }>;
  usuariosPendientes: MockUserProfile[];
  incidencias: Array<{
    id: number;
    area: string;
    descripcion: string;
    estado: string;
    adhesiones_count: number;
    url_foto: string | null;
  }>;
  tareas: Array<{
    id: number;
    titulo: string;
    area: string;
    completada: boolean;
    incidencia_id: number | null;
  }>;
  fotosVoceros: Array<{
    id: number;
    periodo: string;
    area: string;
    comentario: string;
    url_foto: string;
  }>;
  bitacora: Array<{
    id: number;
    fecha: string;
    hora: string;
    ubicacion: string;
    contenido: string;
  }>;
  consultas: Array<{
    id: number;
    titulo: string;
    tipo_consulta: string;
    regla_quorum: string;
    estado: string;
    descripcion_legal: string;
    fecha_cierre: string;
    quorum_minimo_alicuota: string;
    participacion_alicuota: string;
    total_votos: number;
    ya_voto_usuario: boolean;
    acta_bitacora_id: number | null;
    mi_voto: Record<string, unknown> | null;
    opciones: Array<{
      id: number;
      etiqueta: string;
      es_opcion_aprobatoria: boolean;
      votos_cantidad: number;
      alicuota_acumulada: string;
    }>;
  }>;
  pases: PaseState[];
  paquetes: Array<{
    id: number;
    unidad_id: number;
    identificador_unidad: string;
    empresa_envio: string;
    descripcion: string;
    estado: string;
    url_foto_evidencia: string | null;
  }>;
  areasSociales: Array<{
    id: number;
    nombre: string;
    aforo_maximo: number;
    costo_uso_usd: string;
    deposito_garantia_usd: string;
    requiere_solvencia_estricta: boolean;
  }>;
  reservas: ReservaState[];
  nextId: number;
}

const PROFILES: Record<ProfileKey, MockUserProfile> = {
  PROPIETARIO: {
    id: 101,
    nombre: 'Ana Residente',
    cedula: 'V-11111111',
    correo: 'residente@condominio.test',
    telefono: '0414-0000001',
    es_activo: true,
    rol: 'PROPIETARIO',
    unidad_activa_id: 1,
  },
  TESORERO: {
    id: 102,
    nombre: 'Carlos Tesorero',
    cedula: 'V-22222222',
    correo: 'tesorero@condominio.test',
    telefono: '0414-0000002',
    es_activo: true,
    rol: 'TESORERO',
    unidad_activa_id: 2,
  },
  VICEPRESIDENTE: {
    id: 103,
    nombre: 'Elena Vicepresidente',
    cedula: 'V-33333333',
    correo: 'vicepresidente@condominio.test',
    telefono: '0414-0000003',
    es_activo: true,
    rol: 'VICEPRESIDENTE',
    unidad_activa_id: 1,
  },
  PRESIDENTE: {
    id: 104,
    nombre: 'Mateo Presidente',
    cedula: 'V-44444444',
    correo: 'presidente@condominio.test',
    telefono: '0414-0000004',
    es_activo: true,
    rol: 'PRESIDENTE',
    unidad_activa_id: 1,
  },
  SECRETARIO: {
    id: 105,
    nombre: 'Lucia Secretaria',
    cedula: 'V-55555555',
    correo: 'secretario@condominio.test',
    telefono: '0414-0000005',
    es_activo: true,
    rol: 'SECRETARIO',
    unidad_activa_id: 1,
  },
  VOCERO: {
    id: 106,
    nombre: 'Diego Vocero',
    cedula: 'V-66666666',
    correo: 'vocero@condominio.test',
    telefono: '0414-0000006',
    es_activo: true,
    rol: 'VOCERO',
    unidad_activa_id: 1,
  },
  CONSERJE: {
    id: 107,
    nombre: 'Pedro Conserje',
    cedula: 'V-77777777',
    correo: 'conserje@condominio.test',
    telefono: '0414-0000007',
    es_activo: true,
    rol: 'CONSERJE',
    unidad_activa_id: 1,
  },
  FANTASMA: {
    id: 108,
    nombre: 'Sofia Fantasma',
    cedula: 'V-88888888',
    correo: 'fantasma@condominio.test',
    telefono: '0414-0000008',
    es_activo: false,
    rol: 'FANTASMA',
    unidad_activa_id: null,
  },
};

function resolveProfileByEmail(email: string): ProfileKey {
  const lower = email.toLowerCase();
  const keys: ProfileKey[] = [
    'TESORERO',
    'VICEPRESIDENTE',
    'PRESIDENTE',
    'SECRETARIO',
    'VOCERO',
    'CONSERJE',
    'FANTASMA',
  ];
  return keys.find((k) => lower.includes(k.toLowerCase())) ?? 'PROPIETARIO';
}

function createInitialState(options: CondominioMockOptions): CondominioMockState {
  const initialUser = options.initialProfile ? { ...PROFILES[options.initialProfile] } : null;
  return {
    currentUser: initialUser,
    closingActive: Boolean(options.closingActive),
    strictSolvencyBlock: Boolean(options.strictSolvencyBlock),
    tasaUsdVes: '45.50',
    capturedIdempotencyKeys: [],
    unidades: [
      {
        id: 1,
        identificador: 'A-101',
        estructura_id: 1,
        alicuota: '10.0000',
        cuota_fija_usd: null,
      },
      {
        id: 2,
        identificador: 'A-102',
        estructura_id: 1,
        alicuota: '10.0000',
        cuota_fija_usd: null,
      },
    ],
    recibos: [
      {
        recibo_id: 1,
        unidad_id: 1,
        identificador_unidad: 'A-101',
        periodo: '2026-10',
        monto_usd: '50.00',
        estado: 'PENDIENTE',
        saldo_usd: '50.00',
      },
    ],
    pagos: [
      {
        id: 1,
        recibo_id: 1,
        monto: '1825.00',
        moneda: 'VES',
        tasa_cambio: '45.50',
        monto_usd: '40.11',
        metodo_pago: 'PAGO_MOVIL',
        numero_referencia: '99881122',
        estado: 'EN_REVISION',
      },
    ],
    fondos: [
      {
        id: 1,
        nombre: 'Fondo de Reserva Legal',
        tipo: 'RESERVA_LEGAL',
        porcentaje_recargo: '10.00',
        saldo_actual_usd: '1250.00',
      },
    ],
    usuariosPendientes: [{ ...PROFILES.FANTASMA, id: 501, nombre: 'Marcos Pendiente' }],
    incidencias: [
      {
        id: 1,
        area: 'Bombas de Agua',
        descripcion: 'Fuga menor en sello mecanico bomba auxiliar',
        estado: 'ABIERTA',
        adhesiones_count: 3,
        url_foto: 's3://condominio-media/incidencias/1.avif',
      },
    ],
    tareas: [
      {
        id: 1,
        titulo: 'Inspeccionar presion de bomba auxiliar',
        area: 'Bombas de Agua',
        completada: false,
        incidencia_id: 1,
      },
    ],
    fotosVoceros: [
      {
        id: 1,
        periodo: '2026-10',
        area: 'Cuarto de Bombas',
        comentario: 'Valvulas lubricadas y sin humedad aparente',
        url_foto: 'https://cdn.condominio.local/voceros/bomba-1.avif',
      },
    ],
    bitacora: [
      {
        id: 1,
        fecha: '2026-10-15',
        hora: '19:00',
        ubicacion: 'Salon de Usos Multiples',
        contenido: 'Aprobacion de mantenimiento preventivo anual.',
      },
    ],
    consultas: [
      {
        id: 1,
        titulo: 'Aprobacion de Impermeabilizacion Azotea Torre A',
        tipo_consulta: 'CARTA_CONSULTA_1RA',
        regla_quorum: 'MAYORIA_SIMPLE',
        estado: 'ABIERTA',
        descripcion_legal:
          'Contratacion de impermeabilizacion con manto asfaltico segun Art. 23 LPH.',
        fecha_cierre: '2026-12-30T23:59:00Z',
        quorum_minimo_alicuota: '50.0100',
        participacion_alicuota: '42.0000',
        total_votos: 4,
        ya_voto_usuario: false,
        acta_bitacora_id: null,
        mi_voto: null,
        opciones: [
          {
            id: 11,
            etiqueta: 'Aprobar Presupuesto',
            es_opcion_aprobatoria: true,
            votos_cantidad: 4,
            alicuota_acumulada: '42.0000',
          },
          {
            id: 12,
            etiqueta: 'Rechazar y Solicitar Nueva Licitacion',
            es_opcion_aprobatoria: false,
            votos_cantidad: 0,
            alicuota_acumulada: '0.0000',
          },
        ],
      },
    ],
    pases: [
      {
        id: 1,
        unidad_id: 1,
        identificador_unidad: 'A-101',
        jti: 'jti-seed-0001-abcd',
        qr_token: 'qr-seed-token-0001.hmac_valid_sig',
        nombre_visitante: 'Tecnico Fibra Seed',
        cedula_visitante: 'V-19000111',
        placa_vehiculo: 'AA111BB',
        modalidad: 'UNICO_USO',
        estado: 'ACTIVO',
        fecha_expiracion: '2026-12-31T23:59:00Z',
      },
    ],
    paquetes: [
      {
        id: 1,
        unidad_id: 1,
        identificador_unidad: 'A-101',
        empresa_envio: 'ZOOM',
        descripcion: 'Sobre certificado guia #90012',
        estado: 'EN_GARITA',
        url_foto_evidencia: null,
      },
    ],
    areasSociales: [
      {
        id: 1,
        nombre: 'Salon de Fiestas Principal',
        aforo_maximo: 60,
        costo_uso_usd: '25.00',
        deposito_garantia_usd: '100.00',
        requiere_solvencia_estricta: true,
      },
    ],
    reservas: [
      {
        id: 1,
        area_id: 1,
        nombre_area: 'Salon de Fiestas Principal',
        unidad_id: 1,
        identificador_unidad: 'A-101',
        fecha_evento: '2026-12-18',
        motivo_evento: 'Reunion Navidena Familiar',
        estado: 'CONFIRMADA',
        tarea_inspeccion_id: 10,
        observaciones_inspeccion: null,
      },
    ],
    nextId: 600,
  };
}

interface HttpMockResponse {
  status: number;
  body: unknown;
  headers?: Record<string, string>;
}

function jsonResp(
  status: number,
  body: unknown,
  headers?: Record<string, string>,
): HttpMockResponse {
  return { status, body, headers };
}

function loginUser(body: Record<string, unknown>, state: CondominioMockState): HttpMockResponse {
  const email = String(body.username ?? body.correo ?? 'residente@condominio.test');
  if (String(body.password ?? '') === 'ClaveInvalida999') {
    return jsonResp(401, { detail: 'Credenciales invalidas.' });
  }
  state.currentUser = { ...PROFILES[resolveProfileByEmail(email)] };
  return jsonResp(200, { message: 'ok' }, { 'x-csrf-token': 'csrf-e2e-token' });
}

function registerUser(body: Record<string, unknown>, state: CondominioMockState): HttpMockResponse {
  const created: MockUserProfile = {
    id: ++state.nextId,
    nombre: String(body.nombre ?? 'Nuevo Residente'),
    cedula: String(body.cedula ?? 'V-99999999'),
    correo: String(body.correo ?? 'nuevo@condominio.test'),
    telefono: String(body.telefono ?? '0414-0000099'),
    es_activo: false,
    rol: 'FANTASMA',
    unidad_activa_id: null,
  };
  state.usuariosPendientes.push(created);
  state.currentUser = created;
  return jsonResp(201, created, { 'x-csrf-token': 'csrf-e2e-token' });
}

function handleAuthRoute(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/auth/me' && method === 'GET') {
    return state.currentUser
      ? jsonResp(200, state.currentUser)
      : jsonResp(401, { detail: 'No autenticado' });
  }
  if (path === '/api/auth/login' && method === 'POST') return loginUser(body, state);
  if (path === '/api/auth/register' && method === 'POST') return registerUser(body, state);
  if (path === '/api/auth/logout' && method === 'POST') {
    state.currentUser = null;
    return jsonResp(200, { message: 'ok' });
  }
  return null;
}

function handleFinanceCore(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/finanzas/tasa' && method === 'GET') {
    return jsonResp(200, { id: 1, fecha: '2026-10-30', tasa_usd_ves: state.tasaUsdVes });
  }
  if (path === '/api/finanzas/tasa' && method === 'POST') {
    state.tasaUsdVes = String(body.tasa_usd_ves ?? state.tasaUsdVes);
    return jsonResp(201, { id: 2, fecha: '2026-10-30', tasa_usd_ves: state.tasaUsdVes });
  }
  if (path === '/api/finanzas/resumen' && method === 'GET') {
    return jsonResp(200, {
      deuda_total_usd: state.recibos[0]?.saldo_usd ?? '0.00',
      total_egresos_usd: '450.00',
      gastos_por_categoria: { 'Bombas de Agua': '250.00', Vigilancia: '200.00' },
      estado_cobranza: state.recibos,
    });
  }
  if (path === '/api/finanzas/egresos' && method === 'POST') {
    return jsonResp(201, { id: ++state.nextId, monto_usd: String(body.monto ?? '50.00') });
  }
  if (path === '/api/finanzas/cierre-mensual' && method === 'POST') {
    state.closingActive = true;
    return jsonResp(200, {
      id: 1,
      periodo: String(body.periodo ?? '2026-10'),
      estado: 'CERRADO',
      bloqueado: true,
    });
  }
  return null;
}

function resolveUpdatedPago(pagoId: number, action: string, state: CondominioMockState): PagoState {
  const existing = state.pagos.find((p) => p.id === pagoId);
  state.pagos = state.pagos.filter((p) => p.id !== pagoId);
  const base: PagoState = existing ?? {
    id: pagoId,
    recibo_id: 1,
    monto: '50.00',
    moneda: 'USD',
    tasa_cambio: state.tasaUsdVes,
    monto_usd: '50.00',
    metodo_pago: 'PAGO_MOVIL',
    numero_referencia: '123456',
    estado: 'EN_REVISION',
  };
  return { ...base, estado: action === 'aprobar' ? 'APROBADO' : 'RECHAZADO' };
}

function reportPayment(
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse {
  if (state.closingActive) {
    return jsonResp(409, { detail: 'Periodo contable bloqueado por Candado Contable.' });
  }
  const monto = String(body.monto ?? '50.00');
  const moneda = String(body.moneda ?? 'USD');
  const pago: PagoState = {
    id: ++state.nextId,
    recibo_id: Number(body.recibo_id ?? 1),
    monto,
    moneda,
    tasa_cambio: state.tasaUsdVes,
    monto_usd: moneda === 'USD' ? monto : '40.00',
    metodo_pago: String(body.metodo_pago ?? 'PAGO_MOVIL'),
    numero_referencia: (body.numero_referencia as string | null) ?? null,
    estado: 'EN_REVISION',
  };
  state.pagos.push(pago);
  return jsonResp(201, pago);
}

function mutatePaymentStatus(
  pagoId: number,
  action: string,
  state: CondominioMockState,
): HttpMockResponse {
  const updated = resolveUpdatedPago(pagoId, action, state);
  if (action === 'aprobar' && state.recibos[0]) {
    state.recibos[0].estado = 'PAGADO';
    state.recibos[0].saldo_usd = '0.00';
  }
  return jsonResp(200, updated);
}

function handlePagosRoute(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/pagos/revision' && method === 'GET') {
    return jsonResp(200, state.pagos);
  }
  if (path === '/api/pagos/reportar' && method === 'POST') {
    return reportPayment(body, state);
  }
  const pagoMatch = /^\/api\/pagos\/(\d+)\/(aprobar|rechazar)$/.exec(path);
  if (pagoMatch && method === 'PUT') {
    return mutatePaymentStatus(Number(pagoMatch[1]), pagoMatch[2]!, state);
  }
  return null;
}

function handleFondosRoute(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/finanzas/fondos' && method === 'GET') {
    return jsonResp(200, state.fondos);
  }
  if (path === '/api/finanzas/fondos' && method === 'POST') {
    const created = {
      id: ++state.nextId,
      nombre: String(body.nombre ?? 'Fondo Especial'),
      tipo: String(body.tipo ?? 'PROVISION_ESPECIAL'),
      porcentaje_recargo: String(body.porcentaje_recargo ?? '5.00'),
      saldo_actual_usd: '0.00',
    };
    state.fondos.push(created);
    return jsonResp(201, created);
  }
  return null;
}

function handleBillingAndSolvency(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/finanzas/facturar-periodo' && method === 'POST') {
    return jsonResp(201, {
      periodo: String(body.periodo ?? '2026-10'),
      modalidad: String(body.modalidad ?? 'ALICUOTA'),
      recibos_emitidos: state.unidades.length,
      total_facturado_neto_usd: '100.00',
    });
  }
  const desgloseMatch = /^\/api\/finanzas\/recibos\/(\d+)\/desglose$/.exec(path);
  if (desgloseMatch && method === 'GET') {
    return jsonResp(200, {
      recibo_id: Number(desgloseMatch[1]),
      identificador_unidad: 'A-101',
      periodo: '2026-10',
      alicuota_aplicada: '10.0000',
      estado: 'PENDIENTE',
      monto_usd: '50.00',
      credito_descontado_usd: '5.00',
      saldo_pendiente_usd: '45.00',
      items: [
        {
          id: 1,
          tipo_item: 'GASTO_COMUN',
          descripcion: 'Mantenimiento Bombas',
          monto_usd: '55.00',
        },
        {
          id: 2,
          tipo_item: 'ABONO_CREDITO_PREVIO',
          descripcion: 'Saldo previo',
          monto_usd: '-5.00',
        },
      ],
    });
  }
  const solvEmitMatch = /^\/api\/finanzas\/solvencia\/(\d+)$/.exec(path);
  if (solvEmitMatch && method === 'POST') {
    const uid = Number(solvEmitMatch[1]);
    return jsonResp(201, {
      folio: `SOLV-202610-000${uid}-ABCD`,
      unidad_id: uid,
      identificador_unidad: 'A-101',
      deuda_verificada_usd: '0.00',
      fecha_emision: '2026-10-30',
      fecha_vencimiento: '2026-11-30',
      firma_hmac: 'hmac_sha256_solvencia_e2e_sig_001122',
      qr_token: `SOLV-202610-000${uid}-ABCD.hmac_sha256_solvencia_e2e_sig_001122`,
    });
  }
  const solvVerifMatch = /^\/api\/finanzas\/solvencia\/verificar\/([^/]+)$/.exec(path);
  if (solvVerifMatch && method === 'GET') {
    return jsonResp(200, {
      valido: true,
      vigente: true,
      folio: solvVerifMatch[1],
      identificador_unidad: 'A-101',
      vigente_hasta: '2026-11-30',
      mensaje: 'Certificado verificado criptograficamente.',
    });
  }
  return null;
}

function generateStructureUnits(
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse {
  const ids = Array.isArray(body.identificadores) ? (body.identificadores as string[]) : ['B-101'];
  const createdUnits = ids.map((identificador) => ({
    id: ++state.nextId,
    identificador,
    estructura_id: 2,
    alicuota: '10.0000',
    cuota_fija_usd: null,
  }));
  state.unidades.push(...createdUnits);
  return jsonResp(201, {
    estructura_id: 2,
    nombre: String(body.nombre ?? 'Torre B'),
    unidades_creadas: createdUnits.length,
    unidades: createdUnits,
  });
}

function assignPendingUser(
  uid: number,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse {
  const pending = state.usuariosPendientes.find((u) => u.id === uid) ?? PROFILES.FANTASMA;
  state.usuariosPendientes = state.usuariosPendientes.filter((u) => u.id !== uid);
  return jsonResp(200, {
    ...pending,
    id: uid,
    es_activo: true,
    rol: String(body.rol ?? 'PROPIETARIO') as ProfileKey,
    unidad_activa_id: Number(body.unidad_id ?? 1),
  });
}

function handleStructureRoute(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/estructura/unidades' && method === 'GET') {
    return jsonResp(200, state.unidades);
  }
  if (path === '/api/estructura/generar' && method === 'POST') {
    return generateStructureUnits(body, state);
  }
  const alicuotaMatch = /^\/api\/estructura\/unidades\/(\d+)\/alicuota$/.exec(path);
  if (alicuotaMatch && method === 'PUT') {
    const unit =
      state.unidades.find((u) => u.id === Number(alicuotaMatch[1])) ?? state.unidades[0]!;
    unit.alicuota = String(body.alicuota ?? unit.alicuota);
    return jsonResp(200, unit);
  }
  return null;
}

function handleAdminRoute(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  const structureResp = handleStructureRoute(method, path, body, state);
  if (structureResp) return structureResp;
  if (path === '/api/usuarios/pendientes' && method === 'GET') {
    return jsonResp(200, state.usuariosPendientes);
  }
  const asignarMatch = /^\/api\/usuarios\/(\d+)\/asignar$/.exec(path);
  if (asignarMatch && method === 'PUT') {
    return assignPendingUser(Number(asignarMatch[1]), body, state);
  }
  if (path === '/api/junta/cargos' && method === 'PUT') {
    return jsonResp(200, {
      id: Number(body.usuario_id ?? 101),
      nombre: 'Ana Residente',
      rol: String(body.cargo ?? 'TESORERO'),
    });
  }
  return null;
}

function handleIncidenciasRoute(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/incidencias/abiertas' && method === 'GET') {
    return jsonResp(200, state.incidencias);
  }
  if (path === '/api/incidencias/crear' && method === 'POST') {
    const created = {
      id: ++state.nextId,
      area: String(body.area ?? 'Bombas de Agua'),
      descripcion: String(body.descripcion ?? 'Falla reportada'),
      estado: 'ABIERTA',
      adhesiones_count: 1,
      url_foto: null,
    };
    state.incidencias.unshift(created);
    return jsonResp(201, created);
  }
  const adherirMatch = /^\/api\/incidencias\/(\d+)\/adherir$/.exec(path);
  if (adherirMatch && method === 'POST') {
    const id = Number(adherirMatch[1]);
    const item = state.incidencias.find((i) => i.id === id) ?? state.incidencias[0]!;
    item.adhesiones_count += 1;
    return jsonResp(200, item);
  }
  return null;
}

function handleTareasRoute(
  method: string,
  path: string,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/tareas/diarias' && method === 'GET') {
    return jsonResp(200, state.tareas);
  }
  const tareaMatch = /^\/api\/tareas\/(\d+)\/completar$/.exec(path);
  if (tareaMatch && method === 'PUT') {
    const tarea = state.tareas.find((t) => t.id === Number(tareaMatch[1])) ?? state.tareas[0]!;
    tarea.completada = true;
    return jsonResp(200, tarea);
  }
  return null;
}

function handleVocerosRoute(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/voceros/galeria' && method === 'GET') {
    return jsonResp(200, {
      periodo: '2026-10',
      fotos_usadas_mes: state.fotosVoceros.length,
      limite_mensual: 30,
      fotos: state.fotosVoceros,
    });
  }
  if (path === '/api/voceros/fotos' && method === 'POST') {
    const foto = {
      id: ++state.nextId,
      periodo: String(body.periodo ?? '2026-10'),
      area: String(body.area ?? 'Cuarto de Bombas'),
      comentario: String(body.comentario ?? 'Sin novedades'),
      url_foto: String(body.url_foto ?? 'https://cdn.condominio.local/voceros/ok.avif'),
    };
    state.fotosVoceros.unshift(foto);
    return jsonResp(201, foto);
  }
  return null;
}

function handleBitacoraRoute(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/bitacora/historial' && method === 'GET') {
    return jsonResp(200, state.bitacora);
  }
  if (path === '/api/bitacora/acta' && method === 'POST') {
    const acta = {
      id: ++state.nextId,
      fecha: String(body.fecha ?? '2026-10-30'),
      hora: String(body.hora ?? '19:30'),
      ubicacion: String(body.ubicacion ?? 'Salon Social'),
      contenido: String(body.contenido ?? 'Acuerdo registrado'),
    };
    state.bitacora.unshift(acta);
    return jsonResp(201, acta);
  }
  return null;
}

function handleTareasVocerosBitacoraRoute(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  return (
    handleTareasRoute(method, path, state) ??
    handleVocerosRoute(method, path, body, state) ??
    handleBitacoraRoute(method, path, body, state)
  );
}

function handleGovernanceRoute(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/consultas' && method === 'GET') {
    return jsonResp(200, state.consultas);
  }
  const detailMatch = /^\/api\/consultas\/(\d+)$/.exec(path);
  if (detailMatch && method === 'GET') {
    const id = Number(detailMatch[1]);
    return jsonResp(200, state.consultas.find((c) => c.id === id) ?? state.consultas[0]);
  }
  if (path === '/api/consultas' && method === 'POST') {
    const created = {
      ...state.consultas[0]!,
      id: ++state.nextId,
      titulo: String(body.titulo ?? 'Nueva Carta Consulta'),
      estado: 'ABIERTA',
      participacion_alicuota: '0.0000',
      total_votos: 0,
      ya_voto_usuario: false,
      mi_voto: null,
      acta_bitacora_id: null,
    };
    state.consultas.unshift(created);
    return jsonResp(201, created);
  }
  const voteMatch = /^\/api\/consultas\/(\d+)\/votar$/.exec(path);
  if (voteMatch && method === 'POST') {
    const consulta =
      state.consultas.find((c) => c.id === Number(voteMatch[1])) ?? state.consultas[0]!;
    const option =
      consulta.opciones.find((o) => o.id === Number(body.opcion_id)) ?? consulta.opciones[0]!;
    option.votos_cantidad += 1;
    option.alicuota_acumulada = '52.0000';
    consulta.total_votos += 1;
    consulta.participacion_alicuota = '52.0000';
    consulta.ya_voto_usuario = true;
    const recibo = {
      voto_id: ++state.nextId,
      identificador_unidad: 'A-101',
      opcion_etiqueta: option.etiqueta,
      alicuota_capturada: '10.0000',
      firma_hmac: 'hmac_sha256_voto_emitido_e2e_009911',
      mensaje_verificacion: 'Voto ponderado registrado en urna inmutable.',
    };
    consulta.mi_voto = recibo;
    return jsonResp(201, recibo);
  }
  const closeMatch = /^\/api\/consultas\/(\d+)\/cerrar$/.exec(path);
  if (closeMatch && method === 'POST') {
    const consulta =
      state.consultas.find((c) => c.id === Number(closeMatch[1])) ?? state.consultas[0]!;
    consulta.estado = 'CERRADA_APROBADA';
    consulta.acta_bitacora_id = 301;
    return jsonResp(200, { estado: consulta.estado, acta_bitacora_id: 301 });
  }
  return null;
}

function createVisitorPass(
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse {
  const id = ++state.nextId;
  const pase: PaseState = {
    id,
    unidad_id: Number(body.unidad_id ?? 1),
    identificador_unidad: 'A-101',
    jti: `jti-e2e-${id}`,
    qr_token: `qr-e2e-${id}.hmac_sha256_sig`,
    nombre_visitante: String(body.nombre_visitante ?? 'Visitante'),
    cedula_visitante: String(body.cedula_visitante ?? 'V-20000000'),
    placa_vehiculo: (body.placa_vehiculo as string | null) ?? null,
    modalidad: String(body.modalidad ?? 'UNICO_USO'),
    estado: 'ACTIVO',
    fecha_expiracion: '2026-12-31T23:59:00Z',
  };
  state.pases.unshift(pase);
  return jsonResp(201, pase);
}

function verifyVisitorQr(
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse {
  const pase = state.pases.find((p) => p.qr_token === String(body.qr_token ?? ''));
  if (!pase || pase.estado !== 'ACTIVO') {
    return jsonResp(409, { detail: 'Pase QR invalido, revocado o ya quemado (Anti-Replay).' });
  }
  if (pase.modalidad === 'UNICO_USO') pase.estado = 'USADO';
  return jsonResp(200, {
    autorizado: true,
    jti: pase.jti,
    nombre_visitante: pase.nombre_visitante,
    cedula_visitante: pase.cedula_visitante,
    identificador_unidad: pase.identificador_unidad,
    placa_vehiculo: pase.placa_vehiculo,
    mensaje: 'Ingreso autorizado en garita con proteccion Anti-Replay.',
  });
}

function handlePassesRoute(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/accesos/pases/mios' && method === 'GET') {
    return jsonResp(200, state.pases);
  }
  if (path === '/api/accesos/pases' && method === 'POST') {
    return createVisitorPass(body, state);
  }
  const revMatch = /^\/api\/accesos\/pases\/(\d+)$/.exec(path);
  if (revMatch && method === 'DELETE') {
    const pase = state.pases.find((p) => p.id === Number(revMatch[1])) ?? state.pases[0]!;
    pase.estado = 'REVOCADO';
    return jsonResp(200, pase);
  }
  if (path === '/api/accesos/verificar-qr' && method === 'POST') {
    return verifyVisitorQr(body, state);
  }
  return null;
}

function handleParcelsRoute(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/paqueteria' && method === 'GET') {
    return jsonResp(200, state.paquetes);
  }
  if (path === '/api/paqueteria/registrar' && method === 'POST') {
    const created = {
      id: ++state.nextId,
      unidad_id: Number(body.unidad_id ?? 1),
      identificador_unidad: 'A-101',
      empresa_envio: String(body.empresa_envio ?? 'ZOOM'),
      descripcion: String(body.descripcion ?? 'Paquete registrado'),
      estado: 'EN_GARITA',
      url_foto_evidencia: (body.url_foto_evidencia as string | null) ?? null,
    };
    state.paquetes.unshift(created);
    return jsonResp(201, created);
  }
  const pacMatch = /^\/api\/paqueteria\/(\d+)\/entregar$/.exec(path);
  if (pacMatch && method === 'PUT') {
    const paq = state.paquetes.find((p) => p.id === Number(pacMatch[1])) ?? state.paquetes[0]!;
    paq.estado = 'ENTREGADO';
    return jsonResp(200, paq);
  }
  return null;
}

function handleAmenitiesRoute(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/reservas/areas' && method === 'GET') {
    return jsonResp(200, state.areasSociales);
  }
  if (path === '/api/reservas/areas' && method === 'POST') {
    const area = {
      id: ++state.nextId,
      nombre: String(body.nombre ?? 'Parrillera Norte'),
      aforo_maximo: Number(body.aforo_maximo ?? 30),
      costo_uso_usd: String(body.costo_uso_usd ?? '25.00'),
      deposito_garantia_usd: String(body.deposito_garantia_usd ?? '100.00'),
      requiere_solvencia_estricta: Boolean(body.requiere_solvencia_estricta ?? true),
    };
    state.areasSociales.push(area);
    return jsonResp(201, area);
  }
  return null;
}

function requestReservation(
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse {
  if (state.strictSolvencyBlock) {
    return jsonResp(403, {
      detail: 'Reserva bloqueada: la unidad debe estar solvente ($0.00 USD) para esta area.',
    });
  }
  const area =
    state.areasSociales.find((a) => a.id === Number(body.area_id)) ?? state.areasSociales[0]!;
  const created: ReservaState = {
    id: ++state.nextId,
    area_id: area.id,
    nombre_area: area.nombre,
    unidad_id: Number(body.unidad_id ?? 1),
    identificador_unidad: 'A-101',
    fecha_evento: String(body.fecha_evento ?? '2026-12-20'),
    motivo_evento: String(body.motivo_evento ?? 'Evento familiar'),
    estado: 'CONFIRMADA',
    tarea_inspeccion_id: 88,
    observaciones_inspeccion: null,
  };
  state.reservas.unshift(created);
  return jsonResp(201, created);
}

function mutateReservation(
  id: number,
  action: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse {
  const reserva = state.reservas.find((r) => r.id === id) ?? state.reservas[0]!;
  if (action === 'cancelar') {
    reserva.estado = 'CANCELADA';
  } else {
    reserva.estado = String(body.estado ?? 'FINALIZADA_SIN_DANOS');
    reserva.observaciones_inspeccion = String(body.observaciones_inspeccion ?? 'Sin novedades');
  }
  return jsonResp(200, reserva);
}

function handleReservasRoute(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/reservas' && method === 'GET') {
    return jsonResp(200, state.reservas);
  }
  if (path === '/api/reservas/solicitar' && method === 'POST') {
    return requestReservation(body, state);
  }
  const resMatch = /^\/api\/reservas\/(\d+)\/(inspeccionar|cancelar)$/.exec(path);
  if (resMatch && method === 'PUT') {
    return mutateReservation(Number(resMatch[1]), resMatch[2]!, body, state);
  }
  return null;
}

function dispatchMockRoute(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse {
  const handlers = [
    handleAuthRoute,
    handleFinanceCore,
    handlePagosRoute,
    handleFondosRoute,
    handleBillingAndSolvency,
    handleAdminRoute,
    handleIncidenciasRoute,
    handleTareasVocerosBitacoraRoute,
    handleGovernanceRoute,
    handlePassesRoute,
    handleParcelsRoute,
    handleAmenitiesRoute,
    handleReservasRoute,
  ];
  for (const handler of handlers) {
    const response = handler(method, path, body, state);
    if (response) return response;
  }
  return jsonResp(404, { detail: `Ruta no simulada en fixture: ${method} ${path}` });
}

function parseRequestBody(route: Route): Record<string, unknown> {
  const raw = route.request().postData();
  if (!raw) return {};
  try {
    return JSON.parse(raw) as Record<string, unknown>;
  } catch {
    const params = new URLSearchParams(raw);
    return Object.fromEntries(params.entries());
  }
}

export async function installCondominioApiMock(
  page: Page,
  options: CondominioMockOptions = {},
): Promise<CondominioMockState> {
  await page.unroute('**/api/**');
  const state = createInitialState(options);
  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const idempKey = request.headers()['idempotency-key'];
    if (idempKey) {
      state.capturedIdempotencyKeys.push(idempKey);
    }
    const body = parseRequestBody(route);
    const result = dispatchMockRoute(request.method(), url.pathname, body, state);
    await route.fulfill({
      status: result.status,
      contentType: 'application/json',
      headers: result.headers,
      body: JSON.stringify(result.body),
    });
  });
  return state;
}
