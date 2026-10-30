import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { apiClient, ApiError } from '../services/apiClient';
import type { RolUsuario, UsuarioPerfil } from './authStore';

export type TipoEstructura = 'TORRE' | 'BLOQUE' | 'MANZANA' | 'CALLE' | 'EDIFICIO';
export type TipoOcupante = 'PROPIETARIO' | 'INQUILINO';
export type EstadoIncidencia = 'ABIERTO' | 'EN_PROCESO' | 'CERRADO';

export interface UnidadDTO {
  id: number;
  identificador: string;
  estructura_id: number;
  alicuota?: string;
  cuota_fija_usd?: string | null;
  credito_disponible_usd?: string;
}

export interface AlicuotaUpdateDTO {
  alicuota: string;
  cuota_fija_usd?: string | null;
}

export interface EstructuraGenerarRequestDTO {
  nombre: string;
  tipo: TipoEstructura;
  identificadores: string[];
}

export interface EstructuraGenerarResponseDTO {
  estructura_id: number;
  nombre: string;
  tipo: string;
  unidades_creadas: number;
  unidades: UnidadDTO[];
}

export interface UsuarioAsignarRequestDTO {
  unidad_id: number;
  tipo_ocupante: TipoOcupante;
  rol: RolUsuario;
}

export interface JuntaCargoRequestDTO {
  usuario_id: number;
  cargo: 'PRESIDENTE' | 'VICEPRESIDENTE' | 'TESORERO' | 'SECRETARIO' | 'VOCERO';
}

export interface IncidenciaDTO {
  id: number;
  usuario_creador_id: number;
  area: string;
  descripcion: string;
  url_foto: string | null;
  estado: EstadoIncidencia;
  adhesiones_count: number;
}

export interface IncidenciaCreateDTO {
  area: string;
  descripcion: string;
  url_foto?: string | null;
}

export interface TareaDiariaDTO {
  id: number;
  plantilla_id: number | null;
  incidencia_id: number | null;
  titulo: string;
  area: string;
  fecha: string;
  completada: boolean;
  url_evidencia: string | null;
}

export interface FotoVoceroDTO {
  id: number;
  usuario_id: number;
  periodo: string;
  area: string;
  comentario: string;
  url_foto: string;
}

export interface FotoVoceroCreateDTO {
  periodo: string;
  area: string;
  comentario: string;
  url_foto: string;
}

export interface GaleriaVoceroDTO {
  periodo: string;
  fotos_usadas_mes: number;
  limite_mensual: number;
  fotos: FotoVoceroDTO[];
}

export interface BitacoraActaDTO {
  id: number;
  fecha: string;
  hora: string;
  ubicacion: string;
  contenido: string;
  autor_id: number;
}

export interface BitacoraActaCreateDTO {
  fecha: string;
  hora: string;
  ubicacion: string;
  contenido: string;
}

export interface OperationsStateData {
  unidades: UnidadDTO[];
  usuariosPendientes: UsuarioPerfil[];
  incidencias: IncidenciaDTO[];
  tareasDiarias: TareaDiariaDTO[];
  galeriaVoceros: GaleriaVoceroDTO;
  bitacora: BitacoraActaDTO[];
}

export const useOperationsStore = defineStore('operations', () => {
  const data = ref<OperationsStateData>({
    unidades: [
      { id: 1, identificador: 'Apto 1-A', estructura_id: 1 },
      { id: 2, identificador: 'Apto 1-B', estructura_id: 1 },
    ],
    usuariosPendientes: [],
    incidencias: [],
    tareasDiarias: [],
    galeriaVoceros: {
      periodo: '2026-10',
      fotos_usadas_mes: 0,
      limite_mensual: 30,
      fotos: [],
    },
    bitacora: [],
  });

  const isLoading = ref(false);
  const isStale = ref(false);
  const errorMessage = ref<string | null>(null);
  const lastUpdatedAt = ref<number | null>(null);

  const remainingPhotosThisMonth = computed(() =>
    Math.max(
      0,
      data.value.galeriaVoceros.limite_mensual - data.value.galeriaVoceros.fotos_usadas_mes,
    ),
  );
  const isPhotoQuotaExhausted = computed(() => remainingPhotosThisMonth.value === 0);

  async function fetchAdminData(): Promise<void> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const [unidades, pendientes] = await Promise.all([
        apiClient.get<UnidadDTO[]>('/api/estructura/unidades'),
        apiClient.get<UsuarioPerfil[]>('/api/usuarios/pendientes'),
      ]);
      data.value = {
        ...data.value,
        unidades,
        usuariosPendientes: pendientes,
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
    } catch (error) {
      // Anti-Destructive Catch
      isStale.value = true;
      errorMessage.value =
        error instanceof ApiError
          ? error.detail
          : 'No se pudo sincronizar el listado administrativo. Mostrando datos en caché.';
    } finally {
      isLoading.value = false;
    }
  }

  async function generarEstructura(
    payload: EstructuraGenerarRequestDTO,
    idempotencyKey: string,
  ): Promise<EstructuraGenerarResponseDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const created = await apiClient.post<EstructuraGenerarResponseDTO>(
        '/api/estructura/generar',
        payload,
        { idempotencyKey },
      );
      data.value = {
        ...data.value,
        unidades: [...data.value.unidades, ...created.unidades],
      };
      lastUpdatedAt.value = Date.now();
      return created;
    } catch (error) {
      errorMessage.value =
        error instanceof ApiError ? error.detail : 'No se pudo generar la estructura física.';
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function asignarUsuarioFantasma(
    usuarioId: number,
    payload: UsuarioAsignarRequestDTO,
  ): Promise<UsuarioPerfil> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const activated = await apiClient.put<UsuarioPerfil>(
        `/api/usuarios/${usuarioId}/asignar`,
        payload,
      );
      data.value = {
        ...data.value,
        usuariosPendientes: data.value.usuariosPendientes.filter((u) => u.id !== usuarioId),
      };
      lastUpdatedAt.value = Date.now();
      return activated;
    } catch (error) {
      errorMessage.value =
        error instanceof ApiError ? error.detail : 'No se pudo activar al usuario fantasma.';
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function asignarCargoJunta(payload: JuntaCargoRequestDTO): Promise<UsuarioPerfil> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const updated = await apiClient.put<UsuarioPerfil>('/api/junta/cargos', payload);
      lastUpdatedAt.value = Date.now();
      return updated;
    } catch (error) {
      errorMessage.value =
        error instanceof ApiError
          ? error.detail
          : 'No se pudo asignar el cargo en la Junta de Condominio.';
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchIncidencias(): Promise<void> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const list = await apiClient.get<IncidenciaDTO[]>('/api/incidencias/abiertas');
      data.value = {
        ...data.value,
        incidencias: list,
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
    } catch (error) {
      isStale.value = true;
      errorMessage.value =
        error instanceof ApiError
          ? error.detail
          : 'No se pudo actualizar el embudo de incidencias. Mostrando caché local.';
    } finally {
      isLoading.value = false;
    }
  }

  async function crearIncidencia(
    payload: IncidenciaCreateDTO,
    idempotencyKey: string,
  ): Promise<IncidenciaDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const created = await apiClient.post<IncidenciaDTO>('/api/incidencias/crear', payload, {
        idempotencyKey,
      });
      data.value = {
        ...data.value,
        incidencias: [created, ...data.value.incidencias],
      };
      lastUpdatedAt.value = Date.now();
      return created;
    } catch (error) {
      errorMessage.value =
        error instanceof ApiError ? error.detail : 'No se pudo crear el reporte de incidencia.';
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function adherirIncidencia(incidenciaId: number): Promise<IncidenciaDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const updated = await apiClient.post<IncidenciaDTO>(
        `/api/incidencias/${incidenciaId}/adherir`,
        {},
      );
      data.value = {
        ...data.value,
        incidencias: data.value.incidencias
          .map((inc) => (inc.id === incidenciaId ? updated : inc))
          .sort((a, b) => b.adhesiones_count - a.adhesiones_count),
      };
      lastUpdatedAt.value = Date.now();
      return updated;
    } catch (error) {
      errorMessage.value =
        error instanceof ApiError ? error.detail : 'No fue posible sumarse a la incidencia.';
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchTareasDiarias(): Promise<void> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const tareas = await apiClient.get<TareaDiariaDTO[]>('/api/tareas/diarias');
      data.value = {
        ...data.value,
        tareasDiarias: tareas,
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
    } catch (error) {
      isStale.value = true;
      errorMessage.value =
        error instanceof ApiError
          ? error.detail
          : 'No se pudo actualizar el checklist del conserje. Mostrando lista en caché.';
    } finally {
      isLoading.value = false;
    }
  }

  async function completarTareaDiaria(
    tareaId: number,
    urlEvidencia: string | null = null,
  ): Promise<TareaDiariaDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const completed = await apiClient.put<TareaDiariaDTO>(`/api/tareas/${tareaId}/completar`, {
        url_evidencia: urlEvidencia,
      });
      data.value = {
        ...data.value,
        tareasDiarias: data.value.tareasDiarias.map((t) => (t.id === tareaId ? completed : t)),
      };
      lastUpdatedAt.value = Date.now();
      return completed;
    } catch (error) {
      errorMessage.value =
        error instanceof ApiError ? error.detail : 'No se pudo marcar la tarea como completada.';
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchGaleriaVoceros(periodo?: string): Promise<void> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const path = periodo
        ? `/api/voceros/galeria?periodo=${encodeURIComponent(periodo)}`
        : '/api/voceros/galeria';
      const galeria = await apiClient.get<GaleriaVoceroDTO>(path);
      data.value = {
        ...data.value,
        galeriaVoceros: galeria,
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
    } catch (error) {
      isStale.value = true;
      errorMessage.value =
        error instanceof ApiError
          ? error.detail
          : 'No se pudo sincronizar la galería de voceros. Mostrando fotos en caché.';
    } finally {
      isLoading.value = false;
    }
  }

  async function subirFotoVocero(payload: FotoVoceroCreateDTO): Promise<FotoVoceroDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const created = await apiClient.post<FotoVoceroDTO>('/api/voceros/fotos', payload);
      data.value = {
        ...data.value,
        galeriaVoceros: {
          ...data.value.galeriaVoceros,
          fotos_usadas_mes: data.value.galeriaVoceros.fotos_usadas_mes + 1,
          fotos: [created, ...data.value.galeriaVoceros.fotos],
        },
      };
      lastUpdatedAt.value = Date.now();
      return created;
    } catch (error) {
      errorMessage.value =
        error instanceof ApiError ? error.detail : 'No se pudo subir la fotografía de inspección.';
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchBitacora(): Promise<void> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const actas = await apiClient.get<BitacoraActaDTO[]>('/api/bitacora/historial');
      data.value = {
        ...data.value,
        bitacora: actas,
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
    } catch (error) {
      isStale.value = true;
      errorMessage.value =
        error instanceof ApiError
          ? error.detail
          : 'No se pudo cargar el historial de la bitácora. Mostrando actas en caché.';
    } finally {
      isLoading.value = false;
    }
  }

  async function crearActaBitacora(payload: BitacoraActaCreateDTO): Promise<BitacoraActaDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const created = await apiClient.post<BitacoraActaDTO>('/api/bitacora/acta', payload);
      data.value = {
        ...data.value,
        bitacora: [created, ...data.value.bitacora],
      };
      lastUpdatedAt.value = Date.now();
      return created;
    } catch (error) {
      errorMessage.value =
        error instanceof ApiError ? error.detail : 'No se pudo registrar el acta en la bitácora.';
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function actualizarAlicuotaUnidad(
    unidadId: number,
    payload: AlicuotaUpdateDTO,
    idempotencyKey: string,
  ): Promise<UnidadDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const updated = await apiClient.put<UnidadDTO>(
        `/api/estructura/unidades/${unidadId}/alicuota`,
        payload,
        { idempotencyKey },
      );
      data.value = {
        ...data.value,
        unidades: data.value.unidades.map((u) => (u.id === unidadId ? updated : u)),
      };
      lastUpdatedAt.value = Date.now();
      return updated;
    } catch (error) {
      errorMessage.value =
        error instanceof ApiError
          ? error.detail
          : 'No se pudo actualizar la alícuota o cuota fija de la unidad.';
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
    remainingPhotosThisMonth,
    isPhotoQuotaExhausted,
    fetchAdminData,
    generarEstructura,
    asignarUsuarioFantasma,
    asignarCargoJunta,
    fetchIncidencias,
    crearIncidencia,
    adherirIncidencia,
    fetchTareasDiarias,
    completarTareaDiaria,
    fetchGaleriaVoceros,
    subirFotoVocero,
    fetchBitacora,
    crearActaBitacora,
    actualizarAlicuotaUnidad,
  };
});
