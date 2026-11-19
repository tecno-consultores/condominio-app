// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

import http from 'node:http';

const PORT = Number.parseInt(process.env.PORT ?? '8000', 10) || 8000;
const HOST = '0.0.0.0';
const MAX_BODY_BYTES = 2 * 1024 * 1024;
const SESSION_COOKIE_NAME = 'qa_session';
const CSRF_TOKEN = 'qa-csrf-token-11x';

const JUNTA_ROLES = new Set(['PRESIDENTE', 'VICEPRESIDENTE', 'TESORERO', 'SECRETARIO', 'VOCERO']);
const BOARD_ADMIN_ROLES = new Set(['PRESIDENTE', 'VICEPRESIDENTE']);
const TREASURY_ROLES = new Set(['TESORERO', 'PRESIDENTE']);
const QR_VERIFIER_ROLES = new Set(['CONSERJE', 'PRESIDENTE', 'VOCERO']);
const PARCEL_MANAGER_ROLES = new Set(['CONSERJE', 'PRESIDENTE']);
const VOTING_ROLES = new Set([
  'PROPIETARIO',
  'PRESIDENTE',
  'VICEPRESIDENTE',
  'TESORERO',
  'SECRETARIO',
  'VOCERO',
]);

const PROFILES = {
  PROPIETARIO: {
    id: 101,
    nombre: 'Ana Propietaria',
    cedula: 'V-11111111',
    correo: 'propietario@condominio.test',
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
    nombre: 'Lucía Secretaria',
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
    nombre: 'Sofía Fantasma',
    cedula: 'V-88888888',
    correo: 'fantasma@condominio.test',
    telefono: '0414-0000008',
    es_activo: false,
    rol: 'FANTASMA',
    unidad_activa_id: null,
  },
  INQUILINO: {
    id: 109,
    nombre: 'Luis Inquilino',
    cedula: 'V-99999999',
    correo: 'inquilino@condominio.test',
    telefono: '0414-0000009',
    es_activo: true,
    rol: 'INQUILINO',
    unidad_activa_id: 2,
  },
};

const EMAIL_TO_ROLE = {
  'presidente@condominio.test': 'PRESIDENTE',
  'vicepresidente@condominio.test': 'VICEPRESIDENTE',
  'tesorero@condominio.test': 'TESORERO',
  'secretario@condominio.test': 'SECRETARIO',
  'vocero@condominio.test': 'VOCERO',
  'propietario@condominio.test': 'PROPIETARIO',
  'residente@condominio.test': 'PROPIETARIO',
  'inquilino@condominio.test': 'INQUILINO',
  'conserje@condominio.test': 'CONSERJE',
  'fantasma@condominio.test': 'FANTASMA',
};

/** Create initial mutable mock state for QA ephemeral sessions. */
function createInitialState() {
  return {
    nextId: 600,
    tasaUsdVes: '45.50',
    closingActive: false,
    lastRegisteredGhost: null,
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
        credito_disponible_usd: '5.00',
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
      {
        recibo_id: 2,
        unidad_id: 2,
        identificador_unidad: 'A-102',
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
    comunicados: [
      {
        id: 1,
        titulo: 'Mantenimiento Preventivo',
        contenido: 'Lavado de tanques programado para este sábado.',
        enlace_externo: '/consultas',
        url_adjunto: null,
        activo: true,
      },
    ],
    usuariosPendientes: [
      {
        id: 501,
        nombre: 'Marcos Pendiente',
        cedula: 'V-88888888',
        correo: 'marcos.pendiente@condominio.test',
        telefono: '0414-0000008',
        es_activo: false,
        rol: 'FANTASMA',
        unidad_activa_id: null,
      },
    ],
    incidencias: [
      {
        id: 1,
        usuario_creador_id: 101,
        area: 'Bombas de Agua',
        descripcion: 'Fuga menor en sello mecánico de bomba auxiliar',
        url_foto: null,
        estado: 'ABIERTO',
        adhesiones_count: 3,
      },
    ],
    tareas: [
      {
        id: 1,
        plantilla_id: null,
        incidencia_id: 1,
        titulo: 'Inspeccionar presión de bomba auxiliar',
        area: 'Bombas de Agua',
        fecha: '2026-11-18',
        completada: false,
        url_evidencia: null,
      },
    ],
    fotosVoceros: [
      {
        id: 1,
        usuario_id: 106,
        periodo: '2026-11',
        area: 'Cuarto de Bombas',
        comentario: 'Válvulas lubricadas y sin humedad aparente',
        url_foto: '/assets/bomba-ok.avif',
      },
    ],
    bitacora: [
      {
        id: 1,
        fecha: '2026-11-15',
        hora: '19:00',
        ubicacion: 'Salón de Usos Múltiples',
        contenido: 'Aprobación de mantenimiento preventivo anual.',
        autor_id: 105,
      },
    ],
    consultas: [
      {
        id: 1,
        titulo: 'Aprobación de Impermeabilización Azotea Torre A',
        descripcion_legal:
          'Contratación de impermeabilización con manto asfáltico según Art. 23 LPH.',
        tipo_consulta: 'CARTA_CONSULTA_1RA',
        regla_quorum: 'MAYORIA_SIMPLE',
        quorum_minimo_alicuota: '50.0100',
        participacion_alicuota: '42.0000',
        alicuota_aprobatoria: '42.0000',
        total_votos: 4,
        fecha_apertura: '2026-11-01T08:00:00Z',
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
            etiqueta: 'Rechazar y Solicitar Nueva Licitación',
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
        nombre_visitante: 'Técnico Fibra Seed',
        cedula_visitante: 'V-19000111',
        placa_vehiculo: 'AA111BB',
        modalidad: 'UNICO_USO',
        valido_desde: '2026-11-01T00:00:00Z',
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
        descripcion: 'Sobre certificado guía #90012',
        url_foto_evidencia: null,
        estado: 'EN_GARITA',
        fecha_recepcion: '2026-11-18T10:00:00Z',
        fecha_entrega: null,
        retirado_por_id: null,
      },
    ],
    areasSociales: [
      {
        id: 1,
        nombre: 'Salón de Fiestas Principal',
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
        nombre_area: 'Salón de Fiestas Principal',
        unidad_id: 1,
        identificador_unidad: 'A-101',
        solicitante_id: 101,
        fecha_evento: '2026-12-18',
        motivo_evento: 'Reunión Navideña Familiar',
        estado: 'CONFIRMADA',
        tarea_inspeccion_id: 10,
        observaciones_inspeccion: null,
        creado_en: '2026-11-18T09:00:00Z',
      },
    ],
  };
}

function jsonResp(status, body, headers = {}) {
  return { status, body, headers };
}

function parseCookies(cookieHeader) {
  const cookies = {};
  if (!cookieHeader) {
    return cookies;
  }
  for (const part of cookieHeader.split(';')) {
    const idx = part.indexOf('=');
    if (idx <= 0) {
      continue;
    }
    const name = part.slice(0, idx).trim();
    const rawValue = part.slice(idx + 1).trim();
    try {
      cookies[name] = decodeURIComponent(rawValue);
    } catch {
      cookies[name] = rawValue;
    }
  }
  return cookies;
}

function resolveSessionUser(req, state) {
  const cookies = parseCookies(req.headers.cookie);
  const role = cookies[SESSION_COOKIE_NAME];
  if (!role || !Object.hasOwn(PROFILES, role)) {
    return null;
  }
  if (role === 'FANTASMA' && state.lastRegisteredGhost) {
    return state.lastRegisteredGhost;
  }
  return { ...PROFILES[role] };
}

function readRequestBody(req) {
  return new Promise((resolve) => {
    const contentType = String(req.headers['content-type'] ?? '').toLowerCase();
    const chunks = [];
    let totalBytes = 0;

    req.on('data', (chunk) => {
      totalBytes += chunk.length;
      if (totalBytes <= MAX_BODY_BYTES) {
        chunks.push(chunk);
      }
    });

    req.on('end', () => {
      if (chunks.length === 0 || !contentType.includes('application/json')) {
        resolve({});
        return;
      }
      try {
        const parsed = JSON.parse(Buffer.concat(chunks).toString('utf8'));
        resolve(parsed && typeof parsed === 'object' ? parsed : {});
      } catch {
        resolve({});
      }
    });

    req.on('error', () => resolve({}));
  });
}

function requireActiveUser(user) {
  if (!user) {
    return jsonResp(401, { detail: 'No autenticado.' });
  }
  if (!user.es_activo || user.rol === 'FANTASMA') {
    return jsonResp(403, { detail: 'Cuenta en espera de activación por la Junta.' });
  }
  return null;
}

function requireRole(user, allowedRoles, message = 'No posee permisos para esta operación.') {
  const authErr = requireActiveUser(user);
  if (authErr) {
    return authErr;
  }
  if (!allowedRoles.has(user.rol)) {
    return jsonResp(403, { detail: message });
  }
  return null;
}

function findUnitById(state, unitId) {
  return state.unidades.find((u) => u.id === unitId) ?? state.unidades[0];
}

function handleLogin(body) {
  const email = String(body.correo ?? body.username ?? '').trim().toLowerCase();
  const password = String(body.password ?? '');
  const role = EMAIL_TO_ROLE[email];
  if (!role || password.trim().length === 0 || password.length < 8) {
    return jsonResp(401, { detail: 'Credenciales inválidas.' });
  }
  return jsonResp(
    200,
    { message: 'Login exitoso', rol: role, csrf_token: CSRF_TOKEN },
    {
      'Set-Cookie': `${SESSION_COOKIE_NAME}=${role}; Path=/; HttpOnly; SameSite=Lax`,
      'X-CSRF-Token': CSRF_TOKEN,
    },
  );
}

function handleRegister(body, state) {
  const created = {
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
  state.lastRegisteredGhost = created;
  return jsonResp(201, created, {
    'Set-Cookie': `${SESSION_COOKIE_NAME}=FANTASMA; Path=/; HttpOnly; SameSite=Lax`,
    'X-CSRF-Token': CSRF_TOKEN,
  });
}

function handleAuthAndHealth({ method, pathname, body, user, state }) {
  if (pathname === '/health' && method === 'GET') {
    return jsonResp(200, { status: 'ok' });
  }
  if (pathname === '/api/auth/me' && method === 'GET') {
    return user ? jsonResp(200, user) : jsonResp(200, { authenticated: false });
  }
  if (pathname === '/api/auth/login' && method === 'POST') {
    return handleLogin(body);
  }
  if (pathname === '/api/auth/register' && method === 'POST') {
    return handleRegister(body, state);
  }
  if (pathname === '/api/auth/logout' && method === 'POST') {
    state.lastRegisteredGhost = null;
    return jsonResp(
      200,
      { message: 'Sesión cerrada' },
      { 'Set-Cookie': `${SESSION_COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax` },
    );
  }
  if (pathname === '/api/auth/refresh' && method === 'POST') {
    if (!user) {
      return jsonResp(401, { detail: 'Sesión no válida.' });
    }
    return jsonResp(200, { message: 'Sesión renovada', csrf_token: CSRF_TOKEN });
  }
  return null;
}

function computeUserDebtUsd(state, user) {
  const unitId = user.unidad_activa_id ?? 1;
  const total = state.recibos
    .filter((r) => r.unidad_id === unitId)
    .reduce((acc, r) => acc + Number.parseFloat(r.saldo_usd || '0'), 0);
  return total.toFixed(2);
}

function handleFinanceCore({ method, pathname, body, user, state }) {
  if (pathname === '/api/finanzas/tasa' && method === 'GET') {
    return requireActiveUser(user) ?? jsonResp(200, { id: 1, fecha: '2026-11-18', tasa_usd_ves: state.tasaUsdVes });
  }
  if (pathname === '/api/finanzas/tasa' && method === 'POST') {
    const err = requireRole(user, TREASURY_ROLES);
    if (err) return err;
    state.tasaUsdVes = String(body.tasa_usd_ves ?? state.tasaUsdVes);
    return jsonResp(201, { id: 2, fecha: String(body.fecha ?? '2026-11-18'), tasa_usd_ves: state.tasaUsdVes });
  }
  if (pathname === '/api/finanzas/resumen' && method === 'GET') {
    const err = requireActiveUser(user);
    if (err) return err;
    return jsonResp(200, {
      deuda_total_usd: computeUserDebtUsd(state, user),
      total_egresos_usd: '450.00',
      gastos_por_categoria: { 'Bombas de Agua': '250.00', Vigilancia: '200.00' },
      estado_cobranza: state.recibos,
    });
  }
  if (pathname === '/api/finanzas/egresos' && method === 'POST') {
    const err = requireRole(user, TREASURY_ROLES);
    if (err) return err;
    return jsonResp(201, { id: ++state.nextId, monto_usd: String(body.monto ?? '50.00') });
  }
  if (pathname === '/api/finanzas/cierre-mensual' && method === 'POST') {
    const err = requireRole(user, TREASURY_ROLES);
    if (err) return err;
    state.closingActive = true;
    return jsonResp(200, { periodo: String(body.periodo ?? '2026-10'), estado: 'CERRADO' });
  }
  return null;
}

function handleFinanceBillingAndFunds({ method, pathname, body, user, state }) {
  if (pathname === '/api/finanzas/fondos' && method === 'GET') {
    return requireActiveUser(user) ?? jsonResp(200, state.fondos);
  }
  if (pathname === '/api/finanzas/fondos' && method === 'POST') {
    const err = requireRole(user, TREASURY_ROLES);
    if (err) return err;
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
  }
  if (pathname === '/api/finanzas/facturar-periodo' && method === 'POST') {
    const err = requireRole(user, TREASURY_ROLES);
    if (err) return err;
    return jsonResp(201, {
      periodo: String(body.periodo ?? '2026-10'),
      modalidad: String(body.modalidad ?? 'ALICUOTA'),
      recibos_emitidos: state.unidades.length,
      total_egresos_comunes_usd: '450.00',
      recargo_fondo_reserva_usd: '45.00',
      cuota_extraordinaria_total_usd: '0.00',
      total_facturado_bruto_usd: '495.00',
      total_credito_descontado_usd: '0.00',
      total_facturado_neto_usd: '495.00',
      superavit_conciliado_fondo_usd: '0.00',
    });
  }
  return handleReciboAndSolvency({ method, pathname, user, state });
}

function handleReciboAndSolvency({ method, pathname, user, state }) {
  const desgloseMatch = /^\/api\/finanzas\/recibos\/(\d+)\/desglose$/.exec(pathname);
  if (desgloseMatch && method === 'GET') {
    const err = requireActiveUser(user);
    if (err) return err;
    const reciboId = Number(desgloseMatch[1]);
    return jsonResp(200, {
      recibo_id: reciboId,
      unidad_id: 1,
      identificador_unidad: 'A-101',
      alicuota_aplicada: '10.0000',
      periodo: '2026-10',
      monto_usd: '50.00',
      monto_pagado_usd: '0.00',
      saldo_pendiente_usd: '50.00',
      credito_descontado_usd: '0.00',
      estado: 'PENDIENTE',
      bloqueado: state.closingActive,
      items: [
        { id: 1, tipo_item: 'GASTO_COMUN', descripcion: 'Mantenimiento Bombas', monto_usd: '50.00' },
      ],
    });
  }
  const solvEmitMatch = /^\/api\/finanzas\/solvencia\/(\d+)$/.exec(pathname);
  if (solvEmitMatch && method === 'POST') {
    const err = requireActiveUser(user);
    if (err) return err;
    const uid = Number(solvEmitMatch[1]);
    const unit = findUnitById(state, uid);
    return jsonResp(201, {
      id: ++state.nextId,
      jti: `jti-solv-${uid}`,
      folio: `SOLV-202611-000${uid}-ABCD`,
      unidad_id: uid,
      identificador_unidad: unit.identificador,
      emitido_por_id: user.id,
      fecha_emision: '2026-11-18',
      fecha_vencimiento: '2026-12-18',
      deuda_verificada_usd: '0.00',
      firma_hmac: 'hmac_sha256_solvencia_qa_11x',
      qr_token: `SOLV-202611-000${uid}-ABCD.hmac_sha256_solvencia_qa_11x`,
    });
  }
  const solvVerifMatch = /^\/api\/finanzas\/solvencia\/verificar\/([^/]+)$/.exec(pathname);
  if (solvVerifMatch && method === 'GET') {
    return jsonResp(200, {
      valido: true,
      jti: 'jti-solv-1',
      folio: decodeURIComponent(solvVerifMatch[1]),
      unidad_id: 1,
      identificador_unidad: 'A-101',
      fecha_vencimiento: '2026-12-18',
      vigente: true,
      deuda_verificada_usd: '0.00',
      firma_hmac: 'hmac_sha256_solvencia_qa_11x',
    });
  }
  return null;
}

function reportPaymentAction(body, user, state) {
  const err = requireActiveUser(user);
  if (err) return err;
  if (state.closingActive) {
    return jsonResp(409, { detail: 'Periodo contable bloqueado por Candado Contable.' });
  }
  const monto = String(body.monto ?? '50.00');
  const moneda = String(body.moneda ?? 'USD');
  const rate = Number.parseFloat(state.tasaUsdVes) || 45.5;
  const montoUsd = moneda === 'USD' ? monto : (Number.parseFloat(monto) / rate).toFixed(2);
  const pago = {
    id: ++state.nextId,
    recibo_id: Number(body.recibo_id ?? 1),
    usuario_id: user.id,
    monto,
    moneda,
    monto_usd: montoUsd,
    tasa_cambio: state.tasaUsdVes,
    metodo_pago: String(body.metodo_pago ?? 'PAGO_MOVIL'),
    numero_referencia: body.numero_referencia ?? null,
    url_comprobante: body.url_comprobante ?? null,
    estado: 'EN_REVISION',
  };
  state.pagos.push(pago);
  return jsonResp(201, pago);
}

function mutatePaymentAction(pagoId, action, user, state) {
  const err = requireRole(user, TREASURY_ROLES);
  if (err) return err;
  const target = state.pagos.find((p) => p.id === pagoId);
  if (!target) {
    return jsonResp(404, { detail: 'Pago no encontrado.' });
  }
  target.estado = action === 'aprobar' ? 'APROBADO' : 'RECHAZADO';
  const recibo = state.recibos.find((r) => r.recibo_id === target.recibo_id);
  if (action === 'aprobar' && recibo) {
    recibo.estado = 'PAGADO';
    recibo.saldo_usd = '0.00';
  }
  return jsonResp(200, target);
}

function handlePagosRoutes({ method, pathname, body, user, state }) {
  if (pathname === '/api/pagos/revision' && method === 'GET') {
    const err = requireRole(user, TREASURY_ROLES);
    return err ?? jsonResp(200, state.pagos.filter((p) => p.estado === 'EN_REVISION'));
  }
  if (pathname === '/api/pagos/reportar' && method === 'POST') {
    return reportPaymentAction(body, user, state);
  }
  const pagoMatch = /^\/api\/pagos\/(\d+)\/(aprobar|rechazar)$/.exec(pathname);
  if (pagoMatch && method === 'PUT') {
    return mutatePaymentAction(Number(pagoMatch[1]), pagoMatch[2], user, state);
  }
  return null;
}

function handleIncidentsRoutes({ method, pathname, body, user, state }) {
  if (pathname === '/api/incidencias/abiertas' && method === 'GET') {
    return requireActiveUser(user) ?? jsonResp(200, state.incidencias);
  }
  if (pathname === '/api/incidencias/crear' && method === 'POST') {
    const err = requireActiveUser(user);
    if (err) return err;
    const created = {
      id: ++state.nextId,
      usuario_creador_id: user.id,
      area: String(body.area ?? 'General'),
      descripcion: String(body.descripcion ?? 'Falla reportada'),
      url_foto: body.url_foto ?? null,
      estado: 'ABIERTO',
      adhesiones_count: 1,
    };
    state.incidencias.unshift(created);
    return jsonResp(201, created);
  }
  const adherirMatch = /^\/api\/incidencias\/(\d+)\/adherir$/.exec(pathname);
  if (adherirMatch && method === 'POST') {
    const err = requireActiveUser(user);
    if (err) return err;
    const item = state.incidencias.find((i) => i.id === Number(adherirMatch[1])) ?? state.incidencias[0];
    item.adhesiones_count += 1;
    return jsonResp(200, item);
  }
  return null;
}

function handleTasksRoutes({ method, pathname, body, user, state }) {
  if (pathname === '/api/tareas/diarias' && method === 'GET') {
    return requireActiveUser(user) ?? jsonResp(200, state.tareas);
  }
  if (pathname === '/api/tareas/plantillas' && method === 'POST') {
    const err = requireRole(user, JUNTA_ROLES);
    return err ?? jsonResp(201, {
      id: ++state.nextId,
      titulo: String(body.titulo ?? 'Rutina de mantenimiento'),
      area: String(body.area ?? 'General'),
      frecuencia: String(body.frecuencia ?? 'DIARIA'),
      activa: true,
    });
  }
  if (pathname === '/api/tareas/generar-diarias' && method === 'POST') {
    const err = requireRole(user, JUNTA_ROLES);
    return err ?? jsonResp(200, { tareas_generadas: 1 });
  }
  if (pathname === '/api/tareas/diarias' && method === 'POST') {
    const err = requireRole(user, JUNTA_ROLES);
    if (err) return err;
    const created = {
      id: ++state.nextId,
      plantilla_id: null,
      incidencia_id: body.incidencia_id ?? null,
      titulo: String(body.titulo ?? 'Tarea puntual'),
      area: String(body.area ?? 'General'),
      fecha: String(body.fecha ?? '2026-11-18'),
      completada: false,
      url_evidencia: null,
    };
    state.tareas.push(created);
    return jsonResp(201, created);
  }
  const tareaMatch = /^\/api\/tareas\/(\d+)\/completar$/.exec(pathname);
  if (tareaMatch && method === 'PUT') {
    const err = requireRole(user, QR_VERIFIER_ROLES);
    if (err) return err;
    const tarea = state.tareas.find((t) => t.id === Number(tareaMatch[1])) ?? state.tareas[0];
    tarea.completada = true;
    tarea.url_evidencia = body.url_evidencia ?? null;
    return jsonResp(200, tarea);
  }
  return null;
}

function handleCommunityAndMedia({ method, pathname, body, user, state }) {
  if (pathname === '/api/comunicados/recientes' && method === 'GET') {
    return requireActiveUser(user) ?? jsonResp(200, state.comunicados);
  }
  if (pathname === '/api/comunicados' && method === 'POST') {
    const err = requireRole(user, JUNTA_ROLES);
    if (err) return err;
    const created = {
      id: ++state.nextId,
      titulo: String(body.titulo ?? 'Comunicado'),
      contenido: String(body.contenido ?? ''),
      enlace_externo: body.enlace_externo ?? null,
      url_adjunto: null,
      activo: true,
    };
    state.comunicados.unshift(created);
    return jsonResp(201, created);
  }
  if (pathname === '/api/voceros/galeria' && method === 'GET') {
    const err = requireActiveUser(user);
    if (err) return err;
    return jsonResp(200, {
      periodo: '2026-11',
      fotos_usadas_mes: state.fotosVoceros.length,
      limite_mensual: 30,
      fotos: state.fotosVoceros,
    });
  }
  if (pathname === '/api/voceros/fotos' && method === 'POST') {
    const err = requireRole(user, new Set(['VOCERO', 'PRESIDENTE', 'VICEPRESIDENTE']));
    if (err) return err;
    const foto = {
      id: ++state.nextId,
      usuario_id: user.id,
      periodo: String(body.periodo ?? '2026-11'),
      area: String(body.area ?? 'General'),
      comentario: String(body.comentario ?? 'Inspección'),
      url_foto: String(body.url_foto ?? '/assets/voceros-ok.avif'),
    };
    state.fotosVoceros.unshift(foto);
    return jsonResp(201, foto);
  }
  if (pathname === '/api/bitacora/historial' && method === 'GET') {
    return requireActiveUser(user) ?? jsonResp(200, state.bitacora);
  }
  if (pathname === '/api/bitacora/acta' && method === 'POST') {
    const err = requireRole(user, JUNTA_ROLES);
    if (err) return err;
    const acta = {
      id: ++state.nextId,
      fecha: String(body.fecha ?? '2026-11-18'),
      hora: String(body.hora ?? '19:30'),
      ubicacion: String(body.ubicacion ?? 'Salón Social'),
      contenido: String(body.contenido ?? 'Acta asentada'),
      autor_id: user.id,
    };
    state.bitacora.unshift(acta);
    return jsonResp(201, acta);
  }
  if (pathname === '/api/evidencias/subir' && method === 'POST') {
    const err = requireActiveUser(user);
    if (err) return err;
    return jsonResp(202, {
      url: '/api/evidencias/comprobantes/mock.webp',
      mime_origen: 'image/png',
      formato_destino: 'webp',
      bytes_recibidos: 1024,
      estado: 'ENCOLADO',
    });
  }
  return null;
}

function castVoteOnConsultation(consultaId, body, user, state) {
  const err = requireRole(user, VOTING_ROLES, 'Solo propietarios y miembros activos pueden votar.');
  if (err) return err;
  const consulta = state.consultas.find((c) => c.id === consultaId);
  if (!consulta) return jsonResp(404, { detail: 'Consulta no encontrada.' });
  if (consulta.estado !== 'ABIERTA') return jsonResp(409, { detail: 'La consulta no se encuentra abierta.' });

  const option = consulta.opciones.find((o) => o.id === Number(body.opcion_id)) ?? consulta.opciones[0];
  const unit = findUnitById(state, Number(body.unidad_id ?? user.unidad_activa_id ?? 1));
  option.votos_cantidad += 1;
  option.alicuota_acumulada = '52.0000';
  consulta.total_votos += 1;
  consulta.participacion_alicuota = '52.0000';
  consulta.alicuota_aprobatoria = '52.0000';
  consulta.ya_voto_usuario = true;

  const recibo = {
    voto_id: ++state.nextId,
    jti: `jti-voto-${state.nextId}`,
    consulta_id: consulta.id,
    titulo_consulta: consulta.titulo,
    unidad_id: unit.id,
    identificador_unidad: unit.identificador,
    usuario_id: user.id,
    opcion_id: option.id,
    opcion_etiqueta: option.etiqueta,
    alicuota_capturada: unit.alicuota,
    participacion_total_alicuota: consulta.participacion_alicuota,
    quorum_minimo_alicuota: consulta.quorum_minimo_alicuota,
    fecha_voto: new Date().toISOString(),
    ip_hash: 'sha256_qa_mock_ip_hash',
    firma_hmac: 'hmac_sha256_voto_emitido_qa_11x',
    mensaje_verificacion: 'Voto ponderado registrado en urna inmutable.',
  };
  consulta.mi_voto = recibo;
  return jsonResp(201, recibo);
}

function handleGovernanceRoutes({ method, pathname, body, user, state }) {
  if (pathname === '/api/consultas' && method === 'GET') {
    return requireActiveUser(user) ?? jsonResp(200, state.consultas);
  }
  if (pathname === '/api/consultas' && method === 'POST') {
    const err = requireRole(user, new Set(['PRESIDENTE', 'SECRETARIO']));
    if (err) return err;
    const created = {
      ...state.consultas[0],
      id: ++state.nextId,
      titulo: String(body.titulo ?? 'Nueva Carta Consulta'),
      estado: 'ABIERTA',
      participacion_alicuota: '0.0000',
      alicuota_aprobatoria: '0.0000',
      total_votos: 0,
      ya_voto_usuario: false,
      mi_voto: null,
      acta_bitacora_id: null,
    };
    state.consultas.unshift(created);
    return jsonResp(201, created);
  }
  const detailMatch = /^\/api\/consultas\/(\d+)$/.exec(pathname);
  if (detailMatch && method === 'GET') {
    const err = requireActiveUser(user);
    if (err) return err;
    const found = state.consultas.find((c) => c.id === Number(detailMatch[1]));
    return found ? jsonResp(200, found) : jsonResp(404, { detail: 'Consulta no encontrada.' });
  }
  const voteMatch = /^\/api\/consultas\/(\d+)\/votar$/.exec(pathname);
  if (voteMatch && method === 'POST') {
    return castVoteOnConsultation(Number(voteMatch[1]), body, user, state);
  }
  const closeMatch = /^\/api\/consultas\/(\d+)\/cerrar$/.exec(pathname);
  if (closeMatch && method === 'POST') {
    const err = requireRole(user, new Set(['PRESIDENTE', 'SECRETARIO']));
    if (err) return err;
    const consulta = state.consultas.find((c) => c.id === Number(closeMatch[1])) ?? state.consultas[0];
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
      hash_global_escrutinio: 'sha256_escrutinio_qa_11x',
    });
  }
  return null;
}

function verifyQrPassAction(body, user, state) {
  const err = requireRole(user, QR_VERIFIER_ROLES);
  if (err) return err;
  const pase = state.pases.find((p) => p.qr_token === String(body.qr_token ?? '').trim());
  if (!pase || pase.estado !== 'ACTIVO') {
    return jsonResp(409, { detail: 'Pase QR inválido, revocado o ya utilizado (Anti-Replay).' });
  }
  if (pase.modalidad === 'UNICO_USO') {
    pase.estado = 'USADO';
  }
  pase.usado_en = new Date().toISOString();
  pase.verificado_por_id = user.id;
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
    usado_en: pase.usado_en,
    verificado_por_id: user.id,
    mensaje: 'Ingreso autorizado en garita con protección Anti-Replay.',
  });
}

function handleAccessRoutes({ method, pathname, body, user, state }) {
  if (pathname === '/api/accesos/pases/mios' && method === 'GET') {
    return requireActiveUser(user) ?? jsonResp(200, state.pases);
  }
  if (pathname === '/api/accesos/pases' && method === 'POST') {
    const err = requireActiveUser(user);
    if (err) return err;
    const id = ++state.nextId;
    const unit = findUnitById(state, Number(body.unidad_id ?? user.unidad_activa_id ?? 1));
    const pase = {
      id,
      jti: `jti-qa-${id}`,
      unidad_id: unit.id,
      identificador_unidad: unit.identificador,
      creado_por_id: user.id,
      nombre_visitante: String(body.nombre_visitante ?? 'Visitante'),
      cedula_visitante: String(body.cedula_visitante ?? 'V-20000000'),
      placa_vehiculo: body.placa_vehiculo ?? null,
      modalidad: String(body.modalidad ?? 'UNICO_USO'),
      valido_desde: new Date().toISOString(),
      valido_hasta: '2026-12-31T23:59:00Z',
      estado: 'ACTIVO',
      usado_en: null,
      verificado_por_id: null,
      firma_hmac: `hmac_sha256_pase_${id}`,
      qr_token: `qr-qa-${id}.hmac_sha256_pase_${id}`,
    };
    state.pases.unshift(pase);
    return jsonResp(201, pase);
  }
  const revMatch = /^\/api\/accesos\/pases\/(\d+)$/.exec(pathname);
  if (revMatch && method === 'DELETE') {
    const err = requireActiveUser(user);
    if (err) return err;
    const pase = state.pases.find((p) => p.id === Number(revMatch[1]));
    if (!pase) return jsonResp(404, { detail: 'Pase no encontrado.' });
    pase.estado = 'REVOCADO';
    return jsonResp(200, pase);
  }
  if (pathname === '/api/accesos/verificar-qr' && method === 'POST') {
    return verifyQrPassAction(body, user, state);
  }
  return null;
}

function handleParcelsRoutes({ method, pathname, body, user, state }) {
  if (pathname === '/api/paqueteria' && method === 'GET') {
    return requireActiveUser(user) ?? jsonResp(200, state.paquetes);
  }
  if (pathname === '/api/paqueteria/registrar' && method === 'POST') {
    const err = requireRole(user, PARCEL_MANAGER_ROLES);
    if (err) return err;
    const unit = findUnitById(state, Number(body.unidad_id ?? 1));
    const created = {
      id: ++state.nextId,
      unidad_id: unit.id,
      identificador_unidad: unit.identificador,
      recibido_por_id: user.id,
      empresa_envio: String(body.empresa_envio ?? 'ZOOM'),
      descripcion: String(body.descripcion ?? 'Encomienda registrada'),
      url_foto_evidencia: body.url_foto_evidencia ?? null,
      estado: 'EN_GARITA',
      fecha_recepcion: new Date().toISOString(),
      fecha_entrega: null,
      retirado_por_id: null,
    };
    state.paquetes.unshift(created);
    return jsonResp(201, created);
  }
  const deliverMatch = /^\/api\/paqueteria\/(\d+)\/entregar$/.exec(pathname);
  if (deliverMatch && method === 'PUT') {
    const err = requireActiveUser(user);
    if (err) return err;
    const paquete = state.paquetes.find((p) => p.id === Number(deliverMatch[1]));
    if (!paquete) return jsonResp(404, { detail: 'Paquete no encontrado.' });
    paquete.estado = 'ENTREGADO';
    paquete.fecha_entrega = new Date().toISOString();
    paquete.retirado_por_id = user.id;
    return jsonResp(200, paquete);
  }
  return null;
}

function handleAmenitiesRoutes({ method, pathname, body, user, state }) {
  if (pathname === '/api/reservas/areas' && method === 'GET') {
    return requireActiveUser(user) ?? jsonResp(200, state.areasSociales);
  }
  if (pathname === '/api/reservas/areas' && method === 'POST') {
    const err = requireRole(user, TREASURY_ROLES);
    if (err) return err;
    const created = {
      id: ++state.nextId,
      nombre: String(body.nombre ?? 'Parrillera'),
      aforo_maximo: Number(body.aforo_maximo ?? 30),
      costo_uso_usd: String(body.costo_uso_usd ?? '25.00'),
      deposito_garantia_usd: String(body.deposito_garantia_usd ?? '100.00'),
      requiere_solvencia_estricta: Boolean(body.requiere_solvencia_estricta ?? true),
      es_activa: true,
    };
    state.areasSociales.push(created);
    return jsonResp(201, created);
  }
  if (pathname === '/api/reservas' && method === 'GET') {
    return requireActiveUser(user) ?? jsonResp(200, state.reservas);
  }
  if (pathname === '/api/reservas/solicitar' && method === 'POST') {
    const err = requireActiveUser(user);
    if (err) return err;
    const area = state.areasSociales.find((a) => a.id === Number(body.area_id)) ?? state.areasSociales[0];
    const unit = findUnitById(state, Number(body.unidad_id ?? user.unidad_activa_id ?? 1));
    const created = {
      id: ++state.nextId,
      area_id: area.id,
      nombre_area: area.nombre,
      unidad_id: unit.id,
      identificador_unidad: unit.identificador,
      solicitante_id: user.id,
      fecha_evento: String(body.fecha_evento ?? '2026-12-20'),
      motivo_evento: String(body.motivo_evento ?? 'Evento familiar'),
      estado: 'CONFIRMADA',
      tarea_inspeccion_id: 88,
      observaciones_inspeccion: null,
      creado_en: new Date().toISOString(),
    };
    state.reservas.unshift(created);
    return jsonResp(201, created);
  }
  const resMatch = /^\/api\/reservas\/(\d+)\/(inspeccionar|cancelar)$/.exec(pathname);
  if (resMatch && method === 'PUT') {
    const err = resMatch[2] === 'inspeccionar'
      ? requireRole(user, new Set(['CONSERJE', 'PRESIDENTE', 'TESORERO']))
      : requireActiveUser(user);
    if (err) return err;
    const reserva = state.reservas.find((r) => r.id === Number(resMatch[1])) ?? state.reservas[0];
    if (resMatch[2] === 'cancelar') {
      reserva.estado = 'CANCELADA';
    } else {
      reserva.estado = String(body.estado ?? 'FINALIZADA_SIN_DANOS');
      reserva.observaciones_inspeccion = String(body.observaciones_inspeccion ?? 'Sin novedades');
    }
    return jsonResp(200, reserva);
  }
  return null;
}

function handleStructureRoutes({ method, pathname, body, user, state }) {
  if (pathname === '/api/estructura/unidades' && method === 'GET') {
    const isJunta = Boolean(user && user.es_activo && JUNTA_ROLES.has(user.rol));
    const list = state.unidades.map((u) =>
      isJunta ? u : { id: u.id, identificador: u.identificador, estructura_id: u.estructura_id },
    );
    return jsonResp(200, list);
  }
  if (pathname === '/api/estructura/generar' && method === 'POST') {
    const err = requireRole(user, BOARD_ADMIN_ROLES);
    if (err) return err;
    const ids = Array.isArray(body.identificadores) ? body.identificadores : ['B-101'];
    const createdUnits = ids.map((identificador) => ({
      id: ++state.nextId,
      identificador: String(identificador),
      estructura_id: 2,
      alicuota: '10.0000',
      cuota_fija_usd: null,
      credito_disponible_usd: '0.00',
    }));
    state.unidades.push(...createdUnits);
    return jsonResp(201, {
      estructura_id: 2,
      nombre: String(body.nombre ?? 'Torre Nueva'),
      tipo: String(body.tipo ?? 'TORRE'),
      unidades_creadas: createdUnits.length,
      unidades: createdUnits,
    });
  }
  const alicuotaMatch = /^\/api\/estructura\/unidades\/(\d+)\/alicuota$/.exec(pathname);
  if (alicuotaMatch && method === 'PUT') {
    const err = requireRole(user, BOARD_ADMIN_ROLES);
    if (err) return err;
    const unit = findUnitById(state, Number(alicuotaMatch[1]));
    unit.alicuota = String(body.alicuota ?? unit.alicuota);
    unit.cuota_fija_usd = body.cuota_fija_usd ?? unit.cuota_fija_usd;
    return jsonResp(200, unit);
  }
  return null;
}

function handleUsersAndBoardRoutes({ method, pathname, body, user, state }) {
  if (pathname === '/api/usuarios/pendientes' && method === 'GET') {
    return requireRole(user, BOARD_ADMIN_ROLES) ?? jsonResp(200, state.usuariosPendientes);
  }
  const assignMatch = /^\/api\/usuarios\/(\d+)\/asignar$/.exec(pathname);
  if (assignMatch && method === 'PUT') {
    const err = requireRole(user, BOARD_ADMIN_ROLES);
    if (err) return err;
    const uid = Number(assignMatch[1]);
    const pending = state.usuariosPendientes.find((u) => u.id === uid);
    if (!pending) return jsonResp(404, { detail: 'Usuario pendiente no encontrado.' });
    state.usuariosPendientes = state.usuariosPendientes.filter((u) => u.id !== uid);
    return jsonResp(200, {
      ...pending,
      es_activo: true,
      rol: String(body.rol ?? 'PROPIETARIO'),
      unidad_activa_id: Number(body.unidad_id ?? 1),
    });
  }
  if (pathname === '/api/junta/cargos' && method === 'PUT') {
    const err = requireRole(user, new Set(['PRESIDENTE']));
    if (err) return err;
    return jsonResp(200, {
      ...PROFILES.PROPIETARIO,
      id: Number(body.usuario_id ?? 101),
      rol: String(body.cargo ?? 'TESORERO'),
    });
  }
  return null;
}

const ROUTE_HANDLERS = [
  handleAuthAndHealth,
  handleFinanceCore,
  handleFinanceBillingAndFunds,
  handlePagosRoutes,
  handleIncidentsRoutes,
  handleTasksRoutes,
  handleCommunityAndMedia,
  handleGovernanceRoutes,
  handleAccessRoutes,
  handleParcelsRoutes,
  handleAmenitiesRoutes,
  handleStructureRoutes,
  handleUsersAndBoardRoutes,
];

function routeRequest(ctx) {
  for (const handler of ROUTE_HANDLERS) {
    const response = handler(ctx);
    if (response) {
      return response;
    }
  }
  return jsonResp(404, { detail: `Ruta no implementada en QA mock: ${ctx.method} ${ctx.pathname}` });
}

function sendJson(res, response) {
  const payload = JSON.stringify(response.body);
  res.writeHead(response.status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
    ...response.headers,
  });
  res.end(payload);
}

function setupGracefulShutdown(server) {
  const shutdown = () => {
    server.close(() => process.exit(0));
    setTimeout(() => process.exit(0), 3000).unref();
  };
  process.on('SIGTERM', shutdown);
  process.on('SIGINT', shutdown);
}

const state = createInitialState();

const server = http.createServer(async (req, res) => {
  const method = String(req.method ?? 'GET').toUpperCase();
  const parsedUrl = new URL(req.url || '/', 'http://127.0.0.1');
  const pathname = parsedUrl.pathname;
  const user = resolveSessionUser(req, state);
  const body = method === 'GET' || method === 'HEAD' ? {} : await readRequestBody(req);
  const response = routeRequest({ method, pathname, body, user, state });
  sendJson(res, response);
});

setupGracefulShutdown(server);
server.listen(PORT, HOST, () => {
  process.stdout.write(`qa-api-mock listening on http://${HOST}:${PORT}\n`);
});
