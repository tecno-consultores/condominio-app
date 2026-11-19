import inspect
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from src import schemas as schemas_module
from src.routers.auth import LoginData
from src.schemas import (
    CierreMensualRequest,
    ComunicadoCreate,
    EgresoCreate,
    PagoRechazo,
    PagoReportar,
    PaseVisitaCreate,
    ReciboCreate,
    TasaCambioCreate,
    UnidadResponse,
    UsuarioCreate,
    UsuarioResponse,
)


def test_usuario_schema_valido() -> None:
    """Valida que Pydantic acepta un payload de registro correcto con los nuevos campos"""
    user = UsuarioCreate(
        nombre="Juan Perez",
        cedula="V-12345678",
        correo="juan@example.com",
        telefono="+584121234567",
        password="SecurePassword123!",
        unidad_solicitada_id=1,
        tipo_ocupante_solicitado="PROPIETARIO",
    )
    assert user.nombre == "Juan Perez"
    assert user.password == "SecurePassword123!"
    assert user.unidad_solicitada_id == 1
    assert user.tipo_ocupante_solicitado == "PROPIETARIO"


def test_usuario_schema_correo_invalido() -> None:
    """Valida que Pydantic rechaza correos malformados de acuerdo a EmailStr"""
    with pytest.raises(ValidationError) as exc_info:
        UsuarioCreate(
            nombre="Maria Lopez",
            cedula="V-87654321",
            correo="maria-correo-falso",
            telefono="+584129876543",
            password="SecurePassword123!",
            unidad_solicitada_id=1,
            tipo_ocupante_solicitado="INQUILINO",
        )

    assert "correo" in str(exc_info.value)


def test_usuario_response_from_attributes() -> None:
    """Valida que UsuarioResponse construye correctamente el modelo a partir de atributos"""

    class MockUsuario:
        id: int = 10
        nombre: str = "Ana Morales"
        cedula: str = "V-20000000"
        correo: str = "ana@example.com"
        telefono: str = "+584140000000"
        es_activo: bool = False
        rol: str = "FANTASMA"

    response = UsuarioResponse.model_validate(MockUsuario())
    assert response.id == 10
    assert response.nombre == "Ana Morales"
    assert response.es_activo is False
    assert response.rol == "FANTASMA"


def test_pago_reportar_schema_valido() -> None:
    pago = PagoReportar(recibo_id=1, monto=Decimal("100.00"), moneda="USD", metodo_pago="EFECTIVO")
    assert pago.moneda == "USD"
    assert pago.numero_referencia is None
    assert pago.url_comprobante is None


def test_pago_reportar_moneda_invalida() -> None:
    with pytest.raises(ValidationError):
        PagoReportar.model_validate({"recibo_id": 1, "monto": "100.00", "moneda": "EUR", "metodo_pago": "EFECTIVO"})


def test_pago_reportar_monto_no_positivo() -> None:
    with pytest.raises(ValidationError):
        PagoReportar(recibo_id=1, monto=Decimal(0), moneda="USD", metodo_pago="EFECTIVO")


def test_pago_rechazo_motivo_vacio_invalido() -> None:
    with pytest.raises(ValidationError):
        PagoRechazo(motivo="")


def test_pago_rechazo_motivo_valido() -> None:
    assert PagoRechazo(motivo="Sin comprobante").motivo == "Sin comprobante"


def test_tasa_cambio_schema_tasa_no_positiva() -> None:
    with pytest.raises(ValidationError):
        TasaCambioCreate(tasa_usd_ves=Decimal(0))


def test_tasa_cambio_schema_fecha_opcional() -> None:
    tasa = TasaCambioCreate(tasa_usd_ves=Decimal("36.5000"))
    assert tasa.fecha is None


def test_recibo_schema_periodo_invalido() -> None:
    with pytest.raises(ValidationError):
        ReciboCreate(unidad_id=1, periodo="2026/10", monto_usd=Decimal("100.00"))


def test_recibo_schema_valido() -> None:
    recibo = ReciboCreate(unidad_id=1, periodo="2026-10", monto_usd=Decimal("100.00"))
    assert recibo.periodo == "2026-10"


def test_egreso_create_schema_valido() -> None:
    egreso = EgresoCreate(
        periodo="2026-10",
        categoria="LIMPIEZA",
        descripcion="Insumos",
        monto=Decimal("50.00"),
        moneda="VES",
    )
    assert egreso.categoria == "LIMPIEZA"


def test_cierre_mensual_request_valido() -> None:
    assert CierreMensualRequest(periodo="2026-10").periodo == "2026-10"


def test_cierre_mensual_request_periodo_invalido() -> None:
    with pytest.raises(ValidationError):
        CierreMensualRequest(periodo="octubre")


def test_url_evidencia_segura_bloquea_esquemas_peligrosos() -> None:
    """Valida que UrlEvidenciaSegura bloquea javascript:, data:, file: y URLs sin esquema válido."""
    for url_maliciosa in [
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "file:///etc/passwd",
        "   ",
        "ftp://servidor.interno/archivo.png",
    ]:
        with pytest.raises(ValidationError):
            PagoReportar(
                recibo_id=1,
                monto=Decimal("50.00"),
                moneda="USD",
                metodo_pago="EFECTIVO",
                url_comprobante=url_maliciosa,
            )

    pago_https = PagoReportar(
        recibo_id=1,
        monto=Decimal("50.00"),
        moneda="USD",
        metodo_pago="EFECTIVO",
        url_comprobante="https://cdn.condominio.local/recibos/1.avif",
    )
    assert pago_https.url_comprobante == "https://cdn.condominio.local/recibos/1.avif"

    pago_relativo = PagoReportar(
        recibo_id=1,
        monto=Decimal("50.00"),
        moneda="USD",
        metodo_pago="EFECTIVO",
        url_comprobante="/media/recibos/1.avif",
    )
    assert pago_relativo.url_comprobante == "/media/recibos/1.avif"


def _descubrir_esquemas_publicos() -> dict[str, type[BaseModel]]:
    """Descubre dinámicamente todos los BaseModel públicos de src.schemas y LoginData."""
    encontrados: dict[str, type[BaseModel]] = {
        nombre: cls
        for nombre, cls in inspect.getmembers(schemas_module, inspect.isclass)
        if issubclass(cls, BaseModel)
        and cls is not BaseModel
        and cls.__module__ == schemas_module.__name__
        and not nombre.startswith("_")
    }
    encontrados["LoginData"] = LoginData
    return encontrados


_USUARIO_BASE_VALIDO: dict[str, Any] = {
    "nombre": "Ana Morales",
    "cedula": "V-20000000",
    "correo": "ana@example.com",
    "telefono": "+584140000000",
}

_CONSULTA_RESUMEN_VALIDA: dict[str, Any] = {
    "id": 1,
    "titulo": "Impermeabilización Techo",
    "descripcion_legal": "Consulta escrita Art. 23 LPH para techo.",
    "tipo_consulta": "CARTA_CONSULTA_1RA",
    "regla_quorum": "DOS_TERCIOS",
    "quorum_minimo_alicuota": "66.6667",
    "participacion_alicuota": "60.0000",
    "alicuota_aprobatoria": "60.0000",
    "total_votos": 1,
    "fecha_apertura": "2026-10-10T00:00:00Z",
    "fecha_cierre": "2026-10-20T00:00:00Z",
    "estado": "ABIERTA",
    "creada_por_id": 1,
}

CASOS_ESQUEMAS: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {
    "UsuarioBase": (
        dict(_USUARIO_BASE_VALIDO),
        {**_USUARIO_BASE_VALIDO, "correo": "correo-invalido"},
    ),
    "UsuarioCreate": (
        {
            **_USUARIO_BASE_VALIDO,
            "password": "SecurePassword123!",
            "unidad_solicitada_id": 1,
            "tipo_ocupante_solicitado": "PROPIETARIO",
        },
        {
            **_USUARIO_BASE_VALIDO,
            "password": "123",
            "unidad_solicitada_id": 1,
            "tipo_ocupante_solicitado": "PROPIETARIO",
        },
    ),
    "UsuarioResponse": (
        {**_USUARIO_BASE_VALIDO, "id": 10, "es_activo": True, "rol": "PROPIETARIO"},
        {},
    ),
    "TasaCambioCreate": ({"tasa_usd_ves": "45.5000"}, {"tasa_usd_ves": "0"}),
    "TasaCambioResponse": ({"fecha": "2026-10-12", "tasa_usd_ves": "45.5000"}, {}),
    "ReciboCreate": (
        {"unidad_id": 1, "periodo": "2026-10", "monto_usd": "100.00"},
        {"unidad_id": 1, "periodo": "2026-13", "monto_usd": "100.00"},
    ),
    "ReciboResponse": (
        {
            "id": 1,
            "unidad_id": 1,
            "periodo": "2026-10",
            "monto_usd": "100.00",
            "monto_pagado_usd": "0.00",
            "estado": "PENDIENTE",
            "bloqueado": False,
        },
        {},
    ),
    "PagoReportar": (
        {
            "recibo_id": 1,
            "monto": "50.00",
            "moneda": "USD",
            "metodo_pago": "ZELLE",
            "url_comprobante": "https://cdn.example.com/c.avif",
        },
        {"recibo_id": 1, "monto": "50.00", "moneda": "EUR", "metodo_pago": "ZELLE"},
    ),
    "PagoResponse": (
        {
            "id": 1,
            "recibo_id": 1,
            "usuario_id": 2,
            "monto": "50.00",
            "moneda": "USD",
            "monto_usd": "50.00",
            "tasa_cambio": "45.5000",
            "metodo_pago": "EFECTIVO",
            "numero_referencia": None,
            "estado": "EN_REVISION",
        },
        {},
    ),
    "PagoRechazo": ({"motivo": "Referencia duplicada"}, {"motivo": ""}),
    "EgresoCreate": (
        {
            "periodo": "2026-10",
            "categoria": "LIMPIEZA",
            "descripcion": "Cloro",
            "monto": "25.00",
            "moneda": "USD",
        },
        {
            "periodo": "2026-10",
            "categoria": "",
            "descripcion": "Cloro",
            "monto": "25.00",
            "moneda": "USD",
        },
    ),
    "CierreMensualRequest": ({"periodo": "2026-10"}, {"periodo": "2026-00"}),
    "EstructuraGenerarRequest": (
        {"nombre": "Torre A", "tipo": "TORRE", "identificadores": ["1-A", "1-B"]},
        {"nombre": "Torre A", "tipo": "TORRE", "identificadores": []},
    ),
    "UnidadPublicaResponse": ({"id": 1, "identificador": "1-A", "estructura_id": 1}, {}),
    "UnidadResponse": ({"id": 1, "identificador": "1-A", "estructura_id": 1}, {}),
    "AlicuotaUpdateRequest": (
        {"alicuota": "25.5000", "cuota_fija_usd": None},
        {"alicuota": "100.0001"},
    ),
    "EstructuraGenerarResponse": (
        {
            "estructura_id": 1,
            "nombre": "Torre A",
            "tipo": "TORRE",
            "unidades_creadas": 1,
            "unidades": [{"id": 1, "identificador": "1-A", "estructura_id": 1}],
        },
        {},
    ),
    "UsuarioAsignarRequest": (
        {"unidad_id": 1, "tipo_ocupante": "PROPIETARIO", "rol": "PROPIETARIO"},
        {"unidad_id": 1, "tipo_ocupante": "PROPIETARIO", "rol": "ROL_INVALIDO"},
    ),
    "JuntaCargoRequest": (
        {"usuario_id": 1, "cargo": "TESORERO"},
        {"usuario_id": 1, "cargo": "CONSERJE"},
    ),
    "IncidenciaCreate": (
        {"area": "Lobby", "descripcion": "Bombillo quemado"},
        {"area": "", "descripcion": "Bombillo quemado"},
    ),
    "IncidenciaResponse": (
        {
            "id": 1,
            "usuario_creador_id": 2,
            "area": "Lobby",
            "descripcion": "Falla",
            "url_foto": None,
            "estado": "ABIERTO",
            "adhesiones_count": 1,
        },
        {},
    ),
    "PlantillaTareaCreate": (
        {"titulo": "Barrer", "area": "Pasillo", "frecuencia": "DIARIA"},
        {"titulo": "Barrer", "area": "Pasillo", "frecuencia": "ANUAL"},
    ),
    "PlantillaTareaResponse": (
        {"id": 1, "titulo": "Barrer", "area": "Pasillo", "frecuencia": "DIARIA", "activa": True},
        {},
    ),
    "TareaDiariaCreate": (
        {"titulo": "Revisar bomba", "area": "Sótano"},
        {"titulo": "", "area": "Sótano"},
    ),
    "TareaCompletarRequest": (
        {"url_evidencia": "/media/tareas/1.avif"},
        {"url_evidencia": "javascript:alert(1)"},
    ),
    "TareaDiariaResponse": (
        {
            "id": 1,
            "plantilla_id": None,
            "incidencia_id": None,
            "titulo": "Limpiar",
            "area": "Lobby",
            "fecha": "2026-10-12",
            "completada": False,
            "url_evidencia": None,
        },
        {},
    ),
    "FotoVoceroCreate": (
        {
            "periodo": "2026-10",
            "area": "Jardín",
            "comentario": "Poda completa",
            "url_foto": "https://cdn.example.com/j.avif",
        },
        {
            "periodo": "2026-10",
            "area": "Jardín",
            "comentario": "Poda",
            "url_foto": "file:///etc/passwd",
        },
    ),
    "FotoVoceroResponse": (
        {
            "id": 1,
            "usuario_id": 4,
            "periodo": "2026-10",
            "area": "Jardín",
            "comentario": "Poda",
            "url_foto": "/media/1.avif",
        },
        {},
    ),
    "GaleriaVoceroResponse": (
        {"periodo": "2026-10", "fotos_usadas_mes": 0, "limite_mensual": 30, "fotos": []},
        {},
    ),
    "BitacoraActaCreate": (
        {"fecha": "2026-10-12", "hora": "19:00", "ubicacion": "Salón", "contenido": "Acuerdos"},
        {"fecha": "fecha-invalida", "hora": "19:00", "ubicacion": "Salón", "contenido": "Acta"},
    ),
    "BitacoraActaResponse": (
        {
            "id": 1,
            "fecha": "2026-10-12",
            "hora": "19:00",
            "ubicacion": "Salón",
            "contenido": "Acta",
            "autor_id": 3,
        },
        {},
    ),
    "ComunicadoCreate": (
        {
            "titulo": "Aviso",
            "contenido": "Fumigación programada",
            "enlace_externo": "https://example.com/aviso",
        },
        {
            "titulo": "Aviso",
            "contenido": "Fumigación",
            "enlace_externo": "javascript:alert(1)",
        },
    ),
    "ComunicadoResponse": (
        {"id": 1, "titulo": "Aviso", "contenido": "Texto", "enlace_externo": None, "activo": True},
        {},
    ),
    "FondoCondominioCreate": (
        {"nombre": "Fondo Reserva", "tipo": "RESERVA_LEGAL", "porcentaje_recargo": "10.00"},
        {"nombre": "AB", "porcentaje_recargo": "10.00"},
    ),
    "FondoCondominioResponse": (
        {
            "id": 1,
            "nombre": "Fondo Reserva",
            "tipo": "RESERVA_LEGAL",
            "porcentaje_recargo": "10.00",
            "saldo_actual_usd": "500.00",
            "es_activo": True,
        },
        {},
    ),
    "FacturarPeriodoRequest": (
        {"periodo": "2026-10", "modalidad": "ALICUOTA"},
        {"periodo": "2026-10", "modalidad": "ARBITRARIA"},
    ),
    "ReciboItemResponse": (
        {"id": 1, "recibo_id": 1, "tipo_item": "GASTO_COMUN", "descripcion": "Cuota", "monto_usd": "50.00"},
        {},
    ),
    "ReciboDesgloseResponse": (
        {
            "recibo_id": 1,
            "unidad_id": 1,
            "identificador_unidad": "1-A",
            "alicuota_aplicada": "60.0000",
            "periodo": "2026-10",
            "monto_usd": "100.00",
            "monto_pagado_usd": "0.00",
            "saldo_pendiente_usd": "100.00",
            "credito_descontado_usd": "0.00",
            "estado": "PENDIENTE",
            "bloqueado": False,
            "items": [],
        },
        {},
    ),
    "FacturarPeriodoResponse": (
        {
            "periodo": "2026-10",
            "modalidad": "ALICUOTA",
            "recibos_emitidos": 2,
            "total_egresos_comunes_usd": "100.00",
            "recargo_fondo_reserva_usd": "10.00",
            "cuota_extraordinaria_total_usd": "0.00",
            "total_facturado_bruto_usd": "110.00",
            "total_credito_descontado_usd": "0.00",
            "total_facturado_neto_usd": "110.00",
            "superavit_conciliado_fondo_usd": "0.00",
        },
        {},
    ),
    "CertificadoSolvenciaResponse": (
        {
            "id": 1,
            "jti": "jti-1",
            "folio": "SOLV-001",
            "unidad_id": 1,
            "identificador_unidad": "1-A",
            "emitido_por_id": 2,
            "fecha_emision": "2026-10-12T10:00:00Z",
            "fecha_vencimiento": "2026-11-12",
            "deuda_verificada_usd": "0.00",
            "firma_hmac": "abc",
            "qr_token": "tok",
        },
        {},
    ),
    "VerificarSolvenciaResponse": (
        {
            "valido": True,
            "folio": "SOLV-001",
            "unidad_id": 1,
            "identificador_unidad": "1-A",
            "fecha_vencimiento": "2026-11-12",
            "vigente": True,
            "deuda_verificada_usd": "0.00",
            "firma_hmac": "abc",
        },
        {},
    ),
    "OpcionConsultaCreate": (
        {"etiqueta": "Sí, aprobar", "es_opcion_aprobatoria": True},
        {"etiqueta": "X"},
    ),
    "ConsultaCreate": (
        {
            "titulo": "Impermeabilización Techo",
            "descripcion_legal": "Consulta escrita Art. 23 LPH para techo.",
            "fecha_cierre": "2026-11-01T23:59:00Z",
            "opciones": [
                {"etiqueta": "Sí", "es_opcion_aprobatoria": True},
                {"etiqueta": "No", "es_opcion_aprobatoria": False},
            ],
        },
        {
            "titulo": "Ab",
            "descripcion_legal": "Corto",
            "fecha_cierre": "2026-11-01T23:59:00Z",
            "opciones": [{"etiqueta": "Sí"}],
        },
    ),
    "OpcionConsultaResultadoResponse": (
        {"id": 1, "etiqueta": "Sí", "es_opcion_aprobatoria": True},
        {},
    ),
    "VotoReciboResumenResponse": (
        {
            "voto_id": 1,
            "unidad_id": 1,
            "identificador_unidad": "1-A",
            "opcion_id": 1,
            "opcion_etiqueta": "Sí",
            "alicuota_capturada": "60.0000",
            "fecha_voto": "2026-10-12T10:00:00Z",
            "firma_hmac": "abc",
        },
        {},
    ),
    "ConsultaResumenResponse": (dict(_CONSULTA_RESUMEN_VALIDA), {}),
    "ConsultaDetalleResponse": ({**_CONSULTA_RESUMEN_VALIDA, "opciones": []}, {}),
    "VotarConsultaRequest": ({"unidad_id": 1, "opcion_id": 2}, {"unidad_id": 0, "opcion_id": 2}),
    "ReciboVotoResponse": (
        {
            "voto_id": 1,
            "consulta_id": 1,
            "titulo_consulta": "T",
            "unidad_id": 1,
            "identificador_unidad": "1-A",
            "usuario_id": 2,
            "opcion_id": 1,
            "opcion_etiqueta": "Sí",
            "alicuota_capturada": "60.0000",
            "participacion_total_alicuota": "60.0000",
            "quorum_minimo_alicuota": "66.6667",
            "fecha_voto": "2026-10-12T10:00:00Z",
            "ip_hash": "h1",
            "firma_hmac": "h2",
            "mensaje_verificacion": "OK",
        },
        {},
    ),
    "CerrarConsultaResponse": (
        {
            "consulta_id": 1,
            "titulo": "T",
            "estado": "CERRADA_APROBADA",
            "regla_quorum": "DOS_TERCIOS",
            "quorum_minimo_alicuota": "66.6667",
            "participacion_alicuota": "100.0000",
            "alicuota_aprobatoria": "100.0000",
            "total_votos": 2,
            "acta_bitacora_id": 1,
            "hash_global_escrutinio": "h3",
        },
        {},
    ),
    "PaseVisitaCreate": (
        {"unidad_id": 1, "nombre_visitante": "Juan Visita", "cedula_visitante": "V-1234567"},
        {"unidad_id": 1, "nombre_visitante": "Jo", "cedula_visitante": "V-1"},
    ),
    "PaseVisitaResponse": (
        {
            "id": 1,
            "jti": "j1",
            "unidad_id": 1,
            "identificador_unidad": "1-A",
            "creado_por_id": 2,
            "nombre_visitante": "Juan",
            "cedula_visitante": "V-12345",
            "modalidad": "UNICO_USO",
            "valido_desde": "2026-10-12T08:00:00Z",
            "valido_hasta": "2026-10-13T08:00:00Z",
            "estado": "ACTIVO",
            "firma_hmac": "sig",
            "qr_token": "qr",
        },
        {},
    ),
    "VerificarPaseQRRequest": ({"qr_token": "qr_token_valido_123456"}, {"qr_token": "corto"}),
    "VerificarPaseQRResponse": (
        {
            "autorizado": True,
            "pase_id": 1,
            "jti": "j1",
            "unidad_id": 1,
            "identificador_unidad": "1-A",
            "nombre_visitante": "Juan",
            "cedula_visitante": "V-12345",
            "modalidad": "UNICO_USO",
            "estado": "USADO",
            "usado_en": "2026-10-12T10:00:00Z",
            "verificado_por_id": 5,
            "mensaje": "Acceso autorizado",
        },
        {},
    ),
    "PaqueteCreate": (
        {"unidad_id": 1, "empresa_envio": "MRW", "descripcion": "Sobre sellado"},
        {"unidad_id": 1, "empresa_envio": "X", "descripcion": "Ok"},
    ),
    "PaqueteResponse": (
        {
            "id": 1,
            "unidad_id": 1,
            "identificador_unidad": "1-A",
            "recibido_por_id": 5,
            "empresa_envio": "MRW",
            "descripcion": "Sobre",
            "estado": "EN_GARITA",
            "fecha_recepcion": "2026-10-12T10:00:00Z",
        },
        {},
    ),
    "AreaSocialCreate": (
        {
            "nombre": "Parrillera",
            "aforo_maximo": 30,
            "costo_uso_usd": "20.00",
            "deposito_garantia_usd": "50.00",
            "requiere_solvencia_estricta": True,
        },
        {"nombre": "Parrillera", "aforo_maximo": 501},
    ),
    "AreaSocialResponse": (
        {
            "id": 1,
            "nombre": "Parrillera",
            "aforo_maximo": 30,
            "costo_uso_usd": "20.00",
            "deposito_garantia_usd": "50.00",
            "requiere_solvencia_estricta": True,
            "es_activa": True,
        },
        {},
    ),
    "ReservaAreaCreate": (
        {
            "area_id": 1,
            "unidad_id": 1,
            "fecha_evento": "2026-10-25",
            "motivo_evento": "Cumpleaños infantil",
        },
        {
            "area_id": 1,
            "unidad_id": 1,
            "fecha_evento": "2026-10-25",
            "motivo_evento": "ABC",
        },
    ),
    "ReservaInspeccionarRequest": (
        {"estado": "FINALIZADA_SIN_DANOS", "observaciones_inspeccion": "Área entregada limpia."},
        {"estado": "INVALIDO", "observaciones_inspeccion": "OK"},
    ),
    "ReservaAreaResponse": (
        {
            "id": 1,
            "area_id": 1,
            "nombre_area": "Parrillera",
            "unidad_id": 1,
            "identificador_unidad": "1-A",
            "solicitante_id": 2,
            "fecha_evento": "2026-10-25",
            "motivo_evento": "Reunión",
            "estado": "CONFIRMADA",
            "creado_en": "2026-10-12T10:00:00Z",
        },
        {},
    ),
    "HealthResponse": ({"status": "ok"}, {}),
    "AuthSessionResponse": ({"message": "Login exitoso", "rol": "PROPIETARIO", "csrf_token": "tok"}, {}),
    "LogoutResponse": ({"message": "Sesión cerrada"}, {}),
    "AuthMeResponse": (
        {
            "id": 1,
            "nombre": "Ana",
            "cedula": "V-1",
            "correo": "ana@example.com",
            "telefono": "0414",
            "es_activo": True,
            "rol": "PROPIETARIO",
        },
        {},
    ),
    "EgresoCreatedResponse": ({"id": 1, "monto_usd": "100.00"}, {}),
    "EstadoCobranzaItemResponse": (
        {
            "recibo_id": 1,
            "unidad_id": 1,
            "periodo": "2026-10",
            "monto_usd": "100.00",
            "estado": "PENDIENTE",
            "saldo_usd": "100.00",
        },
        {},
    ),
    "ResumenFinancieroResponse": (
        {
            "deuda_total_usd": "100.00",
            "total_egresos_usd": "50.00",
            "gastos_por_categoria": {"LIMPIEZA": "50.00"},
            "estado_cobranza": [],
        },
        {},
    ),
    "CierreMensualResponse": ({"periodo": "2026-10", "estado": "CERRADO"}, {}),
    "GenerarTareasDiariasResponse": ({"tareas_generadas": 3}, {}),
    "EvidenciaUploadResponse": (
        {
            "url": "/media/1.avif",
            "mime_origen": "image/png",
            "formato_destino": "image/avif",
            "bytes_recibidos": 1024,
            "estado": "PROCESADA",
        },
        {},
    ),
    "LoginData": (
        {"correo": "ana@example.com", "password": "Password123!"},
        {"correo": "ana@example.com", "password": "123"},
    ),
}


def test_todos_los_esquemas_descubiertos_tienen_contrato() -> None:
    """Verifica por introspección que los >= 71 esquemas públicos tienen cobertura declarada."""
    descubiertos = _descubrir_esquemas_publicos()
    assert len(descubiertos) >= 71
    assert set(descubiertos.keys()) == set(CASOS_ESQUEMAS.keys())


@pytest.mark.parametrize("nombre_esquema", sorted(CASOS_ESQUEMAS.keys()))
def test_esquema_construccion_y_validacion_invalida(nombre_esquema: str) -> None:
    """Valida construcción válida y rechazo ValidationError para cada esquema Pydantic."""
    descubiertos = _descubrir_esquemas_publicos()
    cls = descubiertos[nombre_esquema]
    payload_valido, payload_invalido = CASOS_ESQUEMAS[nombre_esquema]

    instancia = cls.model_validate(payload_valido)
    assert isinstance(instancia, cls)

    with pytest.raises(ValidationError):
        cls.model_validate(payload_invalido)


def test_validadores_personalizados_enteros_urls_y_normalizacion() -> None:
    """Cubre validadores de EnteroEstricto, enlace externo, normalización ORM y zona horaria."""
    recibo = ReciboCreate.model_validate({"unidad_id": 5.0, "periodo": "2026-10", "monto_usd": "10.00"})
    assert recibo.unidad_id == 5

    for valor_invalido in (5.5, True, "5"):
        with pytest.raises(ValidationError):
            ReciboCreate.model_validate({"unidad_id": valor_invalido, "periodo": "2026-10", "monto_usd": "10.00"})

    comunicado_vacio = ComunicadoCreate.model_validate(
        {"titulo": "Aviso", "contenido": "Contenido", "enlace_externo": "   "}
    )
    assert comunicado_vacio.enlace_externo is None

    for enlace_malo in ("javascript:alert(1)", "//evil.com/x", "/relativo", "https://a.com\n"):
        with pytest.raises(ValidationError):
            ComunicadoCreate.model_validate(
                {"titulo": "Aviso", "contenido": "Contenido", "enlace_externo": enlace_malo}
            )

    unidad_orm = UnidadResponse.model_validate(
        SimpleNamespace(
            id=1,
            identificador="1-A",
            estructura_id=1,
            alicuota=None,
            cuota_fija_usd=None,
            credito_disponible_usd=None,
        )
    )
    assert unidad_orm.alicuota == Decimal("0.0000")
    assert unidad_orm.credito_disponible_usd == Decimal("0.00")

    pase = PaseVisitaCreate.model_validate(
        {
            "unidad_id": 1,
            "nombre_visitante": "Visitante Prueba",
            "cedula_visitante": "V-1234567",
            "valido_desde": datetime(2026, 10, 12, 8, 0),
        }
    )
    assert pase.valido_desde is not None
    assert pase.valido_desde.tzinfo == UTC
