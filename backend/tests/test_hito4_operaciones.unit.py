"""Pruebas unitarias Nivel 11X para el Hito 4 (Administración, Incidencias, Operaciones y Worker)."""

from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from src.database import get_db
from src.dependencies import get_current_user
from src.main import app
from src.models import (
    BitacoraActa,
    Comunicado,
    ContratoOcupacion,
    FotoVocero,
    Incidencia,
    IncidenciaAdhesion,
    PlantillaTarea,
    TareaDiaria,
    Unidad,
    Usuario,
)
from src.redis_client import get_redis_client
from src.worker import (
    convertir_y_subir_avif,
    encolar_notificacion_correo,
    generar_tareas_diarias_desde_plantillas,
)


class FakeUser:
    def __init__(self, user_id: int = 1, rol: str = "PRESIDENTE", es_activo: bool = True) -> None:
        self.id = user_id
        self.correo = f"{rol.lower()}@condominio.test"
        self.rol = rol
        self.es_activo = es_activo


def _result(value: Any) -> MagicMock:
    res = MagicMock()
    res.scalars().first.return_value = value
    return res


def _result_list(values: list[Any]) -> MagicMock:
    res = MagicMock()
    res.scalars().all.return_value = values
    return res


def _mock_session(*results: Any) -> AsyncMock:
    session = AsyncMock()
    session.execute.side_effect = list(results)
    session.add = MagicMock()

    async def _refresh(instance: Any, *args: object, **kwargs: object) -> None:
        if getattr(instance, "id", None) is None:
            instance.id = 10

    session.refresh = _refresh
    return session


def _setup(session: AsyncMock, user: FakeUser | None = None, redis_new: bool = True) -> AsyncMock:
    mock_redis = AsyncMock()
    mock_redis.set.return_value = redis_new
    mock_redis.rpush = AsyncMock(return_value=1)
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_redis_client] = lambda: mock_redis
    app.dependency_overrides[get_current_user] = lambda: user or FakeUser()
    return mock_redis


# ==============================================================================
# 1. WORKER ASÍNCRONO (AVIF, NOTIFICACIONES Y CRONJOB DE TAREAS)
# ==============================================================================


def test_convertir_y_subir_avif_exitoso_y_vacio() -> None:
    uri = convertir_y_subir_avif(b"\x89PNG\r\n\x1a\ncontenido", "/voceros/2026-10/")
    assert uri.startswith("s3://condominio-media/voceros/2026-10/")
    assert uri.endswith(".avif")

    with pytest.raises(ValueError, match="vacío"):
        convertir_y_subir_avif(b"", "voceros")


async def test_encolar_notificacion_correo_con_y_sin_redis() -> None:
    mock_redis = AsyncMock()
    evento = await encolar_notificacion_correo(
        destinatarios=["presidente@test.com"],
        asunto="Nuevo vecino",
        cuerpo="Solicitud pendiente",
        redis_client=mock_redis,
    )
    assert evento["tipo"] == "EMAIL_NOTIFICATION"
    mock_redis.rpush.assert_awaited_once()

    evento_sin_redis = await encolar_notificacion_correo(
        destinatarios=["vp@test.com"],
        asunto="Aviso",
        cuerpo="Detalle",
        redis_client=None,
    )
    assert evento_sin_redis["destinatarios"] == ["vp@test.com"]

    with pytest.raises(ValueError, match="destinatario"):
        await encolar_notificacion_correo([], "Asunto", "Cuerpo")


async def test_generar_tareas_diarias_desde_plantillas_idempotente() -> None:
    # Caso 1: Sin plantillas activas
    session_vacia = _mock_session(_result_list([]))
    assert await generar_tareas_diarias_desde_plantillas(session_vacia) == 0

    # Caso 2: 2 plantillas activas, 1 ya generada hoy -> solo crea 1
    p1 = PlantillaTarea(id=1, titulo="Limpiar lobby", area="Torre A", frecuencia="DIARIA", activa=True)
    p2 = PlantillaTarea(id=2, titulo="Revisar bombas", area="Sótano", frecuencia="DIARIA", activa=True)
    t_existente = TareaDiaria(
        id=50,
        plantilla_id=1,
        incidencia_id=None,
        titulo="Limpiar lobby",
        area="Torre A",
        fecha=date(2026, 10, 29),
        completada=False,
    )
    session = _mock_session(_result_list([p1, p2]), _result_list([t_existente]))
    creadas = await generar_tareas_diarias_desde_plantillas(session, fecha_objetivo=date(2026, 10, 29))
    assert creadas == 1
    session.commit.assert_awaited_once()

    # Caso 3: Todas las plantillas ya fueron generadas hoy -> 0 creadas
    session_completa = _mock_session(_result_list([p1]), _result_list([t_existente]))
    assert await generar_tareas_diarias_desde_plantillas(session_completa, fecha_objetivo=date(2026, 10, 29)) == 0


# ==============================================================================
# 2. ADMINISTRACIÓN: ESTRUCTURA, USUARIOS FANTASMA Y JUNTA DE CONDOMINIO
# ==============================================================================


def test_estructura_listar_y_generar_exitoso_y_errores() -> None:
    u1 = Unidad(id=1, identificador="A-101", estructura_id=1)
    session_list = _mock_session(_result_list([u1]))
    _setup(session_list)
    client = TestClient(app)

    r_list = client.get("/api/estructura/unidades")
    assert r_list.status_code == 200
    assert r_list.json()[0]["identificador"] == "A-101"

    # Generación exitosa por Presidente
    session_gen = _mock_session()
    _setup(session_gen, user=FakeUser(rol="PRESIDENTE"))
    r_gen = client.post(
        "/api/estructura/generar",
        headers={"Idempotency-Key": "idem-est-001"},
        json={"nombre": "Torre A", "tipo": "EDIFICIO", "identificadores": ["A-101", "A-102", "A-101"]},
    )
    assert r_gen.status_code == 201
    assert r_gen.json()["unidades_creadas"] == 2

    # Idempotencia repetida -> 409
    _setup(_mock_session(), user=FakeUser(rol="PRESIDENTE"), redis_new=False)
    r_dup = client.post(
        "/api/estructura/generar",
        headers={"Idempotency-Key": "idem-est-001"},
        json={"nombre": "Torre A", "tipo": "EDIFICIO", "identificadores": ["A-101"]},
    )
    assert r_dup.status_code == 409

    # IntegrityError -> 409
    session_int = _mock_session()
    session_int.commit.side_effect = IntegrityError("dup", {}, Exception("dup"))
    _setup(session_int, user=FakeUser(rol="PRESIDENTE"))
    r_int = client.post(
        "/api/estructura/generar",
        headers={"Idempotency-Key": "idem-est-002"},
        json={"nombre": "Torre A", "tipo": "EDIFICIO", "identificadores": ["A-101"]},
    )
    assert r_int.status_code == 409

    # Error inesperado de BD -> 500
    session_err = _mock_session()
    session_err.commit.side_effect = RuntimeError("db down")
    _setup(session_err, user=FakeUser(rol="PRESIDENTE"))
    r_err = client.post(
        "/api/estructura/generar",
        headers={"Idempotency-Key": "idem-est-003"},
        json={"nombre": "Torre A", "tipo": "EDIFICIO", "identificadores": ["A-101"]},
    )
    assert r_err.status_code == 500
    app.dependency_overrides.clear()


def test_rbac_bloquea_usuario_fantasma_y_rol_no_autorizado() -> None:
    client = TestClient(app)

    # Estado A (Usuario Fantasma inactivo) -> 403
    _setup(_mock_session(), user=FakeUser(rol="FANTASMA", es_activo=False))
    r_ghost = client.get("/api/incidencias/abiertas")
    assert r_ghost.status_code == 403

    # Rol PROPIETARIO intentando aprobar usuarios -> 403
    _setup(_mock_session(), user=FakeUser(rol="PROPIETARIO", es_activo=True))
    r_forbidden = client.get("/api/usuarios/pendientes")
    assert r_forbidden.status_code == 403
    app.dependency_overrides.clear()


def test_usuarios_pendientes_asignar_y_junta_cargos() -> None:
    fantasma = Usuario(
        id=9,
        nombre="Vecino Nuevo",
        cedula="V-99999999",
        correo="nuevo@condominio.test",
        telefono="04140000000",
        password_hash="hash",
        es_activo=False,
        rol="FANTASMA",
    )
    unidad = Unidad(id=3, identificador="A-301", estructura_id=1)
    contrato = ContratoOcupacion(id=4, usuario_id=9, unidad_id=3, tipo_ocupante="PROPIETARIO", es_activo=False)

    client = TestClient(app)

    # 1. Listar pendientes
    _setup(_mock_session(_result_list([fantasma])), user=FakeUser(rol="PRESIDENTE"))
    r_pend = client.get("/api/usuarios/pendientes")
    assert r_pend.status_code == 200
    assert len(r_pend.json()) == 1

    # 2. Asignar con contrato previo existente
    _setup(
        _mock_session(_result(fantasma), _result(unidad), _result_list([contrato])),
        user=FakeUser(rol="PRESIDENTE"),
    )
    r_asig = client.put(
        "/api/usuarios/9/asignar",
        json={"unidad_id": 3, "tipo_ocupante": "PROPIETARIO", "rol": "PROPIETARIO"},
    )
    assert r_asig.status_code == 200
    assert r_asig.json()["es_activo"] is True
    assert r_asig.json()["rol"] == "PROPIETARIO"

    # 3. Asignar creando contrato nuevo (sin contrato previo)
    _setup(
        _mock_session(_result(fantasma), _result(unidad), _result_list([])),
        user=FakeUser(rol="VICEPRESIDENTE"),
    )
    r_asig_nuevo = client.put(
        "/api/usuarios/9/asignar",
        json={"unidad_id": 3, "tipo_ocupante": "INQUILINO", "rol": "INQUILINO"},
    )
    assert r_asig_nuevo.status_code == 200
    assert r_asig_nuevo.json()["rol"] == "INQUILINO"

    # 4. Asignar usuario o unidad inexistente -> 404
    _setup(_mock_session(_result(None)), user=FakeUser(rol="PRESIDENTE"))
    assert (
        client.put(
            "/api/usuarios/999/asignar",
            json={"unidad_id": 3, "tipo_ocupante": "PROPIETARIO", "rol": "PROPIETARIO"},
        ).status_code
        == 404
    )
    _setup(_mock_session(_result(fantasma), _result(None)), user=FakeUser(rol="PRESIDENTE"))
    assert (
        client.put(
            "/api/usuarios/9/asignar",
            json={"unidad_id": 999, "tipo_ocupante": "PROPIETARIO", "rol": "PROPIETARIO"},
        ).status_code
        == 404
    )

    # 5. Asignar cargo de Junta: usuario inexistente -> 404
    _setup(_mock_session(_result(None)), user=FakeUser(rol="PRESIDENTE"))
    assert client.put("/api/junta/cargos", json={"usuario_id": 999, "cargo": "TESORERO"}).status_code == 404

    # 6. Asignar cargo de Junta: inquilino sin contrato de propietario -> 400
    fantasma.es_activo = True
    _setup(_mock_session(_result(fantasma), _result(None)), user=FakeUser(rol="PRESIDENTE"))
    r_junta_fail = client.put("/api/junta/cargos", json={"usuario_id": 9, "cargo": "TESORERO"})
    assert r_junta_fail.status_code == 400

    # 7. Asignar cargo de Junta: propietario activo con contrato -> 200
    contrato.es_activo = True
    contrato.tipo_ocupante = "PROPIETARIO"
    _setup(_mock_session(_result(fantasma), _result(contrato)), user=FakeUser(rol="PRESIDENTE"))
    r_junta_ok = client.put("/api/junta/cargos", json={"usuario_id": 9, "cargo": "TESORERO"})
    assert r_junta_ok.status_code == 200
    assert r_junta_ok.json()["rol"] == "TESORERO"
    app.dependency_overrides.clear()


# ==============================================================================
# 3. EMBUDO DE INCIDENCIAS Y ADHESIÓN ('ME SUMO')
# ==============================================================================


def test_flujo_completo_incidencias_y_me_sumo() -> None:
    inc = Incidencia(
        id=5,
        usuario_creador_id=2,
        area="Ascensor Torre A",
        descripcion="Puerta del piso 3 trabada",
        url_foto=None,
        estado="ABIERTO",
        adhesiones_count=3,
    )
    client = TestClient(app)

    # 1. Listar abiertas
    _setup(_mock_session(_result_list([inc])), user=FakeUser(user_id=2, rol="PROPIETARIO"))
    r_list = client.get("/api/incidencias/abiertas")
    assert r_list.status_code == 200
    assert r_list.json()[0]["adhesiones_count"] == 3

    # 2. Crear incidencia exitosa
    _setup(_mock_session(), user=FakeUser(user_id=2, rol="PROPIETARIO"))
    r_crear = client.post(
        "/api/incidencias/crear",
        headers={"Idempotency-Key": "inc-key-001"},
        json={"area": "Piscina", "descripcion": "Bomba con ruido", "url_foto": "s3://condominio-media/f.avif"},
    )
    assert r_crear.status_code == 201
    assert r_crear.json()["adhesiones_count"] == 1

    # 3. Crear incidencia con Idempotency-Key repetida -> 409
    _setup(_mock_session(), user=FakeUser(user_id=2, rol="PROPIETARIO"), redis_new=False)
    r_dup_key = client.post(
        "/api/incidencias/crear",
        headers={"Idempotency-Key": "inc-key-001"},
        json={"area": "Piscina", "descripcion": "Bomba con ruido"},
    )
    assert r_dup_key.status_code == 409

    # 4. Crear incidencia con fallo de BD -> 500
    session_err = _mock_session()
    session_err.commit.side_effect = RuntimeError("fallo bd")
    _setup(session_err, user=FakeUser(user_id=2, rol="PROPIETARIO"))
    r_err = client.post(
        "/api/incidencias/crear",
        headers={"Idempotency-Key": "inc-key-002"},
        json={"area": "Piscina", "descripcion": "Bomba con ruido"},
    )
    assert r_err.status_code == 500

    # 5. Adherir ('Me sumo') exitoso -> incrementa adhesiones_count a 4
    _setup(_mock_session(_result(inc), _result(None)), user=FakeUser(user_id=8, rol="INQUILINO"))
    r_adh = client.post("/api/incidencias/5/adherir")
    assert r_adh.status_code == 200
    assert r_adh.json()["adhesiones_count"] == 4

    # 6. Adherir a incidencia inexistente -> 404
    _setup(_mock_session(_result(None)), user=FakeUser(user_id=8, rol="INQUILINO"))
    assert client.post("/api/incidencias/999/adherir").status_code == 404

    # 7. Adherir cuando el vecino ya se sumó -> 409
    adh_existente = IncidenciaAdhesion(id=1, incidencia_id=5, usuario_id=8)
    _setup(_mock_session(_result(inc), _result(adh_existente)), user=FakeUser(user_id=8, rol="INQUILINO"))
    assert client.post("/api/incidencias/5/adherir").status_code == 409

    # 8. Adherir con colisión concurrente IntegrityError -> 409
    session_race = _mock_session(_result(inc), _result(None))
    session_race.commit.side_effect = IntegrityError("dup", {}, Exception("dup"))
    _setup(session_race, user=FakeUser(user_id=8, rol="INQUILINO"))
    assert client.post("/api/incidencias/5/adherir").status_code == 409

    # 9. Adherir a incidencia CERRADA -> 409
    inc.estado = "CERRADO"
    _setup(_mock_session(_result(inc)), user=FakeUser(user_id=8, rol="INQUILINO"))
    assert client.post("/api/incidencias/5/adherir").status_code == 409
    app.dependency_overrides.clear()


# ==============================================================================
# 4. OPERACIONES: CONSERJERÍA, GALERÍA DE VOCEROS (30 FOTOS), BITÁCORA Y COMUNICADOS
# ==============================================================================


def test_conserjeria_plantillas_tareas_y_cierre_automatico_incidencia() -> None:
    client = TestClient(app)

    # 1. Crear plantilla
    _setup(_mock_session(), user=FakeUser(rol="PRESIDENTE"))
    r_plant = client.post(
        "/api/tareas/plantillas",
        json={"titulo": "Baldeo de entrada", "area": "Planta Baja", "frecuencia": "DIARIA"},
    )
    assert r_plant.status_code == 201
    assert r_plant.json()["activa"] is True

    # 2. Asignar tarea directa vinculada a incidencia -> pasa incidencia a EN_PROCESO
    inc = Incidencia(
        id=12,
        usuario_creador_id=3,
        area="Portón",
        descripcion="Falta lubricación",
        url_foto=None,
        estado="ABIERTO",
        adhesiones_count=2,
    )
    _setup(_mock_session(_result(inc)), user=FakeUser(rol="PRESIDENTE"))
    r_td = client.post(
        "/api/tareas/diarias",
        json={"titulo": "Lubricar riel de portón", "area": "Portón", "incidencia_id": 12},
    )
    assert r_td.status_code == 201
    assert inc.estado == "EN_PROCESO"

    # 3. Asignar tarea directa con incidencia inexistente -> 404
    _setup(_mock_session(_result(None)), user=FakeUser(rol="PRESIDENTE"))
    r_td_404 = client.post(
        "/api/tareas/diarias",
        json={"titulo": "Revisar foco", "area": "Pasillo", "incidencia_id": 999},
    )
    assert r_td_404.status_code == 404

    # 4. Asignar tarea directa sin incidencia
    _setup(_mock_session(), user=FakeUser(rol="VICEPRESIDENTE"))
    r_td_simple = client.post(
        "/api/tareas/diarias",
        json={"titulo": "Limpiar vidrios", "area": "Lobby"},
    )
    assert r_td_simple.status_code == 201

    # 5. Ejecutar cronjob desde endpoint
    p_activa = PlantillaTarea(id=1, titulo="Barrer", area="Patio", frecuencia="DIARIA", activa=True)
    _setup(_mock_session(_result_list([p_activa]), _result_list([])), user=FakeUser(rol="PRESIDENTE"))
    r_cron = client.post("/api/tareas/generar-diarias")
    assert r_cron.status_code == 200
    assert r_cron.json()["tareas_generadas"] == 1

    # 6. Listar tareas del día
    tarea_obj = TareaDiaria(
        id=20,
        plantilla_id=1,
        incidencia_id=12,
        titulo="Lubricar riel",
        area="Portón",
        fecha=date.today(),
        completada=False,
        url_evidencia=None,
    )
    _setup(_mock_session(_result_list([tarea_obj])), user=FakeUser(rol="CONSERJE"))
    r_list = client.get("/api/tareas/diarias")
    assert r_list.status_code == 200
    assert len(r_list.json()) == 1

    # 7. Completar tarea vinculada a incidencia -> cierra incidencia automáticamente
    _setup(_mock_session(_result(tarea_obj), _result(inc)), user=FakeUser(rol="CONSERJE"))
    r_comp = client.put(
        "/api/tareas/20/completar",
        json={"url_evidencia": "s3://condominio-media/evidencias/porton.avif"},
    )
    assert r_comp.status_code == 200
    assert r_comp.json()["completada"] is True
    assert inc.estado == "CERRADO"

    # 8. Completar tarea sin incidencia vinculada
    tarea_simple = TareaDiaria(
        id=21,
        plantilla_id=1,
        incidencia_id=None,
        titulo="Barrer",
        area="Patio",
        fecha=date.today(),
        completada=False,
        url_evidencia=None,
    )
    _setup(_mock_session(_result(tarea_simple)), user=FakeUser(rol="CONSERJE"))
    assert client.put("/api/tareas/21/completar", json={}).status_code == 200

    # 9. Completar tarea inexistente -> 404
    _setup(_mock_session(_result(None)), user=FakeUser(rol="CONSERJE"))
    assert client.put("/api/tareas/999/completar", json={}).status_code == 404
    app.dependency_overrides.clear()


def test_galeria_voceros_limite_estricto_30_fotos_por_mes() -> None:
    client = TestClient(app)

    # 1. Subida exitosa cuando hay < 30 fotos en el mes
    fotos_previas = [
        FotoVocero(
            id=i,
            usuario_id=4,
            periodo="2026-10",
            area="Jardines",
            comentario=f"Foto {i}",
            url_foto=f"s3://condominio-media/voceros/{i}.avif",
        )
        for i in range(1, 30)
    ]
    _setup(_mock_session(_result_list(fotos_previas)), user=FakeUser(user_id=4, rol="VOCERO"))
    r_ok = client.post(
        "/api/voceros/fotos",
        json={
            "periodo": "2026-10",
            "area": "Jardines",
            "comentario": "Foto número 30 permitida",
            "url_foto": "s3://condominio-media/voceros/30.avif",
        },
    )
    assert r_ok.status_code == 201

    # 2. Subida número 31 en el mismo mes -> Rechazada con 429 Too Many Requests
    fotos_llenas = [
        *fotos_previas,
        FotoVocero(
            id=30,
            usuario_id=4,
            periodo="2026-10",
            area="Jardines",
            comentario="Foto 30",
            url_foto="s3://condominio-media/voceros/30.avif",
        ),
    ]
    _setup(_mock_session(_result_list(fotos_llenas)), user=FakeUser(user_id=4, rol="VOCERO"))
    r_limite = client.post(
        "/api/voceros/fotos",
        json={
            "periodo": "2026-10",
            "area": "Jardines",
            "comentario": "Intento 31 sobre el límite",
            "url_foto": "s3://condominio-media/voceros/31.avif",
        },
    )
    assert r_limite.status_code == 429
    assert "30 fotografías" in r_limite.json()["detail"]

    # 3. Consultar galería del mes
    _setup(_mock_session(_result_list(fotos_llenas)), user=FakeUser(user_id=2, rol="PROPIETARIO"))
    r_gal = client.get("/api/voceros/galeria?periodo=2026-10")
    assert r_gal.status_code == 200
    assert r_gal.json()["fotos_usadas_mes"] == 30
    assert r_gal.json()["limite_mensual"] == 30
    app.dependency_overrides.clear()


def test_bitacora_secretario_y_comunicados_con_anti_ssrf() -> None:
    client = TestClient(app)

    # 1. Crear y listar acta de bitácora
    _setup(_mock_session(), user=FakeUser(user_id=6, rol="SECRETARIO"))
    r_acta = client.post(
        "/api/bitacora/acta",
        json={
            "fecha": "2026-10-29",
            "hora": "19:30",
            "ubicacion": "Salón de Fiestas",
            "contenido": "Se aprobó el presupuesto de pintura.",
        },
    )
    assert r_acta.status_code == 201

    acta_obj = BitacoraActa(
        id=1,
        fecha=date(2026, 10, 29),
        hora="19:30",
        ubicacion="Salón de Fiestas",
        contenido="Se aprobó el presupuesto de pintura.",
        autor_id=6,
    )
    _setup(_mock_session(_result_list([acta_obj])), user=FakeUser(user_id=2, rol="PROPIETARIO"))
    r_hist = client.get("/api/bitacora/historial")
    assert r_hist.status_code == 200
    assert len(r_hist.json()) == 1

    # 2. Publicar comunicado sin enlace externo -> 201
    _setup(_mock_session(), user=FakeUser(user_id=6, rol="SECRETARIO"))
    r_com = client.post(
        "/api/comunicados",
        json={"titulo": "Corte programado de agua", "contenido": "Mantenimiento de tanque el sábado."},
    )
    assert r_com.status_code == 201

    # 3. Publicar comunicado con URL interna SSRF -> Bloqueado con 400
    _setup(_mock_session(), user=FakeUser(user_id=6, rol="SECRETARIO"))
    r_ssrf = client.post(
        "/api/comunicados",
        json={
            "titulo": "Enlace malicioso",
            "contenido": "Prueba SSRF",
            "enlace_externo": "http://127.0.0.1:8000/internal",
        },
    )
    assert r_ssrf.status_code == 400

    # 4. Listar comunicados recientes
    com_obj = Comunicado(
        id=1,
        titulo="Corte programado de agua",
        contenido="Mantenimiento de tanque el sábado.",
        enlace_externo=None,
        activo=True,
    )
    _setup(_mock_session(_result_list([com_obj])), user=FakeUser(user_id=2, rol="PROPIETARIO"))
    r_rec = client.get("/api/comunicados/recientes")
    assert r_rec.status_code == 200
    assert r_rec.json()[0]["titulo"] == "Corte programado de agua"
    app.dependency_overrides.clear()
