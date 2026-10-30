import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient, ApiError } from '../services/apiClient';
import { useOperationsStore } from './operationsStore';

describe('operationsStore — Patrón No Destructivo, Incidencias, Conserjería, Voceros y Administración', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
  });

  it('sincroniza datos administrativos y preserva caché con isStale=true ante fallos de red o ApiError', async () => {
    const store = useOperationsStore();
    vi.spyOn(apiClient, 'get')
      .mockResolvedValueOnce([{ id: 10, identificador: 'Torre A-101', estructura_id: 2 }])
      .mockResolvedValueOnce([
        {
          id: 5,
          nombre: 'Pedro Fantasma',
          cedula: 'V-55',
          correo: 'pedro@test.com',
          telefono: '0414',
          es_activo: false,
          rol: 'FANTASMA',
        },
      ]);

    await store.fetchAdminData();
    expect(store.data.unidades).toHaveLength(1);
    expect(store.data.usuariosPendientes).toHaveLength(1);
    expect(store.isStale).toBe(false);

    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(new Error('Network down'));
    await store.fetchAdminData();
    expect(store.isStale).toBe(true);
    expect(store.data.unidades).toHaveLength(1);

    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(new ApiError(503, 'Servicio ocupado'));
    await store.fetchAdminData();
    expect(store.errorMessage).toBe('Servicio ocupado');
  });

  it('genera estructura, activa usuario fantasma y asigna cargo de Junta', async () => {
    const store = useOperationsStore();
    store.data.usuariosPendientes = [
      {
        id: 7,
        nombre: 'Luis',
        cedula: 'V-77',
        correo: 'luis@test.com',
        telefono: '0414',
        es_activo: false,
        rol: 'FANTASMA',
      },
    ];

    vi.spyOn(apiClient, 'post').mockResolvedValueOnce({
      estructura_id: 3,
      nombre: 'Torre Norte',
      tipo: 'TORRE',
      unidades_creadas: 2,
      unidades: [
        { id: 11, identificador: 'N-1', estructura_id: 3 },
        { id: 12, identificador: 'N-2', estructura_id: 3 },
      ],
    });

    const gen = await store.generarEstructura(
      { nombre: 'Torre Norte', tipo: 'TORRE', identificadores: ['N-1', 'N-2'] },
      'idemp-est-1',
    );
    expect(gen.unidades_creadas).toBe(2);

    vi.spyOn(apiClient, 'put')
      .mockResolvedValueOnce({
        id: 7,
        nombre: 'Luis',
        cedula: 'V-77',
        correo: 'luis@test.com',
        telefono: '0414',
        es_activo: true,
        rol: 'PROPIETARIO',
      })
      .mockResolvedValueOnce({
        id: 7,
        nombre: 'Luis',
        cedula: 'V-77',
        correo: 'luis@test.com',
        telefono: '0414',
        es_activo: true,
        rol: 'TESORERO',
      });

    await store.asignarUsuarioFantasma(7, {
      unidad_id: 11,
      tipo_ocupante: 'PROPIETARIO',
      rol: 'PROPIETARIO',
    });
    expect(store.data.usuariosPendientes).toHaveLength(0);

    const junta = await store.asignarCargoJunta({ usuario_id: 7, cargo: 'TESORERO' });
    expect(junta.rol).toBe('TESORERO');
  });

  it('gestiona embudo de incidencias (listar, crear, adherir y ordenar por prioridad)', async () => {
    const store = useOperationsStore();
    vi.spyOn(apiClient, 'get').mockResolvedValueOnce([
      {
        id: 1,
        usuario_creador_id: 2,
        area: 'Ascensor',
        descripcion: 'Ruido en polea',
        url_foto: null,
        estado: 'ABIERTO',
        adhesiones_count: 2,
      },
    ]);

    await store.fetchIncidencias();
    expect(store.data.incidencias).toHaveLength(1);

    vi.spyOn(apiClient, 'post')
      .mockResolvedValueOnce({
        id: 2,
        usuario_creador_id: 3,
        area: 'Portón',
        descripcion: 'Control remoto no responde',
        url_foto: null,
        estado: 'ABIERTO',
        adhesiones_count: 1,
      })
      .mockResolvedValueOnce({
        id: 2,
        usuario_creador_id: 3,
        area: 'Portón',
        descripcion: 'Control remoto no responde',
        url_foto: null,
        estado: 'ABIERTO',
        adhesiones_count: 5,
      });

    await store.crearIncidencia(
      { area: 'Portón', descripcion: 'Control remoto no responde' },
      'idemp-inc-1',
    );
    expect(store.data.incidencias).toHaveLength(2);

    await store.adherirIncidencia(2);
    expect(store.data.incidencias[0]?.id).toBe(2);
    expect(store.data.incidencias[0]?.adhesiones_count).toBe(5);
  });

  it('gestiona tareas del conserje, galería de voceros (cuota 30 fotos) y bitácora del secretario', async () => {
    const store = useOperationsStore();
    vi.spyOn(apiClient, 'get')
      .mockResolvedValueOnce([
        {
          id: 100,
          plantilla_id: 1,
          incidencia_id: 2,
          titulo: 'Purgar bomba hidroneumática',
          area: 'Cuarto de bombas',
          fecha: '2026-10-30',
          completada: false,
          url_evidencia: null,
        },
      ])
      .mockResolvedValueOnce({
        periodo: '2026-10',
        fotos_usadas_mes: 29,
        limite_mensual: 30,
        fotos: [],
      })
      .mockResolvedValueOnce([
        {
          id: 1,
          fecha: '2026-10-29',
          hora: '19:00',
          ubicacion: 'Salón de usos múltiples',
          contenido: 'Aprobado presupuesto de impermeabilización.',
          autor_id: 1,
        },
      ]);

    await store.fetchTareasDiarias();
    await store.fetchGaleriaVoceros('2026-10');
    await store.fetchBitacora();

    expect(store.remainingPhotosThisMonth).toBe(1);
    expect(store.isPhotoQuotaExhausted).toBe(false);

    vi.spyOn(apiClient, 'put').mockResolvedValueOnce({
      ...store.data.tareasDiarias[0]!,
      completada: true,
    });
    await store.completarTareaDiaria(100);
    expect(store.data.tareasDiarias[0]?.completada).toBe(true);

    vi.spyOn(apiClient, 'post')
      .mockResolvedValueOnce({
        id: 30,
        usuario_id: 4,
        periodo: '2026-10',
        area: 'Azotea',
        comentario: 'Manto asfáltico revisado',
        url_foto: 'https://cdn.condominio.test/voceros/30.avif',
      })
      .mockResolvedValueOnce({
        id: 2,
        fecha: '2026-10-30',
        hora: '20:00',
        ubicacion: 'Conserjería',
        contenido: 'Entrega de llaves de cuarto eléctrico.',
        autor_id: 1,
      });

    await store.subirFotoVocero({
      periodo: '2026-10',
      area: 'Azotea',
      comentario: 'Manto asfáltico revisado',
      url_foto: 'https://cdn.condominio.test/voceros/30.avif',
    });
    expect(store.isPhotoQuotaExhausted).toBe(true);

    await store.crearActaBitacora({
      fecha: '2026-10-30',
      hora: '20:00',
      ubicacion: 'Conserjería',
      contenido: 'Entrega de llaves de cuarto eléctrico.',
    });
    expect(store.data.bitacora).toHaveLength(2);
  });

  it('maneja errores en lecturas y mutaciones de operaciones preservando estado no destructivo', async () => {
    const store = useOperationsStore();

    vi.spyOn(apiClient, 'get')
      .mockRejectedValueOnce(new Error('Err inc'))
      .mockRejectedValueOnce(new ApiError(500, 'Err inc api'))
      .mockRejectedValueOnce(new Error('Err tareas'))
      .mockRejectedValueOnce(new ApiError(500, 'Err tareas api'))
      .mockRejectedValueOnce(new Error('Err galeria'))
      .mockRejectedValueOnce(new ApiError(500, 'Err galeria api'))
      .mockRejectedValueOnce(new Error('Err bitacora'))
      .mockRejectedValueOnce(new ApiError(500, 'Err bitacora api'));

    await store.fetchIncidencias();
    await store.fetchIncidencias();
    await store.fetchTareasDiarias();
    await store.fetchTareasDiarias();
    await store.fetchGaleriaVoceros();
    await store.fetchGaleriaVoceros();
    await store.fetchBitacora();
    await store.fetchBitacora();
    expect(store.isStale).toBe(true);

    vi.spyOn(apiClient, 'post')
      .mockRejectedValueOnce(new ApiError(409, 'Estructura duplicada'))
      .mockRejectedValueOnce(new Error('Red estructura'))
      .mockRejectedValueOnce(new ApiError(409, 'Incidencia duplicada'))
      .mockRejectedValueOnce(new Error('Red incidencia'))
      .mockRejectedValueOnce(new ApiError(409, 'Ya te sumaste'))
      .mockRejectedValueOnce(new Error('Red adherir'))
      .mockRejectedValueOnce(new ApiError(429, 'Límite mensual de 30 fotografías alcanzado.'))
      .mockRejectedValueOnce(new Error('Red foto'))
      .mockRejectedValueOnce(new ApiError(400, 'Acta inválida'))
      .mockRejectedValueOnce(new Error('Red acta'));

    await expect(
      store.generarEstructura({ nombre: 'T', tipo: 'TORRE', identificadores: ['1'] }, 'k1'),
    ).rejects.toThrow();
    await expect(
      store.generarEstructura({ nombre: 'T', tipo: 'TORRE', identificadores: ['1'] }, 'k2'),
    ).rejects.toThrow();
    await expect(store.crearIncidencia({ area: 'A', descripcion: 'D' }, 'k3')).rejects.toThrow();
    await expect(store.crearIncidencia({ area: 'A', descripcion: 'D' }, 'k4')).rejects.toThrow();
    await expect(store.adherirIncidencia(1)).rejects.toThrow();
    await expect(store.adherirIncidencia(1)).rejects.toThrow();
    await expect(
      store.subirFotoVocero({
        periodo: '2026-10',
        area: 'A',
        comentario: 'C',
        url_foto: 'https://x.test/1.avif',
      }),
    ).rejects.toThrow();
    await expect(
      store.subirFotoVocero({
        periodo: '2026-10',
        area: 'A',
        comentario: 'C',
        url_foto: 'https://x.test/1.avif',
      }),
    ).rejects.toThrow();
    await expect(
      store.crearActaBitacora({
        fecha: '2026-10-30',
        hora: '10:00',
        ubicacion: 'U',
        contenido: 'C',
      }),
    ).rejects.toThrow();
    await expect(
      store.crearActaBitacora({
        fecha: '2026-10-30',
        hora: '10:00',
        ubicacion: 'U',
        contenido: 'C',
      }),
    ).rejects.toThrow();

    vi.spyOn(apiClient, 'put')
      .mockRejectedValueOnce(new ApiError(404, 'Usuario no existe'))
      .mockRejectedValueOnce(new Error('Red usuario'))
      .mockRejectedValueOnce(new ApiError(400, 'No es propietario'))
      .mockRejectedValueOnce(new Error('Red junta'))
      .mockRejectedValueOnce(new ApiError(404, 'Tarea no existe'))
      .mockRejectedValueOnce(new Error('Red tarea'));

    await expect(
      store.asignarUsuarioFantasma(99, {
        unidad_id: 1,
        tipo_ocupante: 'PROPIETARIO',
        rol: 'PROPIETARIO',
      }),
    ).rejects.toThrow();
    await expect(
      store.asignarUsuarioFantasma(99, {
        unidad_id: 1,
        tipo_ocupante: 'PROPIETARIO',
        rol: 'PROPIETARIO',
      }),
    ).rejects.toThrow();
    await expect(store.asignarCargoJunta({ usuario_id: 99, cargo: 'TESORERO' })).rejects.toThrow();
    await expect(store.asignarCargoJunta({ usuario_id: 99, cargo: 'TESORERO' })).rejects.toThrow();
    await expect(store.completarTareaDiaria(99)).rejects.toThrow();
    await expect(store.completarTareaDiaria(99)).rejects.toThrow();
  });
});
