import { defineStore } from 'pinia';
import { ref } from 'vue';
import { apiRequest } from '../services/apiClient';
import { generateIdempotencyKey, sanitizeUntrustedText } from '../utils/security';

export type TipoConsulta =
  'CARTA_CONSULTA_1RA' | 'CARTA_CONSULTA_2DA' | 'ASAMBLEA_ORDINARIA' | 'ASAMBLEA_EXTRAORDINARIA';

export type ReglaQuorum = 'DOS_TERCIOS' | 'MAYORIA_SIMPLE' | 'UNANIMIDAD';

export type EstadoConsulta =
  'ABIERTA' | 'CERRADA_APROBADA' | 'CERRADA_RECHAZADA' | 'CERRADA_SIN_QUORUM';

export interface OpcionConsultaCreateDTO {
  etiqueta: string;
  es_opcion_aprobatoria: boolean;
}

export interface ConsultaCreateDTO {
  titulo: string;
  descripcion_legal: string;
  tipo_consulta: TipoConsulta;
  regla_quorum: ReglaQuorum;
  fecha_cierre: string;
  opciones: OpcionConsultaCreateDTO[];
}

export interface OpcionConsultaResultadoDTO {
  id: number;
  etiqueta: string;
  es_opcion_aprobatoria: boolean;
  votos_cantidad: number;
  alicuota_acumulada: string;
}

export interface VotoReciboResumenDTO {
  voto_id: number;
  unidad_id: number;
  identificador_unidad: string;
  opcion_id: number;
  opcion_etiqueta: string;
  alicuota_capturada: string;
  fecha_voto: string;
  firma_hmac: string;
}

export interface ConsultaResumenDTO {
  id: number;
  titulo: string;
  descripcion_legal: string;
  tipo_consulta: TipoConsulta;
  regla_quorum: ReglaQuorum;
  quorum_minimo_alicuota: string;
  participacion_alicuota: string;
  alicuota_aprobatoria: string;
  total_votos: number;
  fecha_apertura: string;
  fecha_cierre: string;
  estado: EstadoConsulta;
  creada_por_id: number;
  acta_bitacora_id: number | null;
  ya_voto_usuario: boolean;
}

export interface ConsultaDetalleDTO extends ConsultaResumenDTO {
  opciones: OpcionConsultaResultadoDTO[];
  mi_voto: VotoReciboResumenDTO | null;
}

export interface VotarConsultaDTO {
  unidad_id: number;
  opcion_id: number;
}

export interface ReciboVotoDTO {
  voto_id: number;
  consulta_id: number;
  titulo_consulta: string;
  unidad_id: number;
  identificador_unidad: string;
  usuario_id: number;
  opcion_id: number;
  opcion_etiqueta: string;
  alicuota_capturada: string;
  participacion_total_alicuota: string;
  quorum_minimo_alicuota: string;
  fecha_voto: string;
  ip_hash: string;
  firma_hmac: string;
  mensaje_verificacion: string;
}

export interface CerrarConsultaDTO {
  consulta_id: number;
  titulo: string;
  estado: EstadoConsulta;
  regla_quorum: ReglaQuorum;
  quorum_minimo_alicuota: string;
  participacion_alicuota: string;
  alicuota_aprobatoria: string;
  total_votos: number;
  acta_bitacora_id: number;
  hash_global_escrutinio: string;
}

function sanitizeResumen(item: ConsultaResumenDTO): ConsultaResumenDTO {
  return {
    ...item,
    titulo: sanitizeUntrustedText(item.titulo),
    descripcion_legal: sanitizeUntrustedText(item.descripcion_legal),
  };
}

function sanitizeDetalle(item: ConsultaDetalleDTO): ConsultaDetalleDTO {
  return {
    ...sanitizeResumen(item),
    opciones: item.opciones.map((op) => ({
      ...op,
      etiqueta: sanitizeUntrustedText(op.etiqueta),
    })),
    mi_voto: item.mi_voto
      ? {
          ...item.mi_voto,
          identificador_unidad: sanitizeUntrustedText(item.mi_voto.identificador_unidad),
          opcion_etiqueta: sanitizeUntrustedText(item.mi_voto.opcion_etiqueta),
        }
      : null,
  };
}

export const useGovernanceStore = defineStore('governance', () => {
  const consultas = ref<ConsultaResumenDTO[]>([]);
  const consultaActual = ref<ConsultaDetalleDTO | null>(null);
  const ultimoReciboVoto = ref<ReciboVotoDTO | null>(null);
  const ultimoCierre = ref<CerrarConsultaDTO | null>(null);
  const isLoading = ref(false);
  const isStale = ref(false);
  const error = ref<string | null>(null);

  async function fetchConsultas(): Promise<ConsultaResumenDTO[]> {
    isLoading.value = true;
    error.value = null;
    try {
      const data = await apiRequest<ConsultaResumenDTO[]>('/api/consultas');
      const limpias = data.map(sanitizeResumen);
      consultas.value = limpias;
      isStale.value = false;
      return limpias;
    } catch (err) {
      isStale.value = true;
      error.value = err instanceof Error ? err.message : 'Error al cargar las Cartas Consulta';
      return consultas.value;
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchConsultaDetalle(consultaId: number): Promise<ConsultaDetalleDTO> {
    isLoading.value = true;
    error.value = null;
    try {
      const data = await apiRequest<ConsultaDetalleDTO>(`/api/consultas/${consultaId}`);
      const limpia = sanitizeDetalle(data);
      consultaActual.value = limpia;
      isStale.value = false;
      return limpia;
    } catch (err) {
      isStale.value = true;
      error.value =
        err instanceof Error ? err.message : 'Error al cargar el detalle de la consulta';
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  async function crearConsulta(payload: ConsultaCreateDTO): Promise<ConsultaDetalleDTO> {
    isLoading.value = true;
    error.value = null;
    try {
      const data = await apiRequest<ConsultaDetalleDTO>('/api/consultas', {
        method: 'POST',
        body: payload,
        idempotencyKey: generateIdempotencyKey(),
      });
      const limpia = sanitizeDetalle(data);
      consultaActual.value = limpia;
      consultas.value = [limpia, ...consultas.value.filter((c) => c.id !== limpia.id)];
      isStale.value = false;
      return limpia;
    } catch (err) {
      isStale.value = true;
      error.value = err instanceof Error ? err.message : 'Error al convocar la Carta Consulta';
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  async function votarConsulta(
    consultaId: number,
    payload: VotarConsultaDTO,
  ): Promise<ReciboVotoDTO> {
    isLoading.value = true;
    error.value = null;
    try {
      const recibo = await apiRequest<ReciboVotoDTO>(`/api/consultas/${consultaId}/votar`, {
        method: 'POST',
        body: payload,
        idempotencyKey: generateIdempotencyKey(),
      });
      ultimoReciboVoto.value = recibo;
      if (consultaActual.value && consultaActual.value.id === consultaId) {
        consultaActual.value = {
          ...consultaActual.value,
          participacion_alicuota: recibo.participacion_total_alicuota,
          total_votos: consultaActual.value.total_votos + 1,
          ya_voto_usuario: true,
          mi_voto: {
            voto_id: recibo.voto_id,
            unidad_id: recibo.unidad_id,
            identificador_unidad: recibo.identificador_unidad,
            opcion_id: recibo.opcion_id,
            opcion_etiqueta: recibo.opcion_etiqueta,
            alicuota_capturada: recibo.alicuota_capturada,
            fecha_voto: recibo.fecha_voto,
            firma_hmac: recibo.firma_hmac,
          },
        };
      }
      isStale.value = false;
      return recibo;
    } catch (err) {
      isStale.value = true;
      error.value = err instanceof Error ? err.message : 'Error al registrar el voto';
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  async function cerrarConsulta(consultaId: number): Promise<CerrarConsultaDTO> {
    isLoading.value = true;
    error.value = null;
    try {
      const cierre = await apiRequest<CerrarConsultaDTO>(`/api/consultas/${consultaId}/cerrar`, {
        method: 'POST',
        idempotencyKey: generateIdempotencyKey(),
      });
      ultimoCierre.value = cierre;
      if (consultaActual.value && consultaActual.value.id === consultaId) {
        consultaActual.value = {
          ...consultaActual.value,
          estado: cierre.estado,
          participacion_alicuota: cierre.participacion_alicuota,
          alicuota_aprobatoria: cierre.alicuota_aprobatoria,
          total_votos: cierre.total_votos,
          acta_bitacora_id: cierre.acta_bitacora_id,
        };
      }
      consultas.value = consultas.value.map((c) =>
        c.id === consultaId
          ? {
              ...c,
              estado: cierre.estado,
              participacion_alicuota: cierre.participacion_alicuota,
              alicuota_aprobatoria: cierre.alicuota_aprobatoria,
              total_votos: cierre.total_votos,
              acta_bitacora_id: cierre.acta_bitacora_id,
            }
          : c,
      );
      isStale.value = false;
      return cierre;
    } catch (err) {
      isStale.value = true;
      error.value = err instanceof Error ? err.message : 'Error al cerrar la Carta Consulta';
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  return {
    consultas,
    consultaActual,
    ultimoReciboVoto,
    ultimoCierre,
    isLoading,
    isStale,
    error,
    fetchConsultas,
    fetchConsultaDetalle,
    crearConsulta,
    votarConsulta,
    cerrarConsulta,
  };
});
