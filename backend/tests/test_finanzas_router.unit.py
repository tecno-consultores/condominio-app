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


def _setup(session: AsyncMock, user: Any = None) -> None:
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: user or FakeUser()


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
    session = _mock_session(_result(_tasa()))
    _setup(session)
    payload = {
        "periodo": "2026-10",
        "categoria": "MANTENIMIENTO",
        "descripcion": "Cambio de bombillos",
        "monto": "3650.00",
        "moneda": "VES",
    }

    response = client.post("/api/finanzas/egresos", json=payload)

    assert response.status_code == 201
    assert float(response.json()["monto_usd"]) == 100.0

    app.dependency_overrides = {}


def test_registrar_egreso_sin_tasa(client: TestClient) -> None:
    session = _mock_session(_result(None))
    _setup(session)
    payload = {
        "periodo": "2026-10",
        "categoria": "MANTENIMIENTO",
        "descripcion": "X",
        "monto": "100.00",
        "moneda": "USD",
    }

    response = client.post("/api/finanzas/egresos", json=payload)

    assert response.status_code == 400

    app.dependency_overrides = {}


def test_registrar_egreso_falla_bd(client: TestClient) -> None:
    session = _mock_session(_result(_tasa()))
    session.commit.side_effect = Exception("DB down")
    _setup(session)
    payload = {
        "periodo": "2026-10",
        "categoria": "MANTENIMIENTO",
        "descripcion": "X",
        "monto": "100.00",
        "moneda": "USD",
    }

    response = client.post("/api/finanzas/egresos", json=payload)

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
    response = client.post("/api/finanzas/egresos", json=payload)
    assert response.status_code == 422
    app.dependency_overrides = {}


def test_registrar_egreso_tasa_cero_falla(client: TestClient) -> None:
    tasa_cero = TasaCambio(id=1, fecha=date.today(), tasa_usd_ves=Decimal("0"))
    session = _mock_session(_result(tasa_cero))
    _setup(session)
    payload = {
        "periodo": "2026-10",
        "categoria": "MANTENIMIENTO",
        "descripcion": "X",
        "monto": "100.00",
        "moneda": "VES",
    }

    response = client.post("/api/finanzas/egresos", json=payload)

    assert response.status_code == 400

    app.dependency_overrides = {}


def test_resumen_financiero(client: TestClient) -> None:
    recibos = [
        Recibo(id=1, unidad_id=1, periodo="2026-10", monto_usd=Decimal("100.00"),
               monto_pagado_usd=Decimal("0.00"), estado="PENDIENTE", bloqueado=False),
        Recibo(id=2, unidad_id=2, periodo="2026-10", monto_usd=Decimal("50.00"),
               monto_pagado_usd=Decimal("50.00"), estado="PAGADO", bloqueado=False),
        Recibo(id=3, unidad_id=3, periodo="2026-10", monto_usd=Decimal("200.00"),
               monto_pagado_usd=Decimal("100.00"), estado="PAGADO_PARCIAL", bloqueado=False),
    ]
    egresos = [_egreso(monto_usd="30.00"), _egreso(categoria="LIMPIEZA", monto_usd="70.00")]
    session = _mock_session(_result_list(recibos), _result_list(egresos))
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
