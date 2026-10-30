"""Pruebas unitarias del flujo de reporte y aprobación de pagos (mockeando BD/Redis)."""

from datetime import date
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from src.database import get_db
from src.dependencies import get_current_user
from src.main import app
from src.models import PagoReportado, Recibo, TasaCambio
from src.redis_client import get_redis_client


class FakeUser:
    id: int = 7
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


def _setup(session: AsyncMock, redis_is_new: bool = True, user: Any = None) -> AsyncMock:
    mock_redis = AsyncMock()
    mock_redis.set.return_value = redis_is_new
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_redis_client] = lambda: mock_redis
    app.dependency_overrides[get_current_user] = lambda: user or FakeUser()
    return mock_redis


def _tasa() -> TasaCambio:
    return TasaCambio(id=1, fecha=date.today(), tasa_usd_ves=Decimal("36.5000"))


def _recibo(bloqueado: bool = False, pagado: str = "0.00") -> Recibo:
    return Recibo(
        id=1,
        unidad_id=1,
        periodo="2026-10",
        monto_usd=Decimal("100.00"),
        monto_pagado_usd=Decimal(pagado),
        estado="PENDIENTE",
        bloqueado=bloqueado,
    )


def _pago(estado: str = "EN_REVISION", monto_usd: str = "40.00") -> PagoReportado:
    return PagoReportado(
        id=5,
        recibo_id=1,
        usuario_id=7,
        monto=Decimal(monto_usd),
        moneda="USD",
        monto_usd=Decimal(monto_usd),
        tasa_cambio=Decimal("36.5000"),
        metodo_pago="EFECTIVO",
        numero_referencia=None,
        url_comprobante=None,
        estado=estado,
    )


PAYLOAD = {"recibo_id": 1, "monto": "100.00", "moneda": "USD", "metodo_pago": "EFECTIVO"}
HEADERS = {"Idempotency-Key": "11111111-1111-1111-1111-111111111111"}


def test_reportar_pago_success(client: TestClient) -> None:
    session = _mock_session(_result(_tasa()), _result(_recibo()))
    _setup(session)

    response = client.post("/api/pagos/reportar", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 201
    body = response.json()
    assert float(body["monto_usd"]) == 100.0
    assert float(body["tasa_cambio"]) == 36.5
    assert body["estado"] == "EN_REVISION"
    assert session.add.call_count == 1

    app.dependency_overrides = {}


def test_reportar_pago_ves_convierte_por_tasa_del_dia(client: TestClient) -> None:
    session = _mock_session(_result(_tasa()), _result(_recibo()))
    _setup(session)
    payload = {"recibo_id": 1, "monto": "3650.00", "moneda": "VES", "metodo_pago": "EFECTIVO"}

    response = client.post("/api/pagos/reportar", json=payload, headers=HEADERS)

    assert response.status_code == 201
    assert float(response.json()["monto_usd"]) == 100.0

    app.dependency_overrides = {}


def test_reportar_pago_duplicado(client: TestClient) -> None:
    session = _mock_session()
    _setup(session, redis_is_new=False)

    response = client.post("/api/pagos/reportar", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 409
    assert "Petición duplicada" in response.json()["detail"]

    app.dependency_overrides = {}


def test_reportar_pago_zelle_sin_referencia_falla(client: TestClient) -> None:
    session = _mock_session()
    _setup(session)
    payload = {"recibo_id": 1, "monto": "100.00", "moneda": "USD", "metodo_pago": "ZELLE"}

    response = client.post("/api/pagos/reportar", json=payload, headers=HEADERS)

    assert response.status_code == 400
    assert "referencia" in response.json()["detail"]

    app.dependency_overrides = {}


def test_reportar_pago_tasa_no_registrada(client: TestClient) -> None:
    session = _mock_session(_result(None))
    _setup(session)

    response = client.post("/api/pagos/reportar", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 400
    assert "tasa de cambio" in response.json()["detail"].lower()

    app.dependency_overrides = {}


def test_reportar_pago_recibo_no_encontrado(client: TestClient) -> None:
    session = _mock_session(_result(_tasa()), _result(None))
    _setup(session)

    response = client.post("/api/pagos/reportar", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 404
    assert "Recibo no encontrado" in response.json()["detail"]

    app.dependency_overrides = {}


def test_reportar_pago_mes_bloqueado(client: TestClient) -> None:
    session = _mock_session(_result(_tasa()), _result(_recibo(bloqueado=True)))
    _setup(session)

    response = client.post("/api/pagos/reportar", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 409
    assert "Candado Contable" in response.json()["detail"]

    app.dependency_overrides = {}


def test_reportar_pago_moneda_invalida_es_422(client: TestClient) -> None:
    _setup(_mock_session())
    payload = {"recibo_id": 1, "monto": "10.00", "moneda": "EUR", "metodo_pago": "EFECTIVO"}
    response = client.post("/api/pagos/reportar", json=payload, headers=HEADERS)
    assert response.status_code == 422
    app.dependency_overrides = {}


def test_reportar_pago_sin_idempotency_key(client: TestClient) -> None:
    _setup(_mock_session())
    response = client.post("/api/pagos/reportar", json=PAYLOAD)
    assert response.status_code == 422
    app.dependency_overrides = {}


def test_reportar_pago_falla_bd(client: TestClient) -> None:
    session = _mock_session(_result(_tasa()), _result(_recibo()))
    session.commit.side_effect = Exception("DB down")
    _setup(session)

    response = client.post("/api/pagos/reportar", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 500
    assert "Error en base de datos" in response.json()["detail"]

    app.dependency_overrides = {}


def test_listar_pagos_en_revision(client: TestClient) -> None:
    session = _mock_session(_result_list([_pago()]))
    _setup(session)

    response = client.get("/api/pagos/revision")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["estado"] == "EN_REVISION"

    app.dependency_overrides = {}


def test_aprobar_pago_parcial(client: TestClient) -> None:
    pago = _pago(monto_usd="40.00")
    recibo = _recibo()
    session = _mock_session(_result(pago), _result(recibo))
    _setup(session)

    response = client.put("/api/pagos/5/aprobar")

    assert response.status_code == 200
    assert response.json()["estado"] == "APROBADO"
    assert recibo.estado == "PAGADO_PARCIAL"
    assert recibo.monto_pagado_usd == Decimal("40.00")
    assert session.add.call_count == 1

    app.dependency_overrides = {}


def test_aprobar_pago_total_exacto(client: TestClient) -> None:
    pago = _pago(monto_usd="100.00")
    recibo = _recibo()
    session = _mock_session(_result(pago), _result(recibo))
    _setup(session)

    response = client.put("/api/pagos/5/aprobar")

    assert response.status_code == 200
    assert recibo.estado == "PAGADO"
    assert recibo.monto_pagado_usd == Decimal("100.00")

    app.dependency_overrides = {}


def test_aprobar_pago_parcial_sobre_saldo_previo(client: TestClient) -> None:
    pago = _pago(monto_usd="30.00")
    recibo = _recibo(pagado="40.00")
    session = _mock_session(_result(pago), _result(recibo))
    _setup(session)

    client.put("/api/pagos/5/aprobar")

    assert recibo.monto_pagado_usd == Decimal("70.00")
    assert recibo.estado == "PAGADO_PARCIAL"

    app.dependency_overrides = {}


def test_aprobar_pago_no_encontrado(client: TestClient) -> None:
    session = _mock_session(_result(None))
    _setup(session)

    response = client.put("/api/pagos/999/aprobar")

    assert response.status_code == 404
    assert "Pago no encontrado" in response.json()["detail"]

    app.dependency_overrides = {}


def test_aprobar_pago_no_esta_en_revision(client: TestClient) -> None:
    session = _mock_session(_result(_pago(estado="APROBADO")))
    _setup(session)

    response = client.put("/api/pagos/5/aprobar")

    assert response.status_code == 409
    assert "no está en revisión" in response.json()["detail"]

    app.dependency_overrides = {}


def test_aprobar_recibo_no_encontrado(client: TestClient) -> None:
    session = _mock_session(_result(_pago()), _result(None))
    _setup(session)

    response = client.put("/api/pagos/5/aprobar")

    assert response.status_code == 404
    assert "Recibo no encontrado" in response.json()["detail"]

    app.dependency_overrides = {}


def test_aprobar_mes_bloqueado(client: TestClient) -> None:
    session = _mock_session(_result(_pago()), _result(_recibo(bloqueado=True)))
    _setup(session)

    response = client.put("/api/pagos/5/aprobar")

    assert response.status_code == 409
    assert "Candado Contable" in response.json()["detail"]

    app.dependency_overrides = {}


def test_rechazar_pago_success(client: TestClient) -> None:
    pago = _pago()
    recibo = _recibo()
    session = _mock_session(_result(pago), _result(recibo))
    _setup(session)

    response = client.put("/api/pagos/5/rechazar", json={"motivo": "Comprobante ilegible"})

    assert response.status_code == 200
    assert response.json()["estado"] == "RECHAZADO"
    assert pago.estado == "RECHAZADO"
    audit = session.add.call_args[0][0]
    assert audit.motivo == "Comprobante ilegible"
    assert audit.estado_nuevo == "RECHAZADO"

    app.dependency_overrides = {}


def test_rechazar_pago_sin_motivo_es_422(client: TestClient) -> None:
    _setup(_mock_session())
    response = client.put("/api/pagos/5/rechazar", json={"motivo": ""})
    assert response.status_code == 422
    app.dependency_overrides = {}


def test_rechazar_pago_no_encontrado(client: TestClient) -> None:
    session = _mock_session(_result(None))
    _setup(session)

    response = client.put("/api/pagos/999/rechazar", json={"motivo": "X"})

    assert response.status_code == 404

    app.dependency_overrides = {}


def test_rechazar_pago_no_esta_en_revision(client: TestClient) -> None:
    session = _mock_session(_result(_pago(estado="RECHAZADO")))
    _setup(session)

    response = client.put("/api/pagos/5/rechazar", json={"motivo": "X"})

    assert response.status_code == 409

    app.dependency_overrides = {}


def test_rechazar_mes_bloqueado(client: TestClient) -> None:
    session = _mock_session(_result(_pago()), _result(_recibo(bloqueado=True)))
    _setup(session)

    response = client.put("/api/pagos/5/rechazar", json={"motivo": "X"})

    assert response.status_code == 409
    assert "Candado Contable" in response.json()["detail"]

    app.dependency_overrides = {}


def test_pagos_rbac_y_bloqueo_fantasma(client: TestClient) -> None:
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
    assert client.post("/api/pagos/reportar", json=PAYLOAD, headers=HEADERS).status_code == 403

    _setup(_mock_session(), user=PropietarioUser())
    assert client.get("/api/pagos/revision").status_code == 403
    assert client.put("/api/pagos/5/aprobar").status_code == 403
    assert client.put("/api/pagos/5/rechazar", json={"motivo": "Motivo válido"}).status_code == 403
    app.dependency_overrides = {}
