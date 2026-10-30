"""Pruebas unitarias Nivel 11X para el Hito 13: Reserva de Áreas Sociales e Inspección Post-Evento."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from src.database import get_db
from src.dependencies import get_current_user
from src.main import app
from src.models import AreaSocial, Recibo, ReservaAreaSocial, TareaDiaria, Unidad
from src.redis_client import get_redis_client

HEADERS = {"Idempotency-Key": "018f4a13-1313-7000-8000-000000001313"}


class FakeUser:
    def __init__(self, user_id: int = 1, rol: str = "RESIDENTE", es_activo: bool = True) -> None:
        self.id = user_id
        self.correo = f"{rol.lower()}_{user_id}@condominio.test"
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
    added: list[Any] = []

    def _add(obj: Any) -> None:
        if getattr(obj, "id", None) is None:
            obj.id = 100 + len(added)
        added.append(obj)

    session.add = MagicMock(side_effect=_add)

    async def _refresh(instance: Any, *args: object, **kwargs: object) -> None:
        if getattr(instance, "id", None) is None:
            instance.id = 200

    session.refresh = _refresh
    return session


def _setup(session: AsyncMock, user: FakeUser | None = None, redis_new: bool = True) -> AsyncMock:
    mock_redis = AsyncMock()
    mock_redis.set.return_value = redis_new
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_redis_client] = lambda: mock_redis
    app.dependency_overrides[get_current_user] = lambda: user or FakeUser()
    return mock_redis


# ==============================================================================
# 1. CONFIGURACIÓN Y LISTADO DE ÁREAS SOCIALES (/api/reservas/areas)
# ==============================================================================


def test_crear_area_social_exitosa_y_duplicada() -> None:
    session = _mock_session(_result(None))
    _setup(session, FakeUser(1, "PRESIDENTE"))
    client = TestClient(app)

    resp = client.post(
        "/api/reservas/areas",
        headers=HEADERS,
        json={
            "nombre": "Salón de Fiestas Principal",
            "aforo_maximo": 80,
            "costo_uso_usd": "35.00",
            "deposito_garantia_usd": "100.00",
            "requiere_solvencia_estricta": True,
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["nombre"] == "Salón de Fiestas Principal"
    assert body["aforo_maximo"] == 80
    assert Decimal(body["deposito_garantia_usd"]) == Decimal("100.00")

    # Nombre duplicado -> 409
    existente = AreaSocial(
        id=1,
        nombre="Salón de Fiestas Principal",
        aforo_maximo=80,
        costo_uso_usd=Decimal("35.00"),
        deposito_garantia_usd=Decimal("100.00"),
        requiere_solvencia_estricta=True,
        es_activa=True,
    )
    session_dup = _mock_session(_result(existente))
    _setup(session_dup, FakeUser(2, "TESORERO"))
    resp_dup = client.post(
        "/api/reservas/areas",
        headers=HEADERS,
        json={
            "nombre": "Salón de Fiestas Principal",
            "aforo_maximo": 50,
        },
    )
    assert resp_dup.status_code == 409

    # Idempotency-Key repetida -> 409
    _setup(_mock_session(), FakeUser(1, "PRESIDENTE"), redis_new=False)
    resp_idem = client.post(
        "/api/reservas/areas",
        headers=HEADERS,
        json={"nombre": "Caney Parrillero", "aforo_maximo": 25},
    )
    assert resp_idem.status_code == 409

    # Rol no autorizado (RESIDENTE) -> 403
    _setup(_mock_session(), FakeUser(3, "RESIDENTE"))
    resp_rol = client.post(
        "/api/reservas/areas",
        headers=HEADERS,
        json={"nombre": "Caney Parrillero", "aforo_maximo": 25},
    )
    assert resp_rol.status_code == 403
    app.dependency_overrides.clear()


def test_listar_areas_sociales_y_bloqueo_fantasma() -> None:
    area = AreaSocial(
        id=5,
        nombre="Parrillera Norte",
        aforo_maximo=20,
        costo_uso_usd=Decimal("15.00"),
        deposito_garantia_usd=Decimal("50.00"),
        requiere_solvencia_estricta=True,
        es_activa=True,
    )
    session = _mock_session(_result_list([area]))
    _setup(session, FakeUser(10, "RESIDENTE"))
    client = TestClient(app)

    resp = client.get("/api/reservas/areas")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["nombre"] == "Parrillera Norte"

    # Usuario Fantasma -> 403
    _setup(_mock_session(), FakeUser(99, "FANTASMA", es_activo=False))
    resp_ghost = client.get("/api/reservas/areas")
    assert resp_ghost.status_code == 403
    app.dependency_overrides.clear()


# ==============================================================================
# 2. SOLICITUD DE RESERVA CON CANDADO DE SOLVENCIA ESTRICTA Y TAREA DIARIA
# ==============================================================================


def test_solicitar_reserva_unidad_solvente_crea_tarea_inspeccion() -> None:
    unidad = Unidad(id=12, estructura_id=1, identificador="PB-02", alicuota=Decimal("2.5000"))
    area = AreaSocial(
        id=3,
        nombre="Salón de Usos Múltiples",
        aforo_maximo=60,
        costo_uso_usd=Decimal("25.00"),
        deposito_garantia_usd=Decimal("80.00"),
        requiere_solvencia_estricta=True,
        es_activa=True,
    )
    recibo_pagado = Recibo(
        id=1,
        periodo="2026-10",
        unidad_id=12,
        monto_usd=Decimal("45.00"),
        monto_pagado_usd=Decimal("45.00"),
        estado="PAGADO",
    )
    session = _mock_session(
        _result(unidad),
        _result_list([12]),
        _result(area),
        _result_list([recibo_pagado]),
        _result(None),
    )
    _setup(session, FakeUser(7, "RESIDENTE"))
    client = TestClient(app)

    resp = client.post(
        "/api/reservas/solicitar",
        headers=HEADERS,
        json={
            "area_id": 3,
            "unidad_id": 12,
            "fecha_evento": "2026-12-15",
            "motivo_evento": "Cumpleaños familiar infantil",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["estado"] == "CONFIRMADA"
    assert body["nombre_area"] == "Salón de Usos Múltiples"
    assert body["identificador_unidad"] == "PB-02"
    assert body["tarea_inspeccion_id"] == 100
    app.dependency_overrides.clear()


def test_solicitar_reserva_rechazada_por_morosidad_403() -> None:
    unidad = Unidad(id=14, estructura_id=1, identificador="A-04", alicuota=Decimal("2.5000"))
    area = AreaSocial(
        id=3,
        nombre="Salón de Fiestas",
        aforo_maximo=60,
        costo_uso_usd=Decimal("25.00"),
        deposito_garantia_usd=Decimal("80.00"),
        requiere_solvencia_estricta=True,
        es_activa=True,
    )
    recibo_moroso = Recibo(
        id=9,
        periodo="2026-10",
        unidad_id=14,
        monto_usd=Decimal("50.00"),
        monto_pagado_usd=Decimal("10.00"),
        estado="PARCIAL",
    )
    session = _mock_session(
        _result(unidad),
        _result_list([14]),
        _result(area),
        _result_list([recibo_moroso]),
    )
    _setup(session, FakeUser(8, "RESIDENTE"))
    client = TestClient(app)

    resp = client.post(
        "/api/reservas/solicitar",
        headers=HEADERS,
        json={
            "area_id": 3,
            "unidad_id": 14,
            "fecha_evento": "2026-12-20",
            "motivo_evento": "Reunión de fin de año",
        },
    )
    assert resp.status_code == 403
    assert "Reserva bloqueada por morosidad" in resp.json()["detail"]
    app.dependency_overrides.clear()


def test_solicitar_reserva_conflictos_fecha_unidad_area_e_idempotencia() -> None:
    unidad = Unidad(id=12, estructura_id=1, identificador="PB-02", alicuota=Decimal("2.5000"))
    area_sin_candado = AreaSocial(
        id=4,
        nombre="Cancha Múltiple",
        aforo_maximo=30,
        costo_uso_usd=Decimal("0.00"),
        deposito_garantia_usd=Decimal("0.00"),
        requiere_solvencia_estricta=False,
        es_activa=True,
    )
    reserva_ocupada = ReservaAreaSocial(
        id=50,
        area_id=4,
        unidad_id=19,
        solicitante_id=2,
        fecha_evento=date(2026, 12, 24),
        motivo_evento="Torneo deportivo",
        estado="CONFIRMADA",
    )

    # 1. Fecha ya ocupada -> 409 Conflict (Presidente salta validación de contrato y área no exige solvencia)
    session_ocupada = _mock_session(
        _result(unidad),
        _result(area_sin_candado),
        _result(reserva_ocupada),
    )
    _setup(session_ocupada, FakeUser(1, "PRESIDENTE"))
    client = TestClient(app)

    resp_409 = client.post(
        "/api/reservas/solicitar",
        headers=HEADERS,
        json={
            "area_id": 4,
            "unidad_id": 12,
            "fecha_evento": "2026-12-24",
            "motivo_evento": "Partido amistoso vecinal",
        },
    )
    assert resp_409.status_code == 409
    assert "ya se encuentra reservada" in resp_409.json()["detail"]

    # 2. Unidad inexistente -> 404
    _setup(_mock_session(_result(None)), FakeUser(1, "PRESIDENTE"))
    resp_u404 = client.post(
        "/api/reservas/solicitar",
        headers=HEADERS,
        json={
            "area_id": 4,
            "unidad_id": 999,
            "fecha_evento": "2026-12-25",
            "motivo_evento": "Evento vecinal",
        },
    )
    assert resp_u404.status_code == 404

    # 3. Usuario sin contrato en unidad -> 403
    _setup(_mock_session(_result(unidad), _result_list([99])), FakeUser(7, "RESIDENTE"))
    resp_u403 = client.post(
        "/api/reservas/solicitar",
        headers=HEADERS,
        json={
            "area_id": 4,
            "unidad_id": 12,
            "fecha_evento": "2026-12-25",
            "motivo_evento": "Evento vecinal",
        },
    )
    assert resp_u403.status_code == 403

    # 4. Área inexistente o inactiva -> 404
    _setup(_mock_session(_result(unidad), _result(None)), FakeUser(1, "PRESIDENTE"))
    resp_a404 = client.post(
        "/api/reservas/solicitar",
        headers=HEADERS,
        json={
            "area_id": 999,
            "unidad_id": 12,
            "fecha_evento": "2026-12-25",
            "motivo_evento": "Evento vecinal",
        },
    )
    assert resp_a404.status_code == 404

    # 5. Idempotency-Key duplicada -> 409
    _setup(_mock_session(), FakeUser(1, "PRESIDENTE"), redis_new=False)
    resp_idem = client.post(
        "/api/reservas/solicitar",
        headers=HEADERS,
        json={
            "area_id": 4,
            "unidad_id": 12,
            "fecha_evento": "2026-12-25",
            "motivo_evento": "Evento vecinal",
        },
    )
    assert resp_idem.status_code == 409
    app.dependency_overrides.clear()


# ==============================================================================
# 3. LISTADO E INSPECCIÓN POST-EVENTO (/api/reservas y /inspeccionar)
# ==============================================================================


def test_listar_reservas_junta_y_residente() -> None:
    r1 = ReservaAreaSocial(
        id=1,
        area_id=3,
        unidad_id=12,
        solicitante_id=7,
        fecha_evento=date(2026, 12, 15),
        motivo_evento="Cumpleaños",
        estado="CONFIRMADA",
        tarea_inspeccion_id=100,
        creado_en=datetime(2026, 10, 30, 12, 0, 0),  # naive datetime para cubrir rama tzinfo is None
    )
    r2 = ReservaAreaSocial(
        id=2,
        area_id=3,
        unidad_id=18,
        solicitante_id=9,
        fecha_evento=date(2026, 12, 16),
        motivo_evento="Aniversario",
        estado="CONFIRMADA",
        tarea_inspeccion_id=101,
    )
    area = AreaSocial(id=3, nombre="Salón Principal", aforo_maximo=50)
    u12 = Unidad(id=12, estructura_id=1, identificador="PB-02", alicuota=Decimal("2.5000"))
    u18 = Unidad(id=18, estructura_id=1, identificador="PB-08", alicuota=Decimal("2.5000"))

    # Conserje ve todas las reservas
    session_conserje = _mock_session(
        _result_list([r1, r2]),
        _result_list([area]),
        _result_list([u12, u18]),
    )
    _setup(session_conserje, FakeUser(4, "CONSERJE"))
    client = TestClient(app)

    resp_all = client.get("/api/reservas")
    assert resp_all.status_code == 200
    assert len(resp_all.json()) == 2

    # Residente ve solo las de su unidad
    session_res = _mock_session(
        _result_list([r1, r2]),
        _result_list([area]),
        _result_list([u12, u18]),
        _result_list([12]),
    )
    _setup(session_res, FakeUser(7, "RESIDENTE"))
    resp_own = client.get("/api/reservas")
    assert resp_own.status_code == 200
    assert len(resp_own.json()) == 1
    assert resp_own.json()[0]["identificador_unidad"] == "PB-02"
    app.dependency_overrides.clear()


def test_inspeccionar_entrega_area_social_completa_tarea_conserje() -> None:
    tarea = TareaDiaria(
        id=100,
        titulo="Inspeccionar entrega de Salón Principal tras reserva de Unidad PB-02",
        area="Salón Principal",
        fecha=date(2026, 12, 15),
        completada=False,
    )
    reserva = ReservaAreaSocial(
        id=15,
        area_id=3,
        unidad_id=12,
        solicitante_id=7,
        fecha_evento=date(2026, 12, 15),
        motivo_evento="Cumpleaños",
        estado="CONFIRMADA",
        tarea_inspeccion_id=100,
    )
    area = AreaSocial(id=3, nombre="Salón Principal", aforo_maximo=50)
    unidad = Unidad(id=12, estructura_id=1, identificador="PB-02", alicuota=Decimal("2.5000"))

    session = _mock_session(
        _result(reserva),
        _result(tarea),
        _result(area),
        _result(unidad),
    )
    _setup(session, FakeUser(4, "CONSERJE"))
    client = TestClient(app)

    resp = client.put(
        "/api/reservas/15/inspeccionar",
        json={
            "estado": "FINALIZADA_SIN_DANOS",
            "observaciones_inspeccion": "Instalaciones entregadas limpias y sin novedades.",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["estado"] == "FINALIZADA_SIN_DANOS"
    assert body["observaciones_inspeccion"] == "Instalaciones entregadas limpias y sin novedades."
    assert tarea.completada is True
    assert tarea.completada_en is not None

    # Re-inspeccionar una reserva ya cerrada -> 409 Conflict
    session_dup = _mock_session(_result(reserva))
    _setup(session_dup, FakeUser(4, "CONSERJE"))
    resp_409 = client.put(
        "/api/reservas/15/inspeccionar",
        json={
            "estado": "FINALIZADA_CON_DANOS",
            "observaciones_inspeccion": "Intento duplicado",
        },
    )
    assert resp_409.status_code == 409

    # Reserva sin tarea_inspeccion_id asociada -> 200 OK
    reserva_sin_tarea = ReservaAreaSocial(
        id=16,
        area_id=3,
        unidad_id=12,
        solicitante_id=7,
        fecha_evento=date(2026, 12, 18),
        motivo_evento="Cena",
        estado="CONFIRMADA",
        tarea_inspeccion_id=None,
    )
    session_sin_tarea = _mock_session(_result(reserva_sin_tarea), _result(None), _result(None))
    _setup(session_sin_tarea, FakeUser(1, "PRESIDENTE"))
    resp_sin_tarea = client.put(
        "/api/reservas/16/inspeccionar",
        json={
            "estado": "FINALIZADA_CON_DANOS",
            "observaciones_inspeccion": "Silla plástica rota en terraza.",
        },
    )
    assert resp_sin_tarea.status_code == 200
    assert resp_sin_tarea.json()["estado"] == "FINALIZADA_CON_DANOS"

    # Reserva inexistente -> 404
    _setup(_mock_session(_result(None)), FakeUser(4, "CONSERJE"))
    resp_404 = client.put(
        "/api/reservas/999/inspeccionar",
        json={
            "estado": "FINALIZADA_SIN_DANOS",
            "observaciones_inspeccion": "No existe",
        },
    )
    assert resp_404.status_code == 404
    app.dependency_overrides.clear()
