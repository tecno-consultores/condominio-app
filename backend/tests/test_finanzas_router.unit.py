"""Pruebas unitarias de tesorería: tasa del día, resumen y Candado Contable."""

from datetime import date
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from src.database import get_db
from src.dependencies import get_current_user
from src.main import app
from src.models import Egreso, Recibo, ReporteMensual, TasaCambio
from src.redis_client import get_redis_client

HEADERS = {"Idempotency-Key": "22222222-2222-2222-2222-222222222222"}


class FakeUser:
    id: int = 3
    correo: str = "tesorero@test.com"
    rol: str = "TESORERO"


def _mock_session(*results: Any) -> AsyncMock:
    session = AsyncMock()
    session.execute.side_effect = list(results)
    session.add = MagicMock()

    async def refresh(instance: Any, *args: object, **kwargs: object) -> None:
        if getattr(instance, "id", None) is None:
            instance.id = 1

    session.refresh = refresh
    return session


def _result(value: Any) -> MagicMock:
    result = MagicMock()
    result.scalars().first.return_value = value
    return result


def _result_list(values: list[Any]) -> MagicMock:
    result = MagicMock()
    result.scalars().all.return_value = values
    return result


def _result_pairs(rows: list[tuple[Any, ...]]) -> MagicMock:
    result = MagicMock()
    result.all.return_value = rows
    return result


def _setup(session: AsyncMock, user: Any = None, redis_is_new: bool = True) -> AsyncMock:
    mock_redis = AsyncMock()
    mock_redis.set.return_value = redis_is_new
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_redis_client] = lambda: mock_redis
    app.dependency_overrides[get_current_user] = lambda: user or FakeUser()
    return mock_redis


def _tasa() -> TasaCambio:
    return TasaCambio(id=1, fecha=date.today(), tasa_usd_ves=Decimal("36.5000"))


def _recibo(bloqueado: bool = False) -> Recibo:
    return Recibo(
        id=1,
        unidad_id=1,
        periodo="2026-10",
        monto_usd=Decimal("100.00"),
        monto_pagado_usd=Decimal("0.00"),
        estado="PENDIENTE",
        bloqueado=bloqueado,
    )


def _egreso(categoria: str = "MANTENIMIENTO", monto_usd: str = "30.00", bloqueado: bool = False) -> Egreso:
    return Egreso(
        id=1,
        periodo="2026-10",
        categoria=categoria,
        descripcion="Pago servicio",
        monto=Decimal(monto_usd),
        moneda="USD",
        monto_usd=Decimal(monto_usd),
        tasa_cambio=Decimal("36.5000"),
        url_factura=None,
        bloqueado=bloqueado,
    )


def test_registrar_tasa_nueva(client: TestClient) -> None:
    session = _mock_session(_result(None))
    _setup(session)

    response = client.post("/api/finanzas/tasa", json={"tasa_usd_ves": "36.5000"})

    assert response.status_code == 201
    assert float(response.json()["tasa_usd_ves"]) == 36.5
    assert session.add.call_count == 1

    app.dependency_overrides = {}


def test_registrar_tasa_existente_actualiza(client: TestClient) -> None:
    tasa = _tasa()
    session = _mock_session(_result(tasa))
    _setup(session)

    response = client.post(
        "/api/finanzas/tasa",
        json={"fecha": "2026-10-12", "tasa_usd_ves": "40.0000"},
    )

    assert response.status_code == 201
    assert tasa.tasa_usd_ves == Decimal("40.0000")
    assert session.add.call_count == 0

    app.dependency_overrides = {}


def test_registrar_tasa_invalida_es_422(client: TestClient) -> None:
    _setup(_mock_session())
    response = client.post("/api/finanzas/tasa", json={"tasa_usd_ves": "0"})
    assert response.status_code == 422
    app.dependency_overrides = {}


def test_obtener_tasa_del_dia(client: TestClient) -> None:
    session = _mock_session(_result(_tasa()))
    _setup(session)

    response = client.get("/api/finanzas/tasa")

    assert response.status_code == 200
    assert float(response.json()["tasa_usd_ves"]) == 36.5

    app.dependency_overrides = {}


def test_obtener_tasa_no_registrada(client: TestClient) -> None:
    session = _mock_session(_result(None))
    _setup(session)

    response = client.get("/api/finanzas/tasa")

    assert response.status_code == 404

    app.dependency_overrides = {}


def test_registrar_egreso_success(client: TestClient) -> None:
    session = _mock_session(_result(None), _result(_tasa()))
    _setup(session)
    payload = {
        "periodo": "2026-10",
        "categoria": "MANTENIMIENTO",
        "descripcion": "Cambio de bombillos",
        "monto": "3650.00",
        "moneda": "VES",
    }

    response = client.post("/api/finanzas/egresos", json=payload, headers=HEADERS)

    assert response.status_code == 201
    assert float(response.json()["monto_usd"]) == 100.0

    app.dependency_overrides = {}


def test_registrar_egreso_sin_tasa(client: TestClient) -> None:
    session = _mock_session(_result(None), _result(None))
    _setup(session)
    payload = {
        "periodo": "2026-10",
        "categoria": "MANTENIMIENTO",
        "descripcion": "X",
        "monto": "100.00",
        "moneda": "USD",
    }

    response = client.post("/api/finanzas/egresos", json=payload, headers=HEADERS)

    assert response.status_code == 400

    app.dependency_overrides = {}


def test_registrar_egreso_falla_bd(client: TestClient) -> None:
    session = _mock_session(_result(None), _result(_tasa()))
    session.commit.side_effect = Exception("DB down")
    _setup(session)
    payload = {
        "periodo": "2026-10",
        "categoria": "MANTENIMIENTO",
        "descripcion": "X",
        "monto": "100.00",
        "moneda": "USD",
    }

    response = client.post("/api/finanzas/egresos", json=payload, headers=HEADERS)

    assert response.status_code == 500

    app.dependency_overrides = {}


def test_registrar_egreso_periodo_invalido_es_422(client: TestClient) -> None:
    _setup(_mock_session())
    payload = {
        "periodo": "2026/10",
        "categoria": "MANTENIMIENTO",
        "descripcion": "X",
        "monto": "100.00",
        "moneda": "USD",
    }
    response = client.post("/api/finanzas/egresos", json=payload, headers=HEADERS)
    assert response.status_code == 422
    app.dependency_overrides = {}


def test_registrar_egreso_tasa_cero_falla(client: TestClient) -> None:
    tasa_cero = TasaCambio(id=1, fecha=date.today(), tasa_usd_ves=Decimal(0))
    session = _mock_session(_result(None), _result(tasa_cero))
    _setup(session)
    payload = {
        "periodo": "2026-10",
        "categoria": "MANTENIMIENTO",
        "descripcion": "X",
        "monto": "100.00",
        "moneda": "VES",
    }

    response = client.post("/api/finanzas/egresos", json=payload, headers=HEADERS)

    assert response.status_code == 400

    app.dependency_overrides = {}


def test_registrar_egreso_candado_contable_e_idempotencia(client: TestClient) -> None:
    payload = {
        "periodo": "2026-10",
        "categoria": "MANTENIMIENTO",
        "descripcion": "Gasto extemporáneo tras cierre",
        "monto": "50.00",
        "moneda": "USD",
    }

    # 1. Falta Idempotency-Key -> 422
    _setup(_mock_session())
    assert client.post("/api/finanzas/egresos", json=payload).status_code == 422

    # 2. Idempotency-Key repetida -> 409
    _setup(_mock_session(), redis_is_new=False)
    res_dup = client.post("/api/finanzas/egresos", json=payload, headers=HEADERS)
    assert res_dup.status_code == 409
    assert "Idempotency-Key" in res_dup.json()["detail"]

    # 3. Periodo cerrado en ReporteMensual -> 409 Candado Contable
    reporte_cerrado = ReporteMensual(id=1, periodo="2026-10", estado="CERRADO")
    _setup(_mock_session(_result(reporte_cerrado)))
    res_cerrado = client.post("/api/finanzas/egresos", json=payload, headers=HEADERS)
    assert res_cerrado.status_code == 409
    assert "Candado Contable" in res_cerrado.json()["detail"]

    app.dependency_overrides = {}


def test_resumen_financiero(client: TestClient) -> None:
    recibos = [
        Recibo(
            id=1,
            unidad_id=1,
            periodo="2026-10",
            monto_usd=Decimal("100.00"),
            monto_pagado_usd=Decimal("0.00"),
            estado="PENDIENTE",
            bloqueado=False,
        ),
        Recibo(
            id=2,
            unidad_id=2,
            periodo="2026-10",
            monto_usd=Decimal("50.00"),
            monto_pagado_usd=Decimal("50.00"),
            estado="PAGADO",
            bloqueado=False,
        ),
        Recibo(
            id=3,
            unidad_id=3,
            periodo="2026-10",
            monto_usd=Decimal("200.00"),
            monto_pagado_usd=Decimal("100.00"),
            estado="PAGADO_PARCIAL",
            bloqueado=False,
        ),
    ]
    session = _mock_session(
        _result_list(recibos),
        _result_pairs([("MANTENIMIENTO", Decimal("30.00")), ("LIMPIEZA", Decimal("70.00"))]),
    )
    _setup(session)

    response = client.get("/api/finanzas/resumen")

    assert response.status_code == 200
    body = response.json()
    assert float(body["deuda_total_usd"]) == 200.0
    assert float(body["total_egresos_usd"]) == 100.0
    assert float(body["gastos_por_categoria"]["MANTENIMIENTO"]) == 30.0
    assert float(body["gastos_por_categoria"]["LIMPIEZA"]) == 70.0
    assert len(body["estado_cobranza"]) == 3

    app.dependency_overrides = {}


def test_cierre_mensual_success(client: TestClient) -> None:
    recibo = _recibo()
    egreso = _egreso()
    session = _mock_session(_result(None), _result_list([recibo]), _result_list([egreso]))
    _setup(session)

    response = client.post("/api/finanzas/cierre-mensual", json={"periodo": "2026-10"})

    assert response.status_code == 200
    assert response.json()["estado"] == "CERRADO"
    assert recibo.bloqueado is True
    assert egreso.bloqueado is True
    assert session.add.call_count == 1

    app.dependency_overrides = {}


def test_cierre_mensual_ya_cerrado_es_inmutable(client: TestClient) -> None:
    reporte = ReporteMensual(id=1, periodo="2026-10", estado="CERRADO")
    session = _mock_session(_result(reporte))
    _setup(session)

    response = client.post("/api/finanzas/cierre-mensual", json={"periodo": "2026-10"})

    assert response.status_code == 409
    assert "inmutable" in response.json()["detail"]

    app.dependency_overrides = {}


def test_cierre_mensual_periodo_invalido_es_422(client: TestClient) -> None:
    _setup(_mock_session())
    response = client.post("/api/finanzas/cierre-mensual", json={"periodo": "2026-1"})
    assert response.status_code == 422
    app.dependency_overrides = {}


def test_finanzas_rbac_y_bloqueo_fantasma(client: TestClient) -> None:
    class GhostUser:
        id: int = 99
        correo: str = "fantasma@test.com"
        rol: str = "FANTASMA"
        es_activo: bool = False

    class PropietarioUser:
        id: int = 88
        correo: str = "vecino@test.com"
        rol: str = "PROPIETARIO"
        es_activo: bool = True

    _setup(_mock_session(), user=GhostUser())
    assert client.get("/api/finanzas/resumen").status_code == 403
    assert client.get("/api/finanzas/tasa").status_code == 403

    _setup(_mock_session(), user=PropietarioUser())
    assert client.post("/api/finanzas/tasa", json={"tasa_usd_ves": "36.5000"}).status_code == 403
    assert (
        client.post(
            "/api/finanzas/egresos",
            json={"periodo": "2026-10", "categoria": "A", "descripcion": "X", "monto": "10.00", "moneda": "USD"},
            headers=HEADERS,
        ).status_code
        == 403
    )
    assert client.post("/api/finanzas/cierre-mensual", json={"periodo": "2026-10"}).status_code == 403
    app.dependency_overrides = {}
