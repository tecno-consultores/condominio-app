// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

import type { Page, Route } from '@playwright/test';

export type ProfileKey =
  | 'PROPIETARIO'
  | 'INQUILINO'
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
  omitDailyRate?: boolean;
  omitResumen?: boolean;
}

interface PagoState {
  id: number;
  recibo_id: number;
  usuario_id: number;
  monto: string;
  moneda: string;
  monto_usd: string;
  tasa_cambio: string;
  metodo_pago: string;
  numero_referencia: string | null;
  url_comprobante: string | null;
  estado: string;
}

interface PaseState {
  id: number;
  jti: string;
  unidad_id: number;
  identificador_unidad: string;
  creado_por_id: number;
  nombre_visitante: string;
  cedula_visitante: string;
  placa_vehiculo: string | null;
  modalidad: string;
  valido_desde: string;
  valido_hasta: string;
  estado: string;
  usado_en: string | null;
  verificado_por_id: number | null;
  firma_hmac: string;
  qr_token: string;
}

interface ReservaState {
  id: number;
  area_id: number;
  nombre_area: string;
  unidad_id: number;
  identificador_unidad: string;
  solicitante_id: number;
  fecha_evento: string;
  motivo_evento: string;
  estado: string;
  tarea_inspeccion_id: number | null;
  observaciones_inspeccion: string | null;
  creado_en: string;
}

export interface CondominioMockState {
  currentUser: MockUserProfile | null;
  closingActive: boolean;
  strictSolvencyBlock: boolean;
  omitDailyRate: boolean;
  omitResumen: boolean;
  tasaUsdVes: string;
  capturedIdempotencyKeys: string[];
  comunicados: Array<{
    id: number;
    titulo: string;
    contenido: string;
    enlace_externo: string | null;
    activo: boolean;
  }>;
  unidades: Array<{
    id: number;
    identificador: string;
    estructura_id: number;
    alicuota: string;
    cuota_fija_usd: string | null;
    credito_disponible_usd: string;
  }>;
  recibos: Array<{
    recibo_id: number;
    unidad_id: number;
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
    es_activo: boolean;
  }>;
  usuariosPendientes: MockUserProfile[];
  incidencias: Array<{
    id: number;
    usuario_creador_id: number;
    area: string;
    descripcion: string;
    url_foto: string | null;
    estado: string;
    adhesiones_count: number;
  }>;
  tareas: Array<{
    id: number;
    plantilla_id: number | null;
    incidencia_id: number | null;
    titulo: string;
    area: string;
    fecha: string;
    completada: boolean;
    url_evidencia: string | null;
  }>;
  fotosVoceros: Array<{
    id: number;
    usuario_id: number;
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
    autor_id: number;
  }>;
  consultas: Array<{
    id: number;
    titulo: string;
    descripcion_legal: string;
    tipo_consulta: string;
    regla_quorum: string;
    quorum_minimo_alicuota: string;
    participacion_alicuota: string;
    alicuota_aprobatoria: string;
    total_votos: number;
    fecha_apertura: string;
    fecha_cierre: string;
    estado: string;
    creada_por_id: number;
    acta_bitacora_id: number | null;
    ya_voto_usuario: boolean;
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
    recibido_por_id: number;
    empresa_envio: string;
    descripcion: string;
    url_foto_evidencia: string | null;
    estado: string;
    fecha_recepcion: string;
    fecha_entrega: string | null;
    retirado_por_id: number | null;
  }>;
  areasSociales: Array<{
    id: number;
    nombre: string;
    aforo_maximo: number;
    costo_uso_usd: string;
    deposito_garantia_usd: string;
    requiere_solvencia_estricta: boolean;
    es_activa: boolean;
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
  INQUILINO: {
    id: 109,
    nombre: 'Luis Inquilino',
    cedula: 'V-99999999',
    correo: 'inquilino@condominio.test',
    telefono: '0414-0000009',
    es_activo: true,
    rol: 'INQUILINO',
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

const ROLES_JUNTA_LPH: readonly ProfileKey[] = [
  'PRESIDENTE',
  'VICEPRESIDENTE',
  'TESORERO',
  'SECRETARIO',
  'VOCERO',
];
const ROLES_TESORERIA: readonly ProfileKey[] = ['TESORERO', 'PRESIDENTE'];
const ROLES_DIRECTIVA: readonly ProfileKey[] = ['PRESIDENTE', 'VICEPRESIDENTE'];
const ROLES_ALICUOTA: readonly ProfileKey[] = ['PRESIDENTE', 'VICEPRESIDENTE', 'TESORERO'];
const ROLES_GOBERNANZA: readonly ProfileKey[] = ['PRESIDENTE', 'SECRETARIO'];
const ROLES_CONSERJERIA: readonly ProfileKey[] = ['CONSERJE', 'PRESIDENTE', 'VICEPRESIDENTE'];
const ROLES_GARITA: readonly ProfileKey[] = ['CONSERJE', 'PRESIDENTE', 'VOCERO'];
const ROLES_PAQUETERIA: readonly ProfileKey[] = ['CONSERJE', 'PRESIDENTE'];
const ROLES_VOCERIA: readonly ProfileKey[] = ['VOCERO', 'PRESIDENTE'];
const ROLES_SECRETARIA: readonly ProfileKey[] = ['SECRETARIO', 'PRESIDENTE'];
const ROLES_GESTION_AREAS: readonly ProfileKey[] = ['PRESIDENTE', 'TESORERO'];
const ROLES_INSPECCION_RESERVA: readonly ProfileKey[] = ['CONSERJE', 'PRESIDENTE', 'TESORERO'];
const ROLES_CANCELACION_JUNTA: readonly ProfileKey[] = [
  'PRESIDENTE',
  'VICEPRESIDENTE',
  'TESORERO',
  'SECRETARIO',
];

function resolveProfileByEmail(email: string): ProfileKey {
  const lower = email.toLowerCase();
  const keys: ProfileKey[] = [
    'TESORERO',
    'VICEPRESIDENTE',
    'PRESIDENTE',
    'SECRETARIO',
    'VOCERO',
    'CONSERJE',
    'INQUILINO',
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
    omitDailyRate: Boolean(options.omitDailyRate),
    omitResumen: Boolean(options.omitResumen),
    tasaUsdVes: '45.50',
    capturedIdempotencyKeys: [],
    comunicados: [
      {
        id: 1,
        titulo: 'Mantenimiento Preventivo',
        contenido: 'Lavado de tanques este sabado.',
        enlace_externo: 'https://condominio.local/consultas',
        activo: true,
      },
    ],
    unidades: [
      {
        id: 1,
        identificador: 'A-101',
        estructura_id: 1,
        alicuota: '10.0000',
        cuota_fija_usd: null,
        credito_disponible_usd: '0.00',
      },
      {
        id: 2,
        identificador: 'A-102',
        estructura_id: 1,
        alicuota: '10.0000',
        cuota_fija_usd: null,
        credito_disponible_usd: '0.00',
      },
    ],
    recibos: [
      {
        recibo_id: 1,
        unidad_id: 1,
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
        usuario_id: 101,
        monto: '1825.00',
        moneda: 'VES',
        monto_usd: '40.11',
        tasa_cambio: '45.50',
        metodo_pago: 'PAGO_MOVIL',
        numero_referencia: '99881122',
        url_comprobante: null,
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
        es_activo: true,
      },
    ],
    usuariosPendientes: [{ ...PROFILES.FANTASMA, id: 501, nombre: 'Marcos Pendiente' }],
    incidencias: [
      {
        id: 1,
        usuario_creador_id: 101,
        area: 'Bombas de Agua',
        descripcion: 'Fuga menor en sello mecanico bomba auxiliar',
        url_foto: 's3://condominio-media/incidencias/1.avif',
        estado: 'ABIERTO',
        adhesiones_count: 3,
      },
    ],
    tareas: [
      {
        id: 1,
        plantilla_id: null,
        incidencia_id: 1,
        titulo: 'Inspeccionar presion de bomba auxiliar',
        area: 'Bombas de Agua',
        fecha: '2026-10-30',
        completada: false,
        url_evidencia: null,
      },
    ],
    fotosVoceros: [
      {
        id: 1,
        usuario_id: 106,
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
        autor_id: 105,
      },
    ],
    consultas: [
      {
        id: 1,
        titulo: 'Aprobacion de Impermeabilizacion Azotea Torre A',
        descripcion_legal:
          'Contratacion de impermeabilizacion con manto asfaltico segun Art. 23 LPH.',
        tipo_consulta: 'CARTA_CONSULTA_1RA',
        regla_quorum: 'MAYORIA_SIMPLE',
        quorum_minimo_alicuota: '50.0100',
        participacion_alicuota: '42.0000',
        alicuota_aprobatoria: '42.0000',
        total_votos: 4,
        fecha_apertura: '2026-10-01T08:00:00Z',
        fecha_cierre: '2026-12-30T23:59:00Z',
        estado: 'ABIERTA',
        creada_por_id: 104,
        acta_bitacora_id: null,
        ya_voto_usuario: false,
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
        jti: 'jti-seed-0001-abcd',
        unidad_id: 1,
        identificador_unidad: 'A-101',
        creado_por_id: 101,
        nombre_visitante: 'Tecnico Fibra Seed',
        cedula_visitante: 'V-19000111',
        placa_vehiculo: 'AA111BB',
        modalidad: 'UNICO_USO',
        valido_desde: '2026-10-30T00:00:00Z',
        valido_hasta: '2026-12-31T23:59:00Z',
        estado: 'ACTIVO',
        usado_en: null,
        verificado_por_id: null,
        firma_hmac: 'hmac_valid_sig',
        qr_token: 'qr-seed-token-0001.hmac_valid_sig',
      },
    ],
    paquetes: [
      {
        id: 1,
        unidad_id: 1,
        identificador_unidad: 'A-101',
        recibido_por_id: 107,
        empresa_envio: 'ZOOM',
        descripcion: 'Sobre certificado guia #90012',
        url_foto_evidencia: null,
        estado: 'EN_GARITA',
        fecha_recepcion: '2026-10-30T10:00:00Z',
        fecha_entrega: null,
        retirado_por_id: null,
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
        es_activa: true,
      },
    ],
    reservas: [
      {
        id: 1,
        area_id: 1,
        nombre_area: 'Salon de Fiestas Principal',
        unidad_id: 1,
        identificador_unidad: 'A-101',
        solicitante_id: 101,
        fecha_evento: '2026-12-18',
        motivo_evento: 'Reunion Navidena Familiar',
        estado: 'CONFIRMADA',
        tarea_inspeccion_id: 10,
        observaciones_inspeccion: null,
        creado_en: '2026-10-30T09:00:00Z',
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

function requireActive(state: CondominioMockState): HttpMockResponse | null {
  if (!state.currentUser) {
    return jsonResp(401, { detail: 'No autenticado' });
  }
  if (!state.currentUser.es_activo || state.currentUser.rol === 'FANTASMA') {
    return jsonResp(403, {
      detail: 'Cuenta pendiente de aprobación por la Junta de Condominio.',
    });
  }
  return null;
}

function withActive(
  state: CondominioMockState,
  handler: (user: MockUserProfile) => HttpMockResponse,
): HttpMockResponse {
  const activeError = requireActive(state);
  return activeError ?? handler(state.currentUser!);
}

function withRoles(
  state: CondominioMockState,
  allowed: readonly ProfileKey[],
  handler: (user: MockUserProfile) => HttpMockResponse,
): HttpMockResponse {
  const activeError = requireActive(state);
  if (activeError) return activeError;
  const user = state.currentUser!;
  if (!allowed.includes(user.rol)) {
    return jsonResp(403, { detail: 'No tiene permisos para ejecutar esta acción.' });
  }
  return handler(user);
}

function toPublicUserResponse(user: MockUserProfile): Omit<MockUserProfile, 'unidad_activa_id'> {
  return {
    id: user.id,
    nombre: user.nombre,
    cedula: user.cedula,
    correo: user.correo,
    telefono: user.telefono,
    es_activo: user.es_activo,
    rol: user.rol,
  };
}

function loginUser(body: Record<string, unknown>, state: CondominioMockState): HttpMockResponse {
  const email = String(body.username ?? body.correo ?? 'residente@condominio.test');
  if (String(body.password ?? '') === 'ClaveInvalida999') {
    return jsonResp(401, { detail: 'Credenciales inválidas' });
  }
  const user = { ...PROFILES[resolveProfileByEmail(email)] };
  state.currentUser = user;
  return jsonResp(
    200,
    { message: 'Login exitoso', rol: user.rol, csrf_token: 'csrf-e2e-token' },
    { 'x-csrf-token': 'csrf-e2e-token' },
  );
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
  return jsonResp(201, toPublicUserResponse(created), { 'x-csrf-token': 'csrf-e2e-token' });
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
    return jsonResp(200, { message: 'Sesión cerrada exitosamente.' });
  }
  return null;
}

function handleComunicadosRoute(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/comunicados/recientes' && method === 'GET') {
    return withActive(state, () => jsonResp(200, state.comunicados));
  }
  if (path === '/api/comunicados' && method === 'POST') {
    return withRoles(state, ROLES_SECRETARIA, () => {
      const created = {
        id: ++state.nextId,
        titulo: String(body.titulo ?? 'Comunicado'),
        contenido: String(body.contenido ?? ''),
        enlace_externo: (body.enlace_externo as string | null) ?? null,
        activo: true,
      };
      state.comunicados.unshift(created);
      return jsonResp(201, created);
    });
  }
  return null;
}

function getDailyRateResponse(state: CondominioMockState): HttpMockResponse {
  if (state.omitDailyRate) {
    return jsonResp(404, { detail: 'No hay tasa BCV registrada para hoy.' });
  }
  return jsonResp(200, { fecha: '2026-10-30', tasa_usd_ves: state.tasaUsdVes });
}

function getFinanceSummaryResponse(state: CondominioMockState): HttpMockResponse {
  if (state.omitResumen) {
    return jsonResp(503, { detail: 'Resumen financiero temporalmente no disponible.' });
  }
  return jsonResp(200, {
    deuda_total_usd: state.recibos[0]?.saldo_usd ?? '0.00',
    total_egresos_usd: '450.00',
    gastos_por_categoria: { 'Bombas de Agua': '250.00', Vigilancia: '200.00' },
    estado_cobranza: state.recibos,
  });
}

function handleFinanceCore(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/finanzas/tasa' && method === 'GET') {
    return withActive(state, () => getDailyRateResponse(state));
  }
  if (path === '/api/finanzas/tasa' && method === 'POST') {
    return withRoles(state, ROLES_TESORERIA, () => {
      state.tasaUsdVes = String(body.tasa_usd_ves ?? state.tasaUsdVes);
      return jsonResp(201, {
        fecha: String(body.fecha ?? '2026-10-30'),
        tasa_usd_ves: state.tasaUsdVes,
      });
    });
  }
  if (path === '/api/finanzas/resumen' && method === 'GET') {
    return withActive(state, () => getFinanceSummaryResponse(state));
  }
  if (path === '/api/finanzas/egresos' && method === 'POST') {
    return withRoles(state, ROLES_TESORERIA, () =>
      jsonResp(201, { id: ++state.nextId, monto_usd: String(body.monto ?? '50.00') }),
    );
  }
  if (path === '/api/finanzas/cierre-mensual' && method === 'POST') {
    return withRoles(state, ROLES_TESORERIA, () => {
      state.closingActive = true;
      return jsonResp(200, {
        periodo: String(body.periodo ?? '2026-10'),
        estado: 'CERRADO',
      });
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
    usuario_id: 101,
    monto: '50.00',
    moneda: 'USD',
    monto_usd: '50.00',
    tasa_cambio: state.tasaUsdVes,
    metodo_pago: 'PAGO_MOVIL',
    numero_referencia: '123456',
    url_comprobante: null,
    estado: 'EN_REVISION',
  };
  return { ...base, estado: action === 'aprobar' ? 'APROBADO' : 'RECHAZADO' };
}

function reportPayment(
  user: MockUserProfile,
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
    usuario_id: user.id,
    monto,
    moneda,
    monto_usd: moneda === 'USD' ? monto : '40.00',
    tasa_cambio: state.tasaUsdVes,
    metodo_pago: String(body.metodo_pago ?? 'PAGO_MOVIL'),
    numero_referencia: (body.numero_referencia as string | null) ?? null,
    url_comprobante: (body.url_comprobante as string | null) ?? null,
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
    return withRoles(state, ROLES_TESORERIA, () => jsonResp(200, state.pagos));
  }
  if (path === '/api/pagos/reportar' && method === 'POST') {
    return withActive(state, (user) => reportPayment(user, body, state));
  }
  const pagoMatch = /^\/api\/pagos\/(\d+)\/(aprobar|rechazar)$/.exec(path);
  if (pagoMatch && method === 'PUT') {
    return withRoles(state, ROLES_TESORERIA, () =>
      mutatePaymentStatus(Number(pagoMatch[1]), pagoMatch[2]!, state),
    );
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
    return withActive(state, () => jsonResp(200, state.fondos));
  }
  if (path === '/api/finanzas/fondos' && method === 'POST') {
    return withRoles(state, ROLES_TESORERIA, () => {
      const created = {
        id: ++state.nextId,
        nombre: String(body.nombre ?? 'Fondo Especial'),
        tipo: String(body.tipo ?? 'ESPECIAL'),
        porcentaje_recargo: String(body.porcentaje_recargo ?? '5.00'),
        saldo_actual_usd: '0.00',
        es_activo: true,
      };
      state.fondos.push(created);
      return jsonResp(201, created);
    });
  }
  return null;
}

function buildReciboDesglose(reciboId: number, state: CondominioMockState): HttpMockResponse {
  const recibo = state.recibos.find((r) => r.recibo_id === reciboId) ?? state.recibos[0];
  const unidadId = recibo?.unidad_id ?? 1;
  const ident = state.unidades.find((u) => u.id === unidadId)?.identificador ?? 'A-101';
  return jsonResp(200, {
    recibo_id: reciboId,
    unidad_id: unidadId,
    identificador_unidad: ident,
    alicuota_aplicada: '10.0000',
    periodo: recibo?.periodo ?? '2026-10',
    monto_usd: '50.00',
    monto_pagado_usd: '5.00',
    saldo_pendiente_usd: '45.00',
    credito_descontado_usd: '5.00',
    estado: recibo?.estado ?? 'PENDIENTE',
    bloqueado: state.closingActive,
    items: [
      {
        id: 1,
        recibo_id: reciboId,
        tipo_item: 'GASTO_COMUN',
        descripcion: 'Mantenimiento Bombas',
        monto_usd: '55.00',
      },
      {
        id: 2,
        recibo_id: reciboId,
        tipo_item: 'ABONO_CREDITO_PREVIO',
        descripcion: 'Saldo previo',
        monto_usd: '-5.00',
      },
    ],
  });
}

function emitSolvencyCertificate(
  uid: number,
  user: MockUserProfile,
  state: CondominioMockState,
): HttpMockResponse {
  const ident = state.unidades.find((u) => u.id === uid)?.identificador ?? 'A-101';
  const folio = `SOLV-202610-000${uid}-ABCD`;
  const firma = 'hmac_sha256_solvencia_e2e_sig_001122';
  return jsonResp(201, {
    id: ++state.nextId,
    jti: `jti-solv-e2e-${uid}`,
    folio,
    unidad_id: uid,
    identificador_unidad: ident,
    emitido_por_id: user.id,
    fecha_emision: '2026-10-30T12:00:00Z',
    fecha_vencimiento: '2026-11-30',
    deuda_verificada_usd: '0.00',
    firma_hmac: firma,
    qr_token: `${folio}.${firma}`,
  });
}

function handleBillingAndSolvency(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/finanzas/facturar-periodo' && method === 'POST') {
    return withRoles(state, ROLES_TESORERIA, () =>
      jsonResp(201, {
        periodo: String(body.periodo ?? '2026-10'),
        modalidad: String(body.modalidad ?? 'ALICUOTA'),
        recibos_emitidos: state.unidades.length,
        total_egresos_comunes_usd: '100.00',
        recargo_fondo_reserva_usd: '10.00',
        cuota_extraordinaria_total_usd: '0.00',
        total_facturado_bruto_usd: '110.00',
        total_credito_descontado_usd: '10.00',
        total_facturado_neto_usd: '100.00',
        superavit_conciliado_fondo_usd: '0.00',
      }),
    );
  }
  const desgloseMatch = /^\/api\/finanzas\/recibos\/(\d+)\/desglose$/.exec(path);
  if (desgloseMatch && method === 'GET') {
    return withActive(state, () => buildReciboDesglose(Number(desgloseMatch[1]), state));
  }
  const solvEmitMatch = /^\/api\/finanzas\/solvencia\/(\d+)$/.exec(path);
  if (solvEmitMatch && method === 'POST') {
    return withActive(state, (user) =>
      emitSolvencyCertificate(Number(solvEmitMatch[1]), user, state),
    );
  }
  const solvVerifMatch = /^\/api\/finanzas\/solvencia\/verificar\/([^/]+)$/.exec(path);
  if (solvVerifMatch && method === 'GET') {
    return jsonResp(200, {
      valido: true,
      jti: 'jti-solv-e2e-1',
      folio: solvVerifMatch[1],
      unidad_id: 1,
      identificador_unidad: 'A-101',
      fecha_vencimiento: '2026-11-30',
      vigente: true,
      deuda_verificada_usd: '0.00',
      firma_hmac: 'hmac_sha256_solvencia_e2e_sig_001122',
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
    credito_disponible_usd: '0.00',
  }));
  state.unidades.push(...createdUnits);
  return jsonResp(201, {
    estructura_id: 2,
    nombre: String(body.nombre ?? 'Torre B'),
    tipo: String(body.tipo ?? 'TORRE'),
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
    ...toPublicUserResponse(pending),
    id: uid,
    es_activo: true,
    rol: String(body.rol ?? 'PROPIETARIO') as ProfileKey,
  });
}

function listUnitsByRole(state: CondominioMockState): HttpMockResponse {
  const user = state.currentUser;
  const isActiveJunta = Boolean(user && user.es_activo && ROLES_JUNTA_LPH.includes(user.rol));
  if (isActiveJunta) {
    return jsonResp(200, state.unidades);
  }
  return jsonResp(
    200,
    state.unidades.map((u) => ({
      id: u.id,
      identificador: u.identificador,
      estructura_id: u.estructura_id,
    })),
  );
}

function handleStructureRoute(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/estructura/unidades' && method === 'GET') {
    return listUnitsByRole(state);
  }
  if (path === '/api/estructura/generar' && method === 'POST') {
    return withRoles(state, ROLES_DIRECTIVA, () => generateStructureUnits(body, state));
  }
  const alicuotaMatch = /^\/api\/estructura\/unidades\/(\d+)\/alicuota$/.exec(path);
  if (alicuotaMatch && method === 'PUT') {
    return withRoles(state, ROLES_ALICUOTA, () => {
      const unit =
        state.unidades.find((u) => u.id === Number(alicuotaMatch[1])) ?? state.unidades[0]!;
      unit.alicuota = String(body.alicuota ?? unit.alicuota);
      return jsonResp(200, unit);
    });
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
    return withRoles(state, ROLES_DIRECTIVA, () =>
      jsonResp(200, state.usuariosPendientes.map(toPublicUserResponse)),
    );
  }
  const asignarMatch = /^\/api\/usuarios\/(\d+)\/asignar$/.exec(path);
  if (asignarMatch && method === 'PUT') {
    return withRoles(state, ROLES_DIRECTIVA, () =>
      assignPendingUser(Number(asignarMatch[1]), body, state),
    );
  }
  if (path === '/api/junta/cargos' && method === 'PUT') {
    return withRoles(state, ['PRESIDENTE'], () =>
      jsonResp(200, {
        ...toPublicUserResponse(PROFILES.PROPIETARIO),
        id: Number(body.usuario_id ?? 101),
        rol: String(body.cargo ?? 'TESORERO'),
      }),
    );
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
    return withActive(state, () => jsonResp(200, state.incidencias));
  }
  if (path === '/api/incidencias/crear' && method === 'POST') {
    return withActive(state, (user) => {
      const created = {
        id: ++state.nextId,
        usuario_creador_id: user.id,
        area: String(body.area ?? 'Bombas de Agua'),
        descripcion: String(body.descripcion ?? 'Falla reportada'),
        url_foto: (body.url_foto as string | null) ?? null,
        estado: 'ABIERTO',
        adhesiones_count: 1,
      };
      state.incidencias.unshift(created);
      return jsonResp(201, created);
    });
  }
  const adherirMatch = /^\/api\/incidencias\/(\d+)\/adherir$/.exec(path);
  if (adherirMatch && method === 'POST') {
    return withActive(state, () => {
      const id = Number(adherirMatch[1]);
      const item = state.incidencias.find((i) => i.id === id) ?? state.incidencias[0]!;
      item.adhesiones_count += 1;
      return jsonResp(200, item);
    });
  }
  return null;
}

function handleTareasRoute(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/tareas/diarias' && method === 'GET') {
    return withActive(state, () => jsonResp(200, state.tareas));
  }
  if (path === '/api/tareas/plantillas' && method === 'POST') {
    return withRoles(state, ROLES_DIRECTIVA, () =>
      jsonResp(201, {
        id: ++state.nextId,
        titulo: String(body.titulo ?? 'Rutina de mantenimiento'),
        area: String(body.area ?? 'General'),
        frecuencia: String(body.frecuencia ?? 'DIARIA'),
        activa: true,
      }),
    );
  }
  if (path === '/api/tareas/diarias' && method === 'POST') {
    return withRoles(state, ROLES_DIRECTIVA, () => {
      const created = {
        id: ++state.nextId,
        plantilla_id: null,
        incidencia_id: (body.incidencia_id as number | null) ?? null,
        titulo: String(body.titulo ?? 'Tarea puntual'),
        area: String(body.area ?? 'General'),
        fecha: '2026-10-30',
        completada: false,
        url_evidencia: null,
      };
      state.tareas.push(created);
      return jsonResp(201, created);
    });
  }
  if (path === '/api/tareas/generar-diarias' && method === 'POST') {
    return withRoles(state, ROLES_DIRECTIVA, () => jsonResp(200, { tareas_generadas: 1 }));
  }
  const tareaMatch = /^\/api\/tareas\/(\d+)\/completar$/.exec(path);
  if (tareaMatch && method === 'PUT') {
    return withRoles(state, ROLES_CONSERJERIA, () => {
      const tarea = state.tareas.find((t) => t.id === Number(tareaMatch[1])) ?? state.tareas[0]!;
      tarea.completada = true;
      return jsonResp(200, tarea);
    });
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
    return withActive(state, () =>
      jsonResp(200, {
        periodo: '2026-10',
        fotos_usadas_mes: state.fotosVoceros.length,
        limite_mensual: 30,
        fotos: state.fotosVoceros,
      }),
    );
  }
  if (path === '/api/voceros/fotos' && method === 'POST') {
    return withRoles(state, ROLES_VOCERIA, (user) => {
      const foto = {
        id: ++state.nextId,
        usuario_id: user.id,
        periodo: String(body.periodo ?? '2026-10'),
        area: String(body.area ?? 'Cuarto de Bombas'),
        comentario: String(body.comentario ?? 'Sin novedades'),
        url_foto: String(body.url_foto ?? 'https://cdn.condominio.local/voceros/ok.avif'),
      };
      state.fotosVoceros.unshift(foto);
      return jsonResp(201, foto);
    });
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
    return withActive(state, () => jsonResp(200, state.bitacora));
  }
  if (path === '/api/bitacora/acta' && method === 'POST') {
    return withRoles(state, ROLES_SECRETARIA, (user) => {
      const acta = {
        id: ++state.nextId,
        fecha: String(body.fecha ?? '2026-10-30'),
        hora: String(body.hora ?? '19:30'),
        ubicacion: String(body.ubicacion ?? 'Salon Social'),
        contenido: String(body.contenido ?? 'Acuerdo registrado'),
        autor_id: user.id,
      };
      state.bitacora.unshift(acta);
      return jsonResp(201, acta);
    });
  }
  return null;
}

function handleEvidenciasRoute(
  method: string,
  path: string,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/evidencias/subir' && method === 'POST') {
    return withActive(state, () =>
      jsonResp(202, {
        url: '/api/evidencias/comprobantes/mock.webp',
        mime_origen: 'image/png',
        formato_destino: 'webp',
        bytes_recibidos: 1024,
        estado: 'ENCOLADO',
      }),
    );
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
    handleEvidenciasRoute(method, path, state) ??
    handleTareasRoute(method, path, body, state) ??
    handleVocerosRoute(method, path, body, state) ??
    handleBitacoraRoute(method, path, body, state)
  );
}

function castConsultationVote(
  consultaId: number,
  user: MockUserProfile,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse {
  if (user.rol === 'INQUILINO') {
    return jsonResp(403, {
      detail:
        'Solo el propietario titular o un representante con poder registrado puede votar en Cartas Consulta.',
    });
  }
  const consulta = state.consultas.find((c) => c.id === consultaId) ?? state.consultas[0]!;
  const option =
    consulta.opciones.find((o) => o.id === Number(body.opcion_id)) ?? consulta.opciones[0]!;
  option.votos_cantidad += 1;
  option.alicuota_acumulada = '52.0000';
  consulta.total_votos += 1;
  consulta.participacion_alicuota = '52.0000';
  consulta.ya_voto_usuario = true;

  const unidadId = Number(body.unidad_id ?? user.unidad_activa_id ?? 1);
  const ident = state.unidades.find((u) => u.id === unidadId)?.identificador ?? 'A-101';
  const votoId = ++state.nextId;
  const fechaVoto = '2026-10-30T14:00:00Z';
  const jti = `jti-voto-e2e-${votoId}`;
  const firma = 'hmac_sha256_voto_emitido_e2e_009911';

  consulta.mi_voto = {
    voto_id: votoId,
    jti,
    unidad_id: unidadId,
    identificador_unidad: ident,
    opcion_id: option.id,
    opcion_etiqueta: option.etiqueta,
    alicuota_capturada: '10.0000',
    fecha_voto: fechaVoto,
    firma_hmac: firma,
  };

  return jsonResp(201, {
    voto_id: votoId,
    jti,
    consulta_id: consulta.id,
    titulo_consulta: consulta.titulo,
    unidad_id: unidadId,
    identificador_unidad: ident,
    usuario_id: user.id,
    opcion_id: option.id,
    opcion_etiqueta: option.etiqueta,
    alicuota_capturada: '10.0000',
    participacion_total_alicuota: consulta.participacion_alicuota,
    quorum_minimo_alicuota: consulta.quorum_minimo_alicuota,
    fecha_voto: fechaVoto,
    ip_hash: 'e2e_ip_hash_001',
    firma_hmac: firma,
    mensaje_verificacion: 'Voto ponderado registrado en urna inmutable.',
  });
}

function closeConsultation(consultaId: number, state: CondominioMockState): HttpMockResponse {
  const consulta = state.consultas.find((c) => c.id === consultaId) ?? state.consultas[0]!;
  consulta.estado = 'CERRADA_APROBADA';
  consulta.acta_bitacora_id = 301;
  return jsonResp(200, {
    consulta_id: consulta.id,
    titulo: consulta.titulo,
    estado: consulta.estado,
    regla_quorum: consulta.regla_quorum,
    quorum_minimo_alicuota: consulta.quorum_minimo_alicuota,
    participacion_alicuota: consulta.participacion_alicuota,
    alicuota_aprobatoria: consulta.alicuota_aprobatoria,
    total_votos: consulta.total_votos,
    acta_bitacora_id: 301,
    hash_global_escrutinio: 'sha256_escrutinio_e2e_001',
  });
}

function handleGovernanceRoute(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/consultas' && method === 'GET') {
    return withActive(state, () => jsonResp(200, state.consultas));
  }
  const detailMatch = /^\/api\/consultas\/(\d+)$/.exec(path);
  if (detailMatch && method === 'GET') {
    return withActive(state, () => {
      const id = Number(detailMatch[1]);
      return jsonResp(200, state.consultas.find((c) => c.id === id) ?? state.consultas[0]);
    });
  }
  if (path === '/api/consultas' && method === 'POST') {
    return withRoles(state, ROLES_GOBERNANZA, (user) => {
      const created = {
        ...state.consultas[0]!,
        id: ++state.nextId,
        titulo: String(body.titulo ?? 'Nueva Carta Consulta'),
        estado: 'ABIERTA',
        participacion_alicuota: '0.0000',
        alicuota_aprobatoria: '0.0000',
        total_votos: 0,
        creada_por_id: user.id,
        ya_voto_usuario: false,
        mi_voto: null,
        acta_bitacora_id: null,
      };
      state.consultas.unshift(created);
      return jsonResp(201, created);
    });
  }
  const voteMatch = /^\/api\/consultas\/(\d+)\/votar$/.exec(path);
  if (voteMatch && method === 'POST') {
    return withActive(state, (user) =>
      castConsultationVote(Number(voteMatch[1]), user, body, state),
    );
  }
  const closeMatch = /^\/api\/consultas\/(\d+)\/cerrar$/.exec(path);
  if (closeMatch && method === 'POST') {
    return withRoles(state, ROLES_GOBERNANZA, () =>
      closeConsultation(Number(closeMatch[1]), state),
    );
  }
  return null;
}

function createVisitorPass(
  user: MockUserProfile,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse {
  const id = ++state.nextId;
  const unidadId = Number(body.unidad_id ?? user.unidad_activa_id ?? 1);
  const ident = state.unidades.find((u) => u.id === unidadId)?.identificador ?? 'A-101';
  const firma = 'hmac_sha256_sig';
  const pase: PaseState = {
    id,
    jti: `jti-e2e-${id}`,
    unidad_id: unidadId,
    identificador_unidad: ident,
    creado_por_id: user.id,
    nombre_visitante: String(body.nombre_visitante ?? 'Visitante'),
    cedula_visitante: String(body.cedula_visitante ?? 'V-20000000'),
    placa_vehiculo: (body.placa_vehiculo as string | null) ?? null,
    modalidad: String(body.modalidad ?? 'UNICO_USO'),
    valido_desde: '2026-10-30T00:00:00Z',
    valido_hasta: '2026-12-31T23:59:00Z',
    estado: 'ACTIVO',
    usado_en: null,
    verificado_por_id: null,
    firma_hmac: firma,
    qr_token: `qr-e2e-${id}.${firma}`,
  };
  state.pases.unshift(pase);
  return jsonResp(201, pase);
}

function verifyVisitorQr(
  user: MockUserProfile,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse {
  const pase = state.pases.find((p) => p.qr_token === String(body.qr_token ?? ''));
  if (!pase || pase.estado !== 'ACTIVO') {
    return jsonResp(409, { detail: 'Pase QR invalido, revocado o ya quemado (Anti-Replay).' });
  }
  const usadoEn = '2026-10-30T15:30:00Z';
  if (pase.modalidad === 'UNICO_USO') {
    pase.estado = 'USADO';
    pase.usado_en = usadoEn;
    pase.verificado_por_id = user.id;
  }
  return jsonResp(200, {
    autorizado: true,
    pase_id: pase.id,
    jti: pase.jti,
    unidad_id: pase.unidad_id,
    identificador_unidad: pase.identificador_unidad,
    nombre_visitante: pase.nombre_visitante,
    cedula_visitante: pase.cedula_visitante,
    placa_vehiculo: pase.placa_vehiculo,
    modalidad: pase.modalidad,
    estado: pase.estado,
    usado_en: usadoEn,
    verificado_por_id: user.id,
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
    return withActive(state, () => jsonResp(200, state.pases));
  }
  if (path === '/api/accesos/pases' && method === 'POST') {
    return withActive(state, (user) => createVisitorPass(user, body, state));
  }
  const revMatch = /^\/api\/accesos\/pases\/(\d+)$/.exec(path);
  if (revMatch && method === 'DELETE') {
    return withActive(state, () => {
      const pase = state.pases.find((p) => p.id === Number(revMatch[1])) ?? state.pases[0]!;
      pase.estado = 'REVOCADO';
      return jsonResp(200, pase);
    });
  }
  if (path === '/api/accesos/verificar-qr' && method === 'POST') {
    return withRoles(state, ROLES_GARITA, (user) => verifyVisitorQr(user, body, state));
  }
  return null;
}

function listParcelsForUser(user: MockUserProfile, state: CondominioMockState): HttpMockResponse {
  if (ROLES_PAQUETERIA.includes(user.rol)) {
    return jsonResp(200, state.paquetes);
  }
  return jsonResp(
    200,
    state.paquetes.filter((p) => p.unidad_id === user.unidad_activa_id),
  );
}

function deliverParcel(
  paqueteId: number,
  user: MockUserProfile,
  state: CondominioMockState,
): HttpMockResponse {
  const paq = state.paquetes.find((p) => p.id === paqueteId) ?? state.paquetes[0]!;
  if (!ROLES_PAQUETERIA.includes(user.rol) && paq.unidad_id !== user.unidad_activa_id) {
    return jsonResp(403, {
      detail:
        'Solo el conserje o el residente de la unidad destinataria pueden confirmar la entrega.',
    });
  }
  paq.estado = 'ENTREGADO';
  paq.fecha_entrega = '2026-10-30T16:00:00Z';
  paq.retirado_por_id = user.id;
  return jsonResp(200, paq);
}

function handleParcelsRoute(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/paqueteria' && method === 'GET') {
    return withActive(state, (user) => listParcelsForUser(user, state));
  }
  if (path === '/api/paqueteria/registrar' && method === 'POST') {
    return withRoles(state, ROLES_PAQUETERIA, (user) => {
      const unidadId = Number(body.unidad_id ?? 1);
      const ident = state.unidades.find((u) => u.id === unidadId)?.identificador ?? 'A-101';
      const created = {
        id: ++state.nextId,
        unidad_id: unidadId,
        identificador_unidad: ident,
        recibido_por_id: user.id,
        empresa_envio: String(body.empresa_envio ?? 'ZOOM'),
        descripcion: String(body.descripcion ?? 'Paquete registrado'),
        url_foto_evidencia: (body.url_foto_evidencia as string | null) ?? null,
        estado: 'EN_GARITA',
        fecha_recepcion: '2026-10-30T10:00:00Z',
        fecha_entrega: null,
        retirado_por_id: null,
      };
      state.paquetes.unshift(created);
      return jsonResp(201, created);
    });
  }
  const pacMatch = /^\/api\/paqueteria\/(\d+)\/entregar$/.exec(path);
  if (pacMatch && method === 'PUT') {
    return withActive(state, (user) => deliverParcel(Number(pacMatch[1]), user, state));
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
    return withActive(state, () => jsonResp(200, state.areasSociales));
  }
  if (path === '/api/reservas/areas' && method === 'POST') {
    return withRoles(state, ROLES_GESTION_AREAS, () => {
      const area = {
        id: ++state.nextId,
        nombre: String(body.nombre ?? 'Parrillera Norte'),
        aforo_maximo: Number(body.aforo_maximo ?? 30),
        costo_uso_usd: String(body.costo_uso_usd ?? '25.00'),
        deposito_garantia_usd: String(body.deposito_garantia_usd ?? '100.00'),
        requiere_solvencia_estricta: Boolean(body.requiere_solvencia_estricta ?? true),
        es_activa: true,
      };
      state.areasSociales.push(area);
      return jsonResp(201, area);
    });
  }
  return null;
}

function requestReservation(
  user: MockUserProfile,
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
  const unidadId = Number(body.unidad_id ?? user.unidad_activa_id ?? 1);
  const ident = state.unidades.find((u) => u.id === unidadId)?.identificador ?? 'A-101';
  const created: ReservaState = {
    id: ++state.nextId,
    area_id: area.id,
    nombre_area: area.nombre,
    unidad_id: unidadId,
    identificador_unidad: ident,
    solicitante_id: user.id,
    fecha_evento: String(body.fecha_evento ?? '2026-12-20'),
    motivo_evento: String(body.motivo_evento ?? 'Evento familiar'),
    estado: 'CONFIRMADA',
    tarea_inspeccion_id: 88,
    observaciones_inspeccion: null,
    creado_en: '2026-10-30T12:00:00Z',
  };
  state.reservas.unshift(created);
  return jsonResp(201, created);
}

function mutateReservation(
  id: number,
  action: string,
  user: MockUserProfile,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse {
  const reserva = state.reservas.find((r) => r.id === id) ?? state.reservas[0]!;
  if (action === 'cancelar') {
    if (!ROLES_CANCELACION_JUNTA.includes(user.rol) && reserva.solicitante_id !== user.id) {
      return jsonResp(403, { detail: 'No tiene permisos para cancelar esta reserva.' });
    }
    reserva.estado = 'CANCELADA';
    return jsonResp(200, reserva);
  }
  if (!ROLES_INSPECCION_RESERVA.includes(user.rol)) {
    return jsonResp(403, { detail: 'No tiene permisos para ejecutar esta acción.' });
  }
  reserva.estado = String(body.estado ?? 'FINALIZADA_SIN_DANOS');
  reserva.observaciones_inspeccion = String(body.observaciones_inspeccion ?? 'Sin novedades');
  return jsonResp(200, reserva);
}

function handleReservasRoute(
  method: string,
  path: string,
  body: Record<string, unknown>,
  state: CondominioMockState,
): HttpMockResponse | null {
  if (path === '/api/reservas' && method === 'GET') {
    return withActive(state, () => jsonResp(200, state.reservas));
  }
  if (path === '/api/reservas/solicitar' && method === 'POST') {
    return withActive(state, (user) => requestReservation(user, body, state));
  }
  const resMatch = /^\/api\/reservas\/(\d+)\/(inspeccionar|cancelar)$/.exec(path);
  if (resMatch && method === 'PUT') {
    return withActive(state, (user) =>
      mutateReservation(Number(resMatch[1]), resMatch[2]!, user, body, state),
    );
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
    handleComunicadosRoute,
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
  let raw: string | null = null;
  try {
    raw = route.request().postData();
  } catch {
    return {};
  }
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
