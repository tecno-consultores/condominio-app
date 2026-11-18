import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { apiClient, ApiError } from '../services/apiClient';
import { compareDecimal, divideDecimalHalfUp, multiplyDecimalHalfUp } from '../utils/decimal';
import { generateIdempotencyKey } from '../utils/security';
import { registerSessionResetter } from './authStore';
import { resolveStoreError } from './storeErrors';

export type MonedaPago = 'USD' | 'VES';
export type MetodoPago = 'PAGO_MOVIL' | 'TRANSFERENCIA' | 'ZELLE' | 'EFECTIVO';
export type EstadoPago = 'EN_REVISION' | 'APROBADO' | 'RECHAZADO';
export type EstadoRecibo =
  'PENDIENTE' | 'ABONO_PARCIAL' | 'SOLVENTE' | 'MOROSO' | 'PAGADO' | 'PAGADO_PARCIAL';
export type ModalidadFacturacion = 'ALICUOTA' | 'CUOTA_FIJA' | 'PARTES_IGUALES';
export type TipoFondoCondominio = 'RESERVA_LEGAL' | 'CAJA_CHICA' | 'ESPECIAL';
export type CategoriaEvidencia = 'comprobantes' | 'incidencias' | 'tareas' | 'voceros';

export interface TasaCambioDTO {
  id?: number;
  fecha: string;
  tasa_usd_ves: string;
}

export interface EstadoCobranzaItemDTO {
  recibo_id?: number;
  unidad_id: number;
  periodo: string;
  monto_usd?: string;
  estado: EstadoRecibo;
  saldo_usd: string;
}

export interface ResumenFinancieroDTO {
  deuda_total_usd: string;
  total_egresos_usd: string;
  gastos_por_categoria: Record<string, string>;
  estado_cobranza: EstadoCobranzaItemDTO[];
}

export interface PagoDTO {
  id: number;
  recibo_id: number;
  usuario_id: number;
  monto: string;
  moneda: MonedaPago;
  monto_usd: string;
  tasa_cambio: string;
  metodo_pago: MetodoPago;
  numero_referencia: string | null;
  url_comprobante: string | null;
  estado: EstadoPago;
}

export interface PagoReportarDTO {
  recibo_id: number;
  monto: string;
  moneda: MonedaPago;
  metodo_pago: MetodoPago;
  numero_referencia: string | null;
  url_comprobante?: string | null;
}

export interface EgresoCreateDTO {
  periodo: string;
  categoria: string;
  descripcion: string;
  monto: string;
  moneda: MonedaPago;
  url_factura?: string | null;
  incidencia_id?: number | null;
  es_gasto_comun?: boolean;
}

export interface ComunicadoDTO {
  id: number;
  titulo: string;
  contenido: string;
  enlace_externo?: string | null;
  url_adjunto?: string | null;
  activo?: boolean;
}

export interface ComunicadoCreateDTO {
  titulo: string;
  contenido: string;
  enlace_externo?: string | null;
}

export interface EvidenciaUploadResponseDTO {
  url: string;
  mime_origen: string;
  formato_destino: string;
  bytes_recibidos: number;
  estado: string;
}

export interface CierreMensualDTO {
  periodo: string;
  estado: 'PRELIMINAR' | 'CERRADO';
}

export interface FondoCondominioDTO {
  id: number;
  nombre: string;
  tipo: TipoFondoCondominio;
  porcentaje_recargo: string;
  saldo_actual_usd: string;
  es_activo: boolean;
}

export interface FondoCondominioCreateDTO {
  nombre: string;
  tipo: TipoFondoCondominio;
  porcentaje_recargo: string;
}

export interface FacturarPeriodoRequestDTO {
  periodo: string;
  modalidad: ModalidadFacturacion;
  monto_cuota_fija_usd?: string | null;
  incluir_fondo_reserva?: boolean;
  cuota_extraordinaria_total_usd?: string;
  descripcion_cuota_extraordinaria?: string | null;
}

export interface FacturarPeriodoResponseDTO {
  periodo: string;
  modalidad: ModalidadFacturacion;
  recibos_emitidos: number;
  total_egresos_comunes_usd: string;
  recargo_fondo_reserva_usd: string;
  cuota_extraordinaria_total_usd: string;
  total_facturado_bruto_usd: string;
  total_credito_descontado_usd: string;
  total_facturado_neto_usd: string;
  superavit_conciliado_fondo_usd: string;
}

export interface ReciboItemDTO {
  id: number;
  recibo_id: number;
  tipo_item: string;
  descripcion: string;
  monto_usd: string;
}

export interface ReciboDesgloseDTO {
  recibo_id: number;
  unidad_id: number;
  identificador_unidad: string;
  alicuota_aplicada: string;
  periodo: string;
  monto_usd: string;
  monto_pagado_usd: string;
  saldo_pendiente_usd: string;
  credito_descontado_usd: string;
  estado: string;
  bloqueado: boolean;
  items: ReciboItemDTO[];
}

export interface CertificadoSolvenciaDTO {
  id: number;
  jti?: string;
  folio: string;
  unidad_id: number;
  identificador_unidad: string;
  emitido_por_id: number;
  fecha_emision: string;
  fecha_vencimiento: string;
  deuda_verificada_usd: string;
  firma_hmac: string;
  qr_token: string;
}

export interface VerificarSolvenciaDTO {
  valido: boolean;
  jti?: string;
  folio: string;
  unidad_id: number;
  identificador_unidad: string;
  fecha_vencimiento: string;
  vigente: boolean;
  deuda_verificada_usd: string;
  firma_hmac: string;
}

export interface FinanceStateData {
  tasaActiva: TasaCambioDTO | null;
  resumen: ResumenFinancieroDTO | null;
  pagosEnRevision: PagoDTO[];
  comunicados: ComunicadoDTO[];
  ultimoCierre: CierreMensualDTO | null;
  fondos: FondoCondominioDTO[];
  ultimaFacturacion: FacturarPeriodoResponseDTO | null;
  desgloseActivo: ReciboDesgloseDTO | null;
  certificadoSolvenciaActivo: CertificadoSolvenciaDTO | null;
  verificacionSolvencia: VerificarSolvenciaDTO | null;
}

function createInitialFinanceData(): FinanceStateData {
  return {
    tasaActiva: null,
    resumen: null,
    pagosEnRevision: [],
    comunicados: [],
    ultimoCierre: null,
    fondos: [],
    ultimaFacturacion: null,
    desgloseActivo: null,
    certificadoSolvenciaActivo: null,
    verificacionSolvencia: null,
  };
}

export function convertUsdToVes(usdAmount: string | number, rateUsdVes: string | number): string {
  if (compareDecimal(rateUsdVes, '0') <= 0) {
    return '0.00';
  }
  return multiplyDecimalHalfUp(usdAmount, rateUsdVes, 2);
}

export function convertVesToUsd(vesAmount: string | number, rateUsdVes: string | number): string {
  if (compareDecimal(rateUsdVes, '0') <= 0) {
    return '0.00';
  }
  return divideDecimalHalfUp(vesAmount, rateUsdVes, 2);
}

export function determinePaymentCoverage(
  montoAbonoUsd: number | string,
  saldoPendienteUsd: number | string,
): 'PAGO_TOTAL' | 'ABONO_PARCIAL' {
  if (compareDecimal(montoAbonoUsd, '0') <= 0 || compareDecimal(saldoPendienteUsd, '0') <= 0) {
    return 'ABONO_PARCIAL';
  }
  return compareDecimal(montoAbonoUsd, saldoPendienteUsd) >= 0 ? 'PAGO_TOTAL' : 'ABONO_PARCIAL';
}

export const useFinanceStore = defineStore('finance', () => {
  const data = ref<FinanceStateData>(createInitialFinanceData());
  const isLoading = ref(false);
  const isStale = ref(false);
  const errorMessage = ref<string | null>(null);
  const lastUpdatedAt = ref<number | null>(null);

  const activeRateValue = computed<string | null>(
    () => data.value.tasaActiva?.tasa_usd_ves ?? null,
  );
  const isPeriodClosed = computed(() => data.value.ultimoCierre?.estado === 'CERRADO');

  function resetState(): void {
    data.value = createInitialFinanceData();
    isLoading.value = false;
    isStale.value = false;
    errorMessage.value = null;
    lastUpdatedAt.value = null;
  }

  registerSessionResetter(resetState);

  async function handleStoreError(
    error: unknown,
    fallbackMessage: string,
    isGetOperation = false,
    hasCachedData = false,
  ): Promise<void> {
    const res = await resolveStoreError(error, fallbackMessage, {
      isGetOperation,
      hasCachedData,
    });
    isStale.value = res.isStale;
    errorMessage.value = res.message;
  }

  function hasDashboardCache(): boolean {
    return (
      data.value.tasaActiva !== null ||
      data.value.resumen !== null ||
      data.value.comunicados.length > 0
    );
  }

  async function fetchDashboardData(): Promise<void> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const [tasaRes, resumenRes, comunicadosRes] = await Promise.allSettled([
        apiClient.get<TasaCambioDTO>('/api/finanzas/tasa'),
        apiClient.get<ResumenFinancieroDTO>('/api/finanzas/resumen'),
        apiClient.get<ComunicadoDTO[]>('/api/comunicados/recientes'),
      ]);

      const rejectedReasons = [tasaRes, resumenRes, comunicadosRes]
        .filter((r): r is PromiseRejectedResult => r.status === 'rejected')
        .map((r) => r.reason);

      const unauthorizedErr = rejectedReasons.find(
        (reason) => reason instanceof ApiError && reason.status === 401,
      );
      if (unauthorizedErr) {
        await handleStoreError(unauthorizedErr, 'Sesión expirada.', true, hasDashboardCache());
        return;
      }

      if (tasaRes.status === 'fulfilled' && tasaRes.value) {
        data.value = { ...data.value, tasaActiva: tasaRes.value };
      } else if (
        tasaRes.status === 'rejected' &&
        tasaRes.reason instanceof ApiError &&
        tasaRes.reason.status === 404
      ) {
        // Ausencia matutina de tasa oficial BCV es estado nominal esperable (HTTP 404)
        data.value = { ...data.value, tasaActiva: null };
      }

      if (comunicadosRes.status === 'fulfilled' && Array.isArray(comunicadosRes.value)) {
        data.value = { ...data.value, comunicados: comunicadosRes.value };
      }

      if (resumenRes.status === 'fulfilled' && resumenRes.value) {
        data.value = { ...data.value, resumen: resumenRes.value };
        isStale.value = false;
        lastUpdatedAt.value = Date.now();
        return;
      }

      if (resumenRes.status === 'rejected') {
        await handleStoreError(
          resumenRes.reason,
          'No se pudo sincronizar el resumen financiero. Mostrando últimos datos conocidos.',
          true,
          hasDashboardCache(),
        );
      }
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchComunicadosRecientes(): Promise<ComunicadoDTO[]> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const comunicados = await apiClient.get<ComunicadoDTO[]>('/api/comunicados/recientes');
      data.value = {
        ...data.value,
        comunicados: Array.isArray(comunicados) ? comunicados : [],
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return data.value.comunicados;
    } catch (error) {
      await handleStoreError(
        error,
        'No se pudieron cargar los comunicados recientes.',
        true,
        data.value.comunicados.length > 0,
      );
      return data.value.comunicados;
    } finally {
      isLoading.value = false;
    }
  }

  async function publicarComunicado(
    payload: ComunicadoCreateDTO,
    idempotencyKey: string = generateIdempotencyKey(),
  ): Promise<ComunicadoDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const created = await apiClient.post<ComunicadoDTO>('/api/comunicados', payload, {
        idempotencyKey,
      });
      data.value = {
        ...data.value,
        comunicados: [created, ...data.value.comunicados],
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return created;
    } catch (error) {
      await handleStoreError(error, 'No se pudo publicar el comunicado oficial.');
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function subirEvidencia(
    archivo: File,
    categoria: CategoriaEvidencia,
    idempotencyKey: string = generateIdempotencyKey(),
  ): Promise<EvidenciaUploadResponseDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const formData = new FormData();
      formData.append('archivo', archivo);
      const uploaded = await apiClient.post<EvidenciaUploadResponseDTO>(
        `/api/evidencias/subir?categoria=${encodeURIComponent(categoria)}`,
        formData,
        { idempotencyKey },
      );
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return uploaded;
    } catch (error) {
      await handleStoreError(error, 'No se pudo subir el archivo de evidencia.');
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchPagosEnRevision(): Promise<void> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const pagos = await apiClient.get<PagoDTO[]>('/api/pagos/revision');
      data.value = {
        ...data.value,
        pagosEnRevision: pagos,
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
    } catch (error) {
      await handleStoreError(
        error,
        'Error al consultar pagos en revisión. Mostrando lista en caché.',
        true,
        data.value.pagosEnRevision.length > 0,
      );
    } finally {
      isLoading.value = false;
    }
  }

  async function registrarTasa(
    tasaUsdVes: string,
    fecha?: string,
    idempotencyKey: string = generateIdempotencyKey(),
  ): Promise<TasaCambioDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const payload = fecha ? { tasa_usd_ves: tasaUsdVes, fecha } : { tasa_usd_ves: tasaUsdVes };
      const nuevaTasa = await apiClient.post<TasaCambioDTO>('/api/finanzas/tasa', payload, {
        idempotencyKey,
      });
      data.value = {
        ...data.value,
        tasaActiva: nuevaTasa,
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return nuevaTasa;
    } catch (error) {
      await handleStoreError(error, 'No se pudo registrar la tasa BCV del día.');
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function registrarEgreso(
    payload: EgresoCreateDTO,
    idempotencyKey: string = generateIdempotencyKey(),
  ): Promise<{ id: number; monto_usd: string }> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const result = await apiClient.post<{ id: number; monto_usd: string }>(
        '/api/finanzas/egresos',
        payload,
        { idempotencyKey },
      );
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return result;
    } catch (error) {
      await handleStoreError(error, 'No se pudo registrar el egreso.');
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function reportarPago(
    payload: PagoReportarDTO,
    idempotencyKey: string = generateIdempotencyKey(),
  ): Promise<PagoDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const created = await apiClient.post<PagoDTO>('/api/pagos/reportar', payload, {
        idempotencyKey,
      });
      data.value = {
        ...data.value,
        pagosEnRevision: [created, ...data.value.pagosEnRevision],
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return created;
    } catch (error) {
      await handleStoreError(error, 'No se pudo reportar el pago.');
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function aprobarPago(
    pagoId: number,
    idempotencyKey: string = generateIdempotencyKey(),
  ): Promise<PagoDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const updated = await apiClient.put<PagoDTO>(
        `/api/pagos/${pagoId}/aprobar`,
        {},
        { idempotencyKey },
      );
      data.value = {
        ...data.value,
        pagosEnRevision: data.value.pagosEnRevision.filter((p) => p.id !== pagoId),
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return updated;
    } catch (error) {
      await handleStoreError(error, 'No se pudo aprobar el pago seleccionado.');
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function rechazarPago(
    pagoId: number,
    motivo: string,
    idempotencyKey: string = generateIdempotencyKey(),
  ): Promise<PagoDTO> {
    const cleanMotivo = motivo.trim();
    if (cleanMotivo.length < 5) {
      const msg = 'El motivo de rechazo debe tener al menos 5 caracteres.';
      isStale.value = false;
      errorMessage.value = msg;
      throw new ApiError(422, msg);
    }

    isLoading.value = true;
    errorMessage.value = null;
    try {
      const updated = await apiClient.put<PagoDTO>(
        `/api/pagos/${pagoId}/rechazar`,
        { motivo: cleanMotivo },
        { idempotencyKey },
      );
      data.value = {
        ...data.value,
        pagosEnRevision: data.value.pagosEnRevision.filter((p) => p.id !== pagoId),
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return updated;
    } catch (error) {
      await handleStoreError(error, 'No se pudo rechazar el pago seleccionado.');
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function ejecutarCierreMensual(
    periodo: string,
    idempotencyKey: string = generateIdempotencyKey(),
  ): Promise<CierreMensualDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const cierre = await apiClient.post<CierreMensualDTO>(
        '/api/finanzas/cierre-mensual',
        { periodo },
        { idempotencyKey },
      );
      data.value = {
        ...data.value,
        ultimoCierre: cierre,
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return cierre;
    } catch (error) {
      await handleStoreError(error, 'No se pudo ejecutar el cierre mensual (Candado Contable).');
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchFondos(): Promise<void> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const fondos = await apiClient.get<FondoCondominioDTO[]>('/api/finanzas/fondos');
      data.value = {
        ...data.value,
        fondos,
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
    } catch (error) {
      await handleStoreError(
        error,
        'No se pudieron sincronizar los fondos patrimoniales. Mostrando datos en caché.',
        true,
        data.value.fondos.length > 0,
      );
    } finally {
      isLoading.value = false;
    }
  }

  async function crearFondo(
    payload: FondoCondominioCreateDTO,
    idempotencyKey: string = generateIdempotencyKey(),
  ): Promise<FondoCondominioDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const created = await apiClient.post<FondoCondominioDTO>('/api/finanzas/fondos', payload, {
        idempotencyKey,
      });
      data.value = {
        ...data.value,
        fondos: [...data.value.fondos, created],
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return created;
    } catch (error) {
      await handleStoreError(error, 'No se pudo crear el fondo patrimonial.');
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function facturarPeriodo(
    payload: FacturarPeriodoRequestDTO,
    idempotencyKey: string = generateIdempotencyKey(),
  ): Promise<FacturarPeriodoResponseDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const res = await apiClient.post<FacturarPeriodoResponseDTO>(
        '/api/finanzas/facturar-periodo',
        payload,
        { idempotencyKey },
      );
      data.value = {
        ...data.value,
        ultimaFacturacion: res,
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return res;
    } catch (error) {
      await handleStoreError(error, 'No se pudo emitir la facturación del periodo seleccionado.');
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchReciboDesglose(reciboId: number): Promise<ReciboDesgloseDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const desglose = await apiClient.get<ReciboDesgloseDTO>(
        `/api/finanzas/recibos/${reciboId}/desglose`,
      );
      data.value = {
        ...data.value,
        desgloseActivo: desglose,
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return desglose;
    } catch (error) {
      await handleStoreError(
        error,
        'No se pudo consultar el desglose del recibo seleccionado.',
        true,
        data.value.desgloseActivo !== null,
      );
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function emitirCertificadoSolvencia(
    unidadId: number,
    idempotencyKey: string = generateIdempotencyKey(),
  ): Promise<CertificadoSolvenciaDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const cert = await apiClient.post<CertificadoSolvenciaDTO>(
        `/api/finanzas/solvencia/${unidadId}`,
        {},
        { idempotencyKey },
      );
      data.value = {
        ...data.value,
        certificadoSolvenciaActivo: cert,
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return cert;
    } catch (error) {
      await handleStoreError(
        error,
        'No se pudo emitir el Certificado de Solvencia para la unidad indicada.',
      );
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function verificarCertificadoSolvencia(
    folio: string,
    sig: string,
  ): Promise<VerificarSolvenciaDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const path = `/api/finanzas/solvencia/verificar/${encodeURIComponent(folio.trim())}?sig=${encodeURIComponent(sig.trim())}`;
      const res = await apiClient.get<VerificarSolvenciaDTO>(path);
      data.value = {
        ...data.value,
        verificacionSolvencia: res,
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return res;
    } catch (error) {
      await handleStoreError(
        error,
        'No se pudo verificar el Certificado de Solvencia.',
        true,
        data.value.verificacionSolvencia !== null,
      );
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  return {
    data,
    isLoading,
    isStale,
    errorMessage,
    lastUpdatedAt,
    activeRateValue,
    isPeriodClosed,
    resetState,
    fetchDashboardData,
    fetchComunicadosRecientes,
    publicarComunicado,
    subirEvidencia,
    fetchPagosEnRevision,
    registrarTasa,
    registrarEgreso,
    reportarPago,
    aprobarPago,
    rechazarPago,
    ejecutarCierreMensual,
    fetchFondos,
    crearFondo,
    facturarPeriodo,
    fetchReciboDesglose,
    emitirCertificadoSolvencia,
    verificarCertificadoSolvencia,
  };
});

export const useFinanzasStore = useFinanceStore;
