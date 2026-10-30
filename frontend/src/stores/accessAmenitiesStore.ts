import { defineStore } from 'pinia';
import { ref } from 'vue';
import { apiRequest } from '../services/apiClient';
import { generateIdempotencyKey, sanitizeUntrustedText } from '../utils/security';

export type ModalidadPaseQR = 'UNICO_USO' | 'VENTANA_TEMPORAL';
export type EstadoPaseQR = 'ACTIVO' | 'USADO' | 'REVOCADO' | 'EXPIRADO';
export type EstadoPaquete = 'EN_GARITA' | 'ENTREGADO';
export type ResultadoInspeccionReserva = 'FINALIZADA_SIN_DANOS' | 'FINALIZADA_CON_DANOS';
export type EstadoReservaArea =
  'CONFIRMADA' | 'FINALIZADA_SIN_DANOS' | 'FINALIZADA_CON_DANOS' | 'CANCELADA';

export interface PaseVisitaCreateDTO {
  unidad_id: number;
  nombre_visitante: string;
  cedula_visitante: string;
  placa_vehiculo?: string | null;
  modalidad: ModalidadPaseQR;
  horas_validez: number;
}

export interface PaseVisitaDTO {
  id: number;
  jti: string;
  unidad_id: number;
  identificador_unidad: string;
  creado_por_id: number;
  nombre_visitante: string;
  cedula_visitante: string;
  placa_vehiculo: string | null;
  modalidad: ModalidadPaseQR;
  valido_desde: string;
  valido_hasta: string;
  estado: EstadoPaseQR;
  usado_en: string | null;
  verificado_por_id: number | null;
  firma_hmac: string;
  qr_token: string;
}

export interface VerificarPaseQRResponseDTO {
  autorizado: boolean;
  pase_id: number;
  jti: string;
  unidad_id: number;
  identificador_unidad: string;
  nombre_visitante: string;
  cedula_visitante: string;
  placa_vehiculo: string | null;
  modalidad: ModalidadPaseQR;
  estado: EstadoPaseQR;
  usado_en: string;
  verificado_por_id: number;
  mensaje: string;
}

export interface PaqueteCreateDTO {
  unidad_id: number;
  empresa_envio: string;
  descripcion: string;
  url_foto_evidencia?: string | null;
}

export interface PaqueteDTO {
  id: number;
  unidad_id: number;
  identificador_unidad: string;
  recibido_por_id: number;
  empresa_envio: string;
  descripcion: string;
  url_foto_evidencia: string | null;
  estado: EstadoPaquete;
  fecha_recepcion: string;
  fecha_entrega: string | null;
  retirado_por_id: number | null;
}

export interface AreaSocialCreateDTO {
  nombre: string;
  aforo_maximo: number;
  costo_uso_usd: string;
  deposito_garantia_usd: string;
  requiere_solvencia_estricta: boolean;
}

export interface AreaSocialDTO {
  id: number;
  nombre: string;
  aforo_maximo: number;
  costo_uso_usd: string;
  deposito_garantia_usd: string;
  requiere_solvencia_estricta: boolean;
  es_activa: boolean;
}

export interface ReservaAreaCreateDTO {
  area_id: number;
  unidad_id: number;
  fecha_evento: string;
  motivo_evento: string;
}

export interface ReservaInspeccionarDTO {
  estado: ResultadoInspeccionReserva;
  observaciones_inspeccion: string;
}

export interface ReservaAreaDTO {
  id: number;
  area_id: number;
  nombre_area: string;
  unidad_id: number;
  identificador_unidad: string;
  solicitante_id: number;
  fecha_evento: string;
  motivo_evento: string;
  estado: EstadoReservaArea;
  tarea_inspeccion_id: number | null;
  observaciones_inspeccion: string | null;
  creado_en: string;
}

function sanitizePase(item: PaseVisitaDTO): PaseVisitaDTO {
  return {
    ...item,
    identificador_unidad: sanitizeUntrustedText(item.identificador_unidad),
    nombre_visitante: sanitizeUntrustedText(item.nombre_visitante),
    cedula_visitante: sanitizeUntrustedText(item.cedula_visitante),
    placa_vehiculo: item.placa_vehiculo ? sanitizeUntrustedText(item.placa_vehiculo) : null,
  };
}

function sanitizePaquete(item: PaqueteDTO): PaqueteDTO {
  return {
    ...item,
    identificador_unidad: sanitizeUntrustedText(item.identificador_unidad),
    empresa_envio: sanitizeUntrustedText(item.empresa_envio),
    descripcion: sanitizeUntrustedText(item.descripcion),
  };
}

function sanitizeAreaSocial(item: AreaSocialDTO): AreaSocialDTO {
  return {
    ...item,
    nombre: sanitizeUntrustedText(item.nombre),
  };
}

function sanitizeReserva(item: ReservaAreaDTO): ReservaAreaDTO {
  return {
    ...item,
    nombre_area: sanitizeUntrustedText(item.nombre_area),
    identificador_unidad: sanitizeUntrustedText(item.identificador_unidad),
    motivo_evento: sanitizeUntrustedText(item.motivo_evento),
    observaciones_inspeccion: item.observaciones_inspeccion
      ? sanitizeUntrustedText(item.observaciones_inspeccion)
      : null,
  };
}

export const useAccessAmenitiesStore = defineStore('accessAmenities', () => {
  const pases = ref<PaseVisitaDTO[]>([]);
  const ultimoPaseCreado = ref<PaseVisitaDTO | null>(null);
  const ultimoEscaneo = ref<VerificarPaseQRResponseDTO | null>(null);
  const paquetes = ref<PaqueteDTO[]>([]);
  const areasSociales = ref<AreaSocialDTO[]>([]);
  const reservas = ref<ReservaAreaDTO[]>([]);
  const isLoading = ref(false);
  const isStale = ref(false);
  const error = ref<string | null>(null);

  async function fetchMisPases(): Promise<PaseVisitaDTO[]> {
    isLoading.value = true;
    error.value = null;
    try {
      const data = await apiRequest<PaseVisitaDTO[]>('/api/accesos/pases/mios');
      const limpios = data.map(sanitizePase);
      pases.value = limpios;
      isStale.value = false;
      return limpios;
    } catch (err) {
      isStale.value = true;
      error.value = err instanceof Error ? err.message : 'Error al cargar los pases de visita QR';
      return pases.value;
    } finally {
      isLoading.value = false;
    }
  }

  async function crearPaseVisita(payload: PaseVisitaCreateDTO): Promise<PaseVisitaDTO> {
    isLoading.value = true;
    error.value = null;
    try {
      const data = await apiRequest<PaseVisitaDTO>('/api/accesos/pases', {
        method: 'POST',
        body: payload,
        idempotencyKey: generateIdempotencyKey(),
      });
      const limpio = sanitizePase(data);
      ultimoPaseCreado.value = limpio;
      pases.value = [limpio, ...pases.value.filter((p) => p.id !== limpio.id)];
      isStale.value = false;
      return limpio;
    } catch (err) {
      isStale.value = true;
      error.value = err instanceof Error ? err.message : 'Error al emitir el pase de visita QR';
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  async function revocarPaseVisita(paseId: number): Promise<PaseVisitaDTO> {
    isLoading.value = true;
    error.value = null;
    try {
      const data = await apiRequest<PaseVisitaDTO>(`/api/accesos/pases/${paseId}`, {
        method: 'DELETE',
      });
      const limpio = sanitizePase(data);
      pases.value = pases.value.map((p) => (p.id === paseId ? limpio : p));
      if (ultimoPaseCreado.value && ultimoPaseCreado.value.id === paseId) {
        ultimoPaseCreado.value = limpio;
      }
      isStale.value = false;
      return limpio;
    } catch (err) {
      isStale.value = true;
      error.value = err instanceof Error ? err.message : 'Error al revocar el pase de visita';
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  async function verificarPaseQR(qrToken: string): Promise<VerificarPaseQRResponseDTO> {
    isLoading.value = true;
    error.value = null;
    try {
      const data = await apiRequest<VerificarPaseQRResponseDTO>('/api/accesos/verificar-qr', {
        method: 'POST',
        body: { qr_token: qrToken.trim() },
        idempotencyKey: generateIdempotencyKey(),
      });
      const limpio: VerificarPaseQRResponseDTO = {
        ...data,
        identificador_unidad: sanitizeUntrustedText(data.identificador_unidad),
        nombre_visitante: sanitizeUntrustedText(data.nombre_visitante),
        cedula_visitante: sanitizeUntrustedText(data.cedula_visitante),
        placa_vehiculo: data.placa_vehiculo ? sanitizeUntrustedText(data.placa_vehiculo) : null,
        mensaje: sanitizeUntrustedText(data.mensaje),
      };
      ultimoEscaneo.value = limpio;
      isStale.value = false;
      return limpio;
    } catch (err) {
      isStale.value = true;
      error.value = err instanceof Error ? err.message : 'Error al verificar el código QR';
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchPaqueteria(): Promise<PaqueteDTO[]> {
    isLoading.value = true;
    error.value = null;
    try {
      const data = await apiRequest<PaqueteDTO[]>('/api/paqueteria');
      const limpios = data.map(sanitizePaquete);
      paquetes.value = limpios;
      isStale.value = false;
      return limpios;
    } catch (err) {
      isStale.value = true;
      error.value = err instanceof Error ? err.message : 'Error al cargar la paquetería en garita';
      return paquetes.value;
    } finally {
      isLoading.value = false;
    }
  }

  async function registrarPaquete(payload: PaqueteCreateDTO): Promise<PaqueteDTO> {
    isLoading.value = true;
    error.value = null;
    try {
      const data = await apiRequest<PaqueteDTO>('/api/paqueteria/registrar', {
        method: 'POST',
        body: payload,
        idempotencyKey: generateIdempotencyKey(),
      });
      const limpio = sanitizePaquete(data);
      paquetes.value = [limpio, ...paquetes.value.filter((p) => p.id !== limpio.id)];
      isStale.value = false;
      return limpio;
    } catch (err) {
      isStale.value = true;
      error.value =
        err instanceof Error ? err.message : 'Error al registrar la encomienda en garita';
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  async function confirmarEntregaPaquete(paqueteId: number): Promise<PaqueteDTO> {
    isLoading.value = true;
    error.value = null;
    try {
      const data = await apiRequest<PaqueteDTO>(`/api/paqueteria/${paqueteId}/entregar`, {
        method: 'PUT',
      });
      const limpio = sanitizePaquete(data);
      paquetes.value = paquetes.value.map((p) => (p.id === paqueteId ? limpio : p));
      isStale.value = false;
      return limpio;
    } catch (err) {
      isStale.value = true;
      error.value =
        err instanceof Error ? err.message : 'Error al confirmar la entrega del paquete';
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchAreasSociales(): Promise<AreaSocialDTO[]> {
    isLoading.value = true;
    error.value = null;
    try {
      const data = await apiRequest<AreaSocialDTO[]>('/api/reservas/areas');
      const limpias = data.map(sanitizeAreaSocial);
      areasSociales.value = limpias;
      isStale.value = false;
      return limpias;
    } catch (err) {
      isStale.value = true;
      error.value = err instanceof Error ? err.message : 'Error al cargar las áreas sociales';
      return areasSociales.value;
    } finally {
      isLoading.value = false;
    }
  }

  async function crearAreaSocial(payload: AreaSocialCreateDTO): Promise<AreaSocialDTO> {
    isLoading.value = true;
    error.value = null;
    try {
      const data = await apiRequest<AreaSocialDTO>('/api/reservas/areas', {
        method: 'POST',
        body: payload,
        idempotencyKey: generateIdempotencyKey(),
      });
      const limpia = sanitizeAreaSocial(data);
      areasSociales.value = [...areasSociales.value.filter((a) => a.id !== limpia.id), limpia];
      isStale.value = false;
      return limpia;
    } catch (err) {
      isStale.value = true;
      error.value = err instanceof Error ? err.message : 'Error al crear el área social';
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchReservas(): Promise<ReservaAreaDTO[]> {
    isLoading.value = true;
    error.value = null;
    try {
      const data = await apiRequest<ReservaAreaDTO[]>('/api/reservas');
      const limpias = data.map(sanitizeReserva);
      reservas.value = limpias;
      isStale.value = false;
      return limpias;
    } catch (err) {
      isStale.value = true;
      error.value =
        err instanceof Error ? err.message : 'Error al cargar el calendario de reservas';
      return reservas.value;
    } finally {
      isLoading.value = false;
    }
  }

  async function solicitarReservaArea(payload: ReservaAreaCreateDTO): Promise<ReservaAreaDTO> {
    isLoading.value = true;
    error.value = null;
    try {
      const data = await apiRequest<ReservaAreaDTO>('/api/reservas/solicitar', {
        method: 'POST',
        body: payload,
        idempotencyKey: generateIdempotencyKey(),
      });
      const limpia = sanitizeReserva(data);
      reservas.value = [limpia, ...reservas.value.filter((r) => r.id !== limpia.id)];
      isStale.value = false;
      return limpia;
    } catch (err) {
      isStale.value = true;
      error.value =
        err instanceof Error ? err.message : 'Error al solicitar la reserva del área social';
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  async function inspeccionarReserva(
    reservaId: number,
    payload: ReservaInspeccionarDTO,
  ): Promise<ReservaAreaDTO> {
    isLoading.value = true;
    error.value = null;
    try {
      const data = await apiRequest<ReservaAreaDTO>(`/api/reservas/${reservaId}/inspeccionar`, {
        method: 'PUT',
        body: payload,
      });
      const limpia = sanitizeReserva(data);
      reservas.value = reservas.value.map((r) => (r.id === reservaId ? limpia : r));
      isStale.value = false;
      return limpia;
    } catch (err) {
      isStale.value = true;
      error.value =
        err instanceof Error
          ? err.message
          : 'Error al registrar la inspección post-evento del área social';
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  return {
    pases,
    ultimoPaseCreado,
    ultimoEscaneo,
    paquetes,
    areasSociales,
    reservas,
    isLoading,
    isStale,
    error,
    fetchMisPases,
    crearPaseVisita,
    revocarPaseVisita,
    verificarPaseQR,
    fetchPaqueteria,
    registrarPaquete,
    confirmarEntregaPaquete,
    fetchAreasSociales,
    crearAreaSocial,
    fetchReservas,
    solicitarReservaArea,
    inspeccionarReserva,
  };
});
