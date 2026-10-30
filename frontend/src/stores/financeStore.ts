import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { apiClient, ApiError } from '../services/apiClient';

export type MonedaPago = 'USD' | 'VES';
export type MetodoPago = 'PAGO_MOVIL' | 'TRANSFERENCIA' | 'ZELLE' | 'EFECTIVO';
export type EstadoPago = 'EN_REVISION' | 'APROBADO' | 'RECHAZADO';
export type EstadoRecibo = 'PENDIENTE' | 'ABONO_PARCIAL' | 'SOLVENTE' | 'MOROSO';

export interface TasaCambioDTO {
  id: number;
  fecha: string;
  tasa_usd_ves: string;
}

export interface EstadoCobranzaItemDTO {
  unidad_id: number;
  periodo: string;
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
}

export interface ComunicadoDTO {
  id: number;
  titulo: string;
  contenido: string;
  url_adjunto?: string | null;
}

export interface CierreMensualDTO {
  periodo: string;
  estado: 'PRELIMINAR' | 'CERRADO';
}

export interface FinanceStateData {
  tasaActiva: TasaCambioDTO | null;
  resumen: ResumenFinancieroDTO | null;
  pagosEnRevision: PagoDTO[];
  comunicados: ComunicadoDTO[];
  ultimoCierre: CierreMensualDTO | null;
}

export function convertUsdToVes(usdAmount: string | number, rateUsdVes: string | number): string {
  const usd = typeof usdAmount === 'number' ? usdAmount : Number.parseFloat(usdAmount);
  const rate = typeof rateUsdVes === 'number' ? rateUsdVes : Number.parseFloat(rateUsdVes);
  if (!Number.isFinite(usd) || !Number.isFinite(rate) || rate <= 0) {
    return '0.00';
  }
  return (usd * rate).toFixed(2);
}

export function convertVesToUsd(vesAmount: string | number, rateUsdVes: string | number): string {
  const ves = typeof vesAmount === 'number' ? vesAmount : Number.parseFloat(vesAmount);
  const rate = typeof rateUsdVes === 'number' ? rateUsdVes : Number.parseFloat(rateUsdVes);
  if (!Number.isFinite(ves) || !Number.isFinite(rate) || rate <= 0) {
    return '0.00';
  }
  return (ves / rate).toFixed(2);
}

export function determinePaymentCoverage(
  montoAbonoUsd: number,
  saldoPendienteUsd: number,
): 'PAGO_TOTAL' | 'ABONO_PARCIAL' {
  if (montoAbonoUsd <= 0 || saldoPendienteUsd <= 0) {
    return 'ABONO_PARCIAL';
  }
  return montoAbonoUsd + 0.0001 >= saldoPendienteUsd ? 'PAGO_TOTAL' : 'ABONO_PARCIAL';
}

export const useFinanceStore = defineStore('finance', () => {
  const data = ref<FinanceStateData>({
    tasaActiva: {
      id: 1,
      fecha: '2026-10-29',
      tasa_usd_ves: '36.50',
    },
    resumen: {
      deuda_total_usd: '0.00',
      total_egresos_usd: '0.00',
      gastos_por_categoria: {},
      estado_cobranza: [],
    },
    pagosEnRevision: [],
    comunicados: [],
    ultimoCierre: null,
  });

  const isLoading = ref(false);
  const isStale = ref(false);
  const errorMessage = ref<string | null>(null);
  const lastUpdatedAt = ref<number | null>(null);

  const activeRateValue = computed(() => data.value.tasaActiva?.tasa_usd_ves ?? '36.50');
  const isPeriodClosed = computed(() => data.value.ultimoCierre?.estado === 'CERRADO');

  async function fetchDashboardData(): Promise<void> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const [tasa, resumen] = await Promise.all([
        apiClient.get<TasaCambioDTO>('/api/finanzas/tasa'),
        apiClient.get<ResumenFinancieroDTO>('/api/finanzas/resumen'),
      ]);
      data.value = {
        ...data.value,
        tasaActiva: tasa,
        resumen,
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
    } catch (error) {
      // Anti-Destructive Catch: preserva data.value intacto y marca isStale = true
      isStale.value = true;
      errorMessage.value =
        error instanceof ApiError
          ? error.detail
          : 'No se pudo sincronizar el resumen financiero. Mostrando últimos datos conocidos.';
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
      isStale.value = true;
      errorMessage.value =
        error instanceof ApiError
          ? error.detail
          : 'Error al consultar pagos en revisión. Mostrando lista en caché.';
    } finally {
      isLoading.value = false;
    }
  }

  async function registrarTasa(tasaUsdVes: string, fecha?: string): Promise<TasaCambioDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const payload = fecha ? { tasa_usd_ves: tasaUsdVes, fecha } : { tasa_usd_ves: tasaUsdVes };
      const nuevaTasa = await apiClient.post<TasaCambioDTO>('/api/finanzas/tasa', payload);
      data.value = {
        ...data.value,
        tasaActiva: nuevaTasa,
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return nuevaTasa;
    } catch (error) {
      errorMessage.value =
        error instanceof ApiError ? error.detail : 'No se pudo registrar la tasa BCV del día.';
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function registrarEgreso(
    payload: EgresoCreateDTO,
  ): Promise<{ id: number; monto_usd: string }> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const result = await apiClient.post<{ id: number; monto_usd: string }>(
        '/api/finanzas/egresos',
        payload,
      );
      lastUpdatedAt.value = Date.now();
      return result;
    } catch (error) {
      errorMessage.value =
        error instanceof ApiError ? error.detail : 'No se pudo registrar el egreso.';
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function reportarPago(payload: PagoReportarDTO, idempotencyKey: string): Promise<PagoDTO> {
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
      lastUpdatedAt.value = Date.now();
      return created;
    } catch (error) {
      errorMessage.value =
        error instanceof ApiError ? error.detail : 'No se pudo reportar el pago.';
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function aprobarPago(pagoId: number): Promise<PagoDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const updated = await apiClient.put<PagoDTO>(`/api/pagos/${pagoId}/aprobar`, {});
      data.value = {
        ...data.value,
        pagosEnRevision: data.value.pagosEnRevision.filter((p) => p.id !== pagoId),
      };
      lastUpdatedAt.value = Date.now();
      return updated;
    } catch (error) {
      errorMessage.value =
        error instanceof ApiError ? error.detail : 'No se pudo aprobar el pago seleccionado.';
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function rechazarPago(pagoId: number, motivo: string): Promise<PagoDTO> {
    const cleanMotivo = motivo.trim();
    if (cleanMotivo.length < 5) {
      const msg = 'El motivo de rechazo debe tener al menos 5 caracteres.';
      errorMessage.value = msg;
      throw new ApiError(422, msg);
    }

    isLoading.value = true;
    errorMessage.value = null;
    try {
      const updated = await apiClient.put<PagoDTO>(`/api/pagos/${pagoId}/rechazar`, {
        motivo: cleanMotivo,
      });
      data.value = {
        ...data.value,
        pagosEnRevision: data.value.pagosEnRevision.filter((p) => p.id !== pagoId),
      };
      lastUpdatedAt.value = Date.now();
      return updated;
    } catch (error) {
      errorMessage.value =
        error instanceof ApiError ? error.detail : 'No se pudo rechazar el pago seleccionado.';
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function ejecutarCierreMensual(periodo: string): Promise<CierreMensualDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const cierre = await apiClient.post<CierreMensualDTO>('/api/finanzas/cierre-mensual', {
        periodo,
      });
      data.value = {
        ...data.value,
        ultimoCierre: cierre,
      };
      lastUpdatedAt.value = Date.now();
      return cierre;
    } catch (error) {
      errorMessage.value =
        error instanceof ApiError
          ? error.detail
          : 'No se pudo ejecutar el cierre mensual (Candado Contable).';
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
    fetchDashboardData,
    fetchPagosEnRevision,
    registrarTasa,
    registrarEgreso,
    reportarPago,
    aprobarPago,
    rechazarPago,
    ejecutarCierreMensual,
  };
});

export const useFinanzasStore = useFinanceStore;
