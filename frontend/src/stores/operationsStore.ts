import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { apiClient } from '../services/apiClient';
import { generateIdempotencyKey } from '../utils/security';
import { registerSessionResetter, type RolUsuario, type UsuarioPerfil } from './authStore';
import { resolveStoreError } from './storeErrors';

export type TipoEstructura = 'TORRE' | 'BLOQUE' | 'MANZANA' | 'CALLE' | 'EDIFICIO';
export type TipoOcupante = 'PROPIETARIO' | 'INQUILINO';
export type EstadoIncidencia = 'ABIERTO' | 'EN_PROCESO' | 'CERRADO';
export type RolResidente = Exclude<RolUsuario, 'FANTASMA'>;
export type FrecuenciaTarea = 'DIARIA' | 'SEMANAL' | 'MENSUAL';

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
  rol: RolResidente;
  puede_votar_asamblea?: boolean | null;
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

export interface PlantillaTareaCreateDTO {
  titulo: string;
  area: string;
  frecuencia?: FrecuenciaTarea;
}

export interface PlantillaTareaDTO {
  id: number;
  titulo: string;
  area: string;
  frecuencia: string;
  activa: boolean;
}

export interface TareaDiariaCreateDTO {
  titulo: string;
  area: string;
  fecha?: string | null;
  incidencia_id?: number | null;
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

function getCurrentPeriodIso(): string {
  return new Date().toISOString().slice(0, 7);
}

function createInitialOperationsData(): OperationsStateData {
  return {
    unidades: [],
    usuariosPendientes: [],
    incidencias: [],
    tareasDiarias: [],
    galeriaVoceros: {
      periodo: getCurrentPeriodIso(),
      fotos_usadas_mes: 0,
      limite_mensual: 30,
      fotos: [],
    },
    bitacora: [],
  };
}

export const useOperationsStore = defineStore('operations', () => {
  const data = ref<OperationsStateData>(createInitialOperationsData());
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

  function resetState(): void {
    data.value = createInitialOperationsData();
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

  async function fetchUnidades(): Promise<UnidadDTO[]> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const unidades = await apiClient.get<UnidadDTO[]>('/api/estructura/unidades');
      data.value = {
        ...data.value,
        unidades,
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return unidades;
    } catch (error) {
      await handleStoreError(
        error,
        'No se pudieron cargar las unidades del condominio.',
        true,
        data.value.unidades.length > 0,
      );
      return data.value.unidades;
    } finally {
      isLoading.value = false;
    }
  }

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
      await handleStoreError(
        error,
        'No se pudo sincronizar el listado administrativo. Mostrando datos en caché.',
        true,
        data.value.unidades.length > 0 || data.value.usuariosPendientes.length > 0,
      );
    } finally {
      isLoading.value = false;
    }
  }

  async function generarEstructura(
    payload: EstructuraGenerarRequestDTO,
    idempotencyKey: string = generateIdempotencyKey(),
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
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return created;
    } catch (error) {
      await handleStoreError(error, 'No se pudo generar la estructura física.');
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function asignarUsuarioFantasma(
    usuarioId: number,
    payload: UsuarioAsignarRequestDTO,
    idempotencyKey: string = generateIdempotencyKey(),
  ): Promise<UsuarioPerfil> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const activated = await apiClient.put<UsuarioPerfil>(
        `/api/usuarios/${usuarioId}/asignar`,
        payload,
        { idempotencyKey },
      );
      data.value = {
        ...data.value,
        usuariosPendientes: data.value.usuariosPendientes.filter((u) => u.id !== usuarioId),
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return activated;
    } catch (error) {
      await handleStoreError(error, 'No se pudo activar al usuario fantasma.');
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function asignarCargoJunta(
    payload: JuntaCargoRequestDTO,
    idempotencyKey: string = generateIdempotencyKey(),
  ): Promise<UsuarioPerfil> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const updated = await apiClient.put<UsuarioPerfil>('/api/junta/cargos', payload, {
        idempotencyKey,
      });
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return updated;
    } catch (error) {
      await handleStoreError(error, 'No se pudo asignar el cargo en la Junta de Condominio.');
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
      await handleStoreError(
        error,
        'No se pudo actualizar el embudo de incidencias. Mostrando caché local.',
        true,
        data.value.incidencias.length > 0,
      );
    } finally {
      isLoading.value = false;
    }
  }

  async function crearIncidencia(
    payload: IncidenciaCreateDTO,
    idempotencyKey: string = generateIdempotencyKey(),
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
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return created;
    } catch (error) {
      await handleStoreError(error, 'No se pudo crear el reporte de incidencia.');
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function adherirIncidencia(
    incidenciaId: number,
    idempotencyKey: string = generateIdempotencyKey(),
  ): Promise<IncidenciaDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const updated = await apiClient.post<IncidenciaDTO>(
        `/api/incidencias/${incidenciaId}/adherir`,
        {},
        { idempotencyKey },
      );
      data.value = {
        ...data.value,
        incidencias: data.value.incidencias
          .map((inc) => (inc.id === incidenciaId ? updated : inc))
          .sort((a, b) => b.adhesiones_count - a.adhesiones_count),
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return updated;
    } catch (error) {
      await handleStoreError(error, 'No fue posible sumarse a la incidencia.');
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
      await handleStoreError(
        error,
        'No se pudo actualizar el checklist del conserje. Mostrando lista en caché.',
        true,
        data.value.tareasDiarias.length > 0,
      );
    } finally {
      isLoading.value = false;
    }
  }

  async function crearPlantillaTarea(
    payload: PlantillaTareaCreateDTO,
    idempotencyKey: string = generateIdempotencyKey(),
  ): Promise<PlantillaTareaDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const created = await apiClient.post<PlantillaTareaDTO>('/api/tareas/plantillas', payload, {
        idempotencyKey,
      });
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return created;
    } catch (error) {
      await handleStoreError(error, 'No se pudo crear la plantilla recurrente de mantenimiento.');
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function crearTareaDiaria(
    payload: TareaDiariaCreateDTO,
    idempotencyKey: string = generateIdempotencyKey(),
  ): Promise<TareaDiariaDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const created = await apiClient.post<TareaDiariaDTO>('/api/tareas/diarias', payload, {
        idempotencyKey,
      });
      data.value = {
        ...data.value,
        tareasDiarias: [...data.value.tareasDiarias, created],
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return created;
    } catch (error) {
      await handleStoreError(error, 'No se pudo asignar la tarea puntual.');
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function generarTareasDiarias(
    fecha?: string,
    idempotencyKey: string = generateIdempotencyKey(),
  ): Promise<{ tareas_generadas: number }> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const generarSuffix = fecha ? `?fecha=${encodeURIComponent(fecha)}` : '';
      const result = await apiClient.post<{ tareas_generadas: number }>(
        `/api/tareas/generar-diarias${generarSuffix}`,
        {},
        { idempotencyKey },
      );
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return result;
    } catch (error) {
      await handleStoreError(error, 'No se pudieron generar las tareas diarias.');
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function completarTareaDiaria(
    tareaId: number,
    urlEvidencia: string | null = null,
    idempotencyKey: string = generateIdempotencyKey(),
  ): Promise<TareaDiariaDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const completed = await apiClient.put<TareaDiariaDTO>(
        `/api/tareas/${tareaId}/completar`,
        { url_evidencia: urlEvidencia },
        { idempotencyKey },
      );
      data.value = {
        ...data.value,
        tareasDiarias: data.value.tareasDiarias.map((t) => (t.id === tareaId ? completed : t)),
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return completed;
    } catch (error) {
      await handleStoreError(error, 'No se pudo marcar la tarea como completada.');
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchGaleriaVoceros(periodo?: string): Promise<void> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const galeriaSuffix = periodo ? `?periodo=${encodeURIComponent(periodo)}` : '';
      const galeria = await apiClient.get<GaleriaVoceroDTO>(`/api/voceros/galeria${galeriaSuffix}`);
      data.value = {
        ...data.value,
        galeriaVoceros: galeria,
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
    } catch (error) {
      await handleStoreError(
        error,
        'No se pudo sincronizar la galería de voceros. Mostrando fotos en caché.',
        true,
        data.value.galeriaVoceros.fotos.length > 0,
      );
    } finally {
      isLoading.value = false;
    }
  }

  async function subirFotoVocero(
    payload: FotoVoceroCreateDTO,
    idempotencyKey: string = generateIdempotencyKey(),
  ): Promise<FotoVoceroDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const created = await apiClient.post<FotoVoceroDTO>('/api/voceros/fotos', payload, {
        idempotencyKey,
      });
      data.value = {
        ...data.value,
        galeriaVoceros: {
          ...data.value.galeriaVoceros,
          fotos_usadas_mes: data.value.galeriaVoceros.fotos_usadas_mes + 1,
          fotos: [created, ...data.value.galeriaVoceros.fotos],
        },
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return created;
    } catch (error) {
      await handleStoreError(error, 'No se pudo subir la fotografía de inspección.');
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
      await handleStoreError(
        error,
        'No se pudo cargar el historial de la bitácora. Mostrando actas en caché.',
        true,
        data.value.bitacora.length > 0,
      );
    } finally {
      isLoading.value = false;
    }
  }

  async function crearActaBitacora(
    payload: BitacoraActaCreateDTO,
    idempotencyKey: string = generateIdempotencyKey(),
  ): Promise<BitacoraActaDTO> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const created = await apiClient.post<BitacoraActaDTO>('/api/bitacora/acta', payload, {
        idempotencyKey,
      });
      data.value = {
        ...data.value,
        bitacora: [created, ...data.value.bitacora],
      };
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return created;
    } catch (error) {
      await handleStoreError(error, 'No se pudo registrar el acta en la bitácora.');
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function actualizarAlicuotaUnidad(
    unidadId: number,
    payload: AlicuotaUpdateDTO,
    idempotencyKey: string = generateIdempotencyKey(),
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
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return updated;
    } catch (error) {
      await handleStoreError(error, 'No se pudo actualizar la alícuota o cuota fija de la unidad.');
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
    resetState,
    fetchUnidades,
    fetchAdminData,
    generarEstructura,
    asignarUsuarioFantasma,
    asignarCargoJunta,
    fetchIncidencias,
    crearIncidencia,
    adherirIncidencia,
    fetchTareasDiarias,
    crearPlantillaTarea,
    crearTareaDiaria,
    generarTareasDiarias,
    completarTareaDiaria,
    fetchGaleriaVoceros,
    subirFotoVocero,
    fetchBitacora,
    crearActaBitacora,
    actualizarAlicuotaUnidad,
  };
});
