"""Contratos Pydantic de entrada, salida y validación de dominio para la API."""

import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from datetime import date as date_type
from decimal import Decimal
from typing import Annotated, Any, Literal

import email_validator
from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator

_CTRL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
_ESQUEMAS_URL_PROHIBIDOS: tuple[str, ...] = ("javascript:", "data:", "vbscript:", "file:")
_PREFIJOS_URL_RELATIVA_PROHIBIDOS: tuple[str, ...] = ("//", "/\\")


@dataclass(frozen=True)
class _ReglasUrlSegura:
    """Política parametrizada de esquemas permitidos y mensajes de rechazo Anti-XSS/LFI."""

    prefijos_permitidos: tuple[str, ...]
    msg_control: str
    msg_protocolo_relativo: str
    msg_esquema_peligroso: str
    msg_prefijo_invalido: str


_REGLAS_URL_EVIDENCIA = _ReglasUrlSegura(
    prefijos_permitidos=("https://", "http://", "s3://", "/"),
    msg_control="La URL contiene caracteres de control no permitidos.",
    msg_protocolo_relativo="URL relativa al protocolo ('//') no permitida por seguridad.",
    msg_esquema_peligroso="Esquema de URL no permitido por seguridad (Anti-XSS/LFI).",
    msg_prefijo_invalido="La URL de evidencia debe iniciar con https://, http://, s3:// o ruta relativa '/'.",
)
_REGLAS_ENLACE_EXTERNO = _ReglasUrlSegura(
    prefijos_permitidos=("https://", "http://"),
    msg_control="El enlace externo contiene caracteres de control no permitidos.",
    msg_protocolo_relativo="Enlace externo peligroso rechazado por seguridad (Anti-XSS).",
    msg_esquema_peligroso="Enlace externo peligroso rechazado por seguridad (Anti-XSS).",
    msg_prefijo_invalido="El enlace externo debe iniciar con https:// o http://.",
)


def _coercer_entero_json_exacto(valor: Any) -> Any:
    """Acepta floats exactos sin fracción (p. ej. 57.0 en OpenAPI 3.1) preservando rechazo de bool/str/fracciones."""
    if isinstance(valor, float) and math.isfinite(valor) and valor.is_integer():
        return int(valor)
    return valor


def _validar_correo(valor: str) -> str:
    """Valida el correo con las mismas reglas que el contrato (format: email), permitiendo
    dominios de prueba reservados (RFC 2606) que schemathesis envía en el fuzzing."""
    try:
        email_validator.validate_email(valor, check_deliverability=False, test_environment=True)
    except email_validator.EmailNotValidError as exc:
        raise ValueError(f"correo electrónico inválido: {exc}") from exc
    return valor


def _validar_url_con_reglas(limpio: str, reglas: _ReglasUrlSegura) -> str:
    """Aplica validaciones Anti-XSS/LFI y de esquema permitido sobre una URL recortada."""
    if limpio.startswith(_PREFIJOS_URL_RELATIVA_PROHIBIDOS):
        raise ValueError(reglas.msg_protocolo_relativo)
    minus = limpio.lower()
    if minus.startswith(_ESQUEMAS_URL_PROHIBIDOS):
        raise ValueError(reglas.msg_esquema_peligroso)
    if not minus.startswith(reglas.prefijos_permitidos):
        raise ValueError(reglas.msg_prefijo_invalido)
    return limpio


def _validar_url_opcional(valor: str | None, reglas: _ReglasUrlSegura) -> str | None:
    """Normaliza una URL opcional retornando None si es vacía o validándola contra la política."""
    if valor is None:
        return None
    if _CTRL_CHAR_RE.search(valor) is not None:
        raise ValueError(reglas.msg_control)
    limpio = valor.strip()
    if not limpio:
        return None
    return _validar_url_con_reglas(limpio, reglas)


def _validar_url_evidencia_segura(valor: str) -> str:
    """Bloquea esquemas peligrosos (XSS/LFI), protocol-relative '//' y caracteres de control en URLs."""
    if _CTRL_CHAR_RE.search(valor) is not None:
        raise ValueError(_REGLAS_URL_EVIDENCIA.msg_control)
    limpio = valor.strip()
    if not limpio:
        raise ValueError("La URL de evidencia no puede estar vacía.")
    return _validar_url_con_reglas(limpio, _REGLAS_URL_EVIDENCIA)


CorreoValido = Annotated[str, Field(json_schema_extra={"format": "email"}), AfterValidator(_validar_correo)]
UrlEvidenciaSegura = Annotated[str, Field(min_length=1), AfterValidator(_validar_url_evidencia_segura)]
EnteroEstricto = Annotated[int, BeforeValidator(_coercer_entero_json_exacto), Field(strict=True)]
_PeriodoFiscal = Annotated[str, Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]
_TextoNoVacio = Annotated[str, Field(min_length=1)]
_MontoUsdPositivo = Annotated[Decimal, Field(gt=0, allow_inf_nan=False, le=Decimal("9999999999.99"))]
_IdPositivo = Annotated[EnteroEstricto, Field(gt=0)]
_MontoAreaSocial = Annotated[Decimal, Field(ge=Decimal("0.00"), le=Decimal("99999999.99"), allow_inf_nan=False)]


class _SchemaEstricto(BaseModel):
    """Base Pydantic de entrada que rechaza propiedades adicionales no declaradas."""

    model_config = ConfigDict(extra="forbid")


class _SchemaORM(BaseModel):
    """Base Pydantic de salida habilitada para hidratación directa desde modelos ORM."""

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# ESQUEMAS DE IDENTIDAD, USUARIOS Y AUTENTICACIÓN
# ==============================================================================


class UsuarioBase(_SchemaEstricto):
    nombre: str = Field(min_length=1, max_length=120)
    cedula: str = Field(min_length=1, max_length=30)
    correo: CorreoValido
    telefono: str = Field(min_length=1, max_length=30)


class UsuarioCreate(UsuarioBase):
    password: str = Field(min_length=8, max_length=128)
    unidad_solicitada_id: EnteroEstricto = Field(ge=1, le=2_000_000_000)
    tipo_ocupante_solicitado: str = Field(min_length=1, max_length=30)


class UsuarioResponse(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    es_activo: bool
    rol: str


# ==============================================================================
# ESQUEMAS DE FINANZAS, RECIBOS, PAGOS Y EGRESOS
# ==============================================================================

Moneda = Literal["USD", "VES"]


class TasaCambioCreate(_SchemaEstricto):
    fecha: date_type | None = None
    tasa_usd_ves: Decimal = Field(gt=0, allow_inf_nan=False, le=Decimal("9999999999.9999"))


class TasaCambioResponse(_SchemaORM):
    fecha: date_type
    tasa_usd_ves: Decimal


class ReciboCreate(_SchemaEstricto):
    unidad_id: EnteroEstricto
    periodo: _PeriodoFiscal
    monto_usd: _MontoUsdPositivo


class ReciboResponse(_SchemaORM):
    id: int
    unidad_id: int
    periodo: str
    monto_usd: Decimal
    monto_pagado_usd: Decimal
    estado: str
    bloqueado: bool


class PagoReportar(_SchemaEstricto):
    recibo_id: EnteroEstricto
    monto: _MontoUsdPositivo
    moneda: Moneda
    metodo_pago: str
    numero_referencia: str | None = None
    url_comprobante: UrlEvidenciaSegura | None = None


class PagoResponse(_SchemaORM):
    id: int
    recibo_id: int
    usuario_id: int
    monto: Decimal
    moneda: str
    monto_usd: Decimal
    tasa_cambio: Decimal
    metodo_pago: str
    numero_referencia: str | None
    url_comprobante: str | None = None
    estado: str


class PagoRechazo(_SchemaEstricto):
    motivo: _TextoNoVacio


class EgresoCreate(_SchemaEstricto):
    periodo: _PeriodoFiscal
    categoria: _TextoNoVacio
    descripcion: _TextoNoVacio
    monto: _MontoUsdPositivo
    moneda: Moneda
    url_factura: UrlEvidenciaSegura | None = None
    incidencia_id: EnteroEstricto | None = None
    es_gasto_comun: bool = True


class CierreMensualRequest(_SchemaEstricto):
    periodo: _PeriodoFiscal


# ==============================================================================
# ESQUEMAS DE ADMINISTRACIÓN, ESTRUCTURAS Y ALÍCUOTAS
# ==============================================================================

TipoEstructura = Literal["EDIFICIO", "TORRE", "BLOQUE", "MANZANA", "CALLE"]
TipoOcupante = Literal["PROPIETARIO", "INQUILINO"]
RolResidente = Literal[
    "PROPIETARIO",
    "INQUILINO",
    "CONSERJE",
    "VOCERO",
    "TESORERO",
    "SECRETARIO",
    "VICEPRESIDENTE",
    "PRESIDENTE",
]
CargoJunta = Literal["PRESIDENTE", "VICEPRESIDENTE", "TESORERO", "SECRETARIO", "VOCERO"]
FrecuenciaTarea = Literal["UNICA", "DIARIA", "SEMANAL", "MENSUAL"]


class EstructuraGenerarRequest(_SchemaEstricto):
    nombre: _TextoNoVacio
    tipo: TipoEstructura
    identificadores: list[str] = Field(min_length=1)


class UnidadPublicaResponse(_SchemaORM):
    """DTO público mínimo para registro de vecinos sin exponer saldos ni alícuotas."""

    id: int
    identificador: str
    estructura_id: int


def _normalizar_unidad_objeto(data: Any) -> dict[str, Any]:
    """Serializa un objeto Unidad en memoria rellenando decimales nulos con valores seguros."""
    alicuota_raw = getattr(data, "alicuota", None)
    credito_raw = getattr(data, "credito_disponible_usd", None)
    return {
        "id": getattr(data, "id", 0),
        "identificador": getattr(data, "identificador", ""),
        "estructura_id": getattr(data, "estructura_id", 1),
        "alicuota": Decimal("0.0000") if alicuota_raw is None else alicuota_raw,
        "cuota_fija_usd": getattr(data, "cuota_fija_usd", None),
        "credito_disponible_usd": Decimal("0.00") if credito_raw is None else credito_raw,
    }


class UnidadResponse(_SchemaORM):
    id: int
    identificador: str
    estructura_id: int
    alicuota: Decimal = Decimal("0.0000")
    cuota_fija_usd: Decimal | None = None
    credito_disponible_usd: Decimal = Decimal("0.00")

    @model_validator(mode="before")
    @classmethod
    def _normalizar_nulos_en_memoria(cls, data: Any) -> Any:
        if hasattr(data, "identificador") and not isinstance(data, dict):
            return _normalizar_unidad_objeto(data)
        return data


class AlicuotaUpdateRequest(_SchemaEstricto):
    alicuota: Decimal = Field(..., ge=Decimal("0.0000"), le=Decimal("100.0000"), allow_inf_nan=False)
    cuota_fija_usd: Decimal | None = Field(
        default=None,
        ge=Decimal("0.00"),
        le=Decimal("9999999999.99"),
        allow_inf_nan=False,
    )


class EstructuraGenerarResponse(BaseModel):
    estructura_id: int
    nombre: str
    tipo: str
    unidades_creadas: int
    unidades: list[UnidadResponse]


class UsuarioAsignarRequest(_SchemaEstricto):
    unidad_id: EnteroEstricto
    tipo_ocupante: TipoOcupante
    rol: RolResidente = "PROPIETARIO"
    puede_votar_asamblea: bool | None = None


class JuntaCargoRequest(_SchemaEstricto):
    usuario_id: EnteroEstricto
    cargo: CargoJunta


# ==============================================================================
# ESQUEMAS DE OPERACIONES, INCIDENCIAS, BITÁCORA Y COMUNICADOS
# ==============================================================================


class IncidenciaCreate(_SchemaEstricto):
    area: _TextoNoVacio
    descripcion: _TextoNoVacio
    url_foto: UrlEvidenciaSegura | None = None


class IncidenciaResponse(_SchemaORM):
    id: int
    usuario_creador_id: int
    area: str
    descripcion: str
    url_foto: str | None
    estado: str
    adhesiones_count: int


class PlantillaTareaCreate(_SchemaEstricto):
    titulo: _TextoNoVacio
    area: _TextoNoVacio
    frecuencia: FrecuenciaTarea = "DIARIA"


class PlantillaTareaResponse(_SchemaORM):
    id: int
    titulo: str
    area: str
    frecuencia: str
    activa: bool


class TareaDiariaCreate(_SchemaEstricto):
    titulo: _TextoNoVacio
    area: _TextoNoVacio
    fecha: date_type | None = None
    incidencia_id: EnteroEstricto | None = None


class TareaCompletarRequest(_SchemaEstricto):
    url_evidencia: UrlEvidenciaSegura | None = None


class TareaDiariaResponse(_SchemaORM):
    id: int
    plantilla_id: int | None
    incidencia_id: int | None
    titulo: str
    area: str
    fecha: date_type
    completada: bool
    url_evidencia: str | None


class FotoVoceroCreate(_SchemaEstricto):
    periodo: _PeriodoFiscal
    area: _TextoNoVacio
    comentario: _TextoNoVacio
    url_foto: UrlEvidenciaSegura


class FotoVoceroResponse(_SchemaORM):
    id: int
    usuario_id: int
    periodo: str
    area: str
    comentario: str
    url_foto: str


class GaleriaVoceroResponse(BaseModel):
    periodo: str
    fotos_usadas_mes: int
    limite_mensual: int
    fotos: list[FotoVoceroResponse]


class BitacoraActaCreate(_SchemaEstricto):
    fecha: date_type
    hora: _TextoNoVacio
    ubicacion: _TextoNoVacio
    contenido: _TextoNoVacio


class BitacoraActaResponse(_SchemaORM):
    id: int
    fecha: date_type
    hora: str
    ubicacion: str
    contenido: str
    autor_id: int


class ComunicadoCreate(_SchemaEstricto):
    titulo: _TextoNoVacio
    contenido: _TextoNoVacio
    enlace_externo: str | None = None

    @field_validator("enlace_externo")
    @classmethod
    def _validar_enlace_externo(cls, v: str | None) -> str | None:
        return _validar_url_opcional(v, _REGLAS_ENLACE_EXTERNO)


class ComunicadoResponse(_SchemaORM):
    id: int
    titulo: str
    contenido: str
    enlace_externo: str | None
    activo: bool


# ==============================================================================
# ESQUEMAS DE FACTURACIÓN LPH, FONDOS Y SOLVENCIA (Hito 10)
# ==============================================================================

TipoFondoCondominio = Literal["RESERVA_LEGAL", "CAJA_CHICA", "ESPECIAL"]
ModalidadFacturacion = Literal["ALICUOTA", "CUOTA_FIJA", "PARTES_IGUALES"]
TipoReciboItem = Literal[
    "CUOTA_FIJA",
    "GASTO_COMUN",
    "FONDO_RESERVA",
    "CUOTA_EXTRAORDINARIA",
    "CARGO_INDIVIDUAL",
    "USO_AREA_SOCIAL",
    "DANOS_AREA_SOCIAL",
    "ABONO_CREDITO_PREVIO",
]


class FondoCondominioCreate(_SchemaEstricto):
    nombre: str = Field(..., min_length=3, max_length=100)
    tipo: TipoFondoCondominio = "RESERVA_LEGAL"
    porcentaje_recargo: Decimal = Field(
        default=Decimal("10.00"),
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        allow_inf_nan=False,
    )


class FondoCondominioResponse(_SchemaORM):
    id: int
    nombre: str
    tipo: str
    porcentaje_recargo: Decimal
    saldo_actual_usd: Decimal
    es_activo: bool


class FacturarPeriodoRequest(_SchemaEstricto):
    periodo: _PeriodoFiscal
    modalidad: ModalidadFacturacion = "ALICUOTA"
    monto_cuota_fija_usd: Decimal | None = Field(
        default=None,
        gt=Decimal("0.00"),
        le=Decimal("9999999999.99"),
        allow_inf_nan=False,
    )
    incluir_fondo_reserva: bool = True
    cuota_extraordinaria_total_usd: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        le=Decimal("9999999999.99"),
        allow_inf_nan=False,
    )
    descripcion_cuota_extraordinaria: str | None = Field(default=None, max_length=200)


class ReciboItemResponse(_SchemaORM):
    id: int
    recibo_id: int
    tipo_item: str
    descripcion: str
    monto_usd: Decimal


class ReciboDesgloseResponse(BaseModel):
    recibo_id: int
    unidad_id: int
    identificador_unidad: str
    alicuota_aplicada: Decimal
    periodo: str
    monto_usd: Decimal
    monto_pagado_usd: Decimal
    saldo_pendiente_usd: Decimal
    credito_descontado_usd: Decimal
    estado: str
    bloqueado: bool
    items: list[ReciboItemResponse]


class FacturarPeriodoResponse(BaseModel):
    periodo: str
    modalidad: str
    recibos_emitidos: int
    total_egresos_comunes_usd: Decimal
    recargo_fondo_reserva_usd: Decimal
    cuota_extraordinaria_total_usd: Decimal
    total_facturado_bruto_usd: Decimal
    total_credito_descontado_usd: Decimal
    total_facturado_neto_usd: Decimal
    superavit_conciliado_fondo_usd: Decimal


class CertificadoSolvenciaResponse(_SchemaORM):
    id: int
    jti: str = ""
    folio: str
    unidad_id: int
    identificador_unidad: str
    emitido_por_id: int
    fecha_emision: datetime
    fecha_vencimiento: date_type
    deuda_verificada_usd: Decimal
    firma_hmac: str
    qr_token: str


class VerificarSolvenciaResponse(BaseModel):
    valido: bool
    jti: str = ""
    folio: str
    unidad_id: int
    identificador_unidad: str
    fecha_vencimiento: date_type
    vigente: bool
    deuda_verificada_usd: Decimal
    firma_hmac: str


# ==============================================================================
# ESQUEMAS DE CARTAS CONSULTA Y ASAMBLEAS DIGITALES (Hito 11)
# ==============================================================================

TipoConsulta = Literal[
    "CARTA_CONSULTA_1RA",
    "CARTA_CONSULTA_2DA",
    "ASAMBLEA_ORDINARIA",
    "ASAMBLEA_EXTRAORDINARIA",
]
ReglaQuorum = Literal["DOS_TERCIOS", "MAYORIA_SIMPLE", "UNANIMIDAD"]
EstadoConsulta = Literal[
    "ABIERTA",
    "CERRADA_APROBADA",
    "CERRADA_RECHAZADA",
    "CERRADA_SIN_QUORUM",
]


class OpcionConsultaCreate(_SchemaEstricto):
    etiqueta: str = Field(..., min_length=2, max_length=120)
    es_opcion_aprobatoria: bool = False


class ConsultaCreate(_SchemaEstricto):
    titulo: str = Field(..., min_length=5, max_length=160)
    descripcion_legal: str = Field(..., min_length=10)
    tipo_consulta: TipoConsulta = "CARTA_CONSULTA_1RA"
    regla_quorum: ReglaQuorum = "DOS_TERCIOS"
    fecha_cierre: datetime
    opciones: list[OpcionConsultaCreate] = Field(..., min_length=2, max_length=10)


class OpcionConsultaResultadoResponse(BaseModel):
    id: int
    etiqueta: str
    es_opcion_aprobatoria: bool
    votos_cantidad: int = 0
    alicuota_acumulada: Decimal = Decimal("0.0000")


class VotoReciboResumenResponse(BaseModel):
    voto_id: int
    jti: str = ""
    unidad_id: int
    identificador_unidad: str
    opcion_id: int
    opcion_etiqueta: str
    alicuota_capturada: Decimal
    fecha_voto: datetime
    firma_hmac: str


class ConsultaResumenResponse(BaseModel):
    id: int
    titulo: str
    descripcion_legal: str
    tipo_consulta: str
    regla_quorum: str
    quorum_minimo_alicuota: Decimal
    participacion_alicuota: Decimal
    alicuota_aprobatoria: Decimal
    total_votos: int
    fecha_apertura: datetime
    fecha_cierre: datetime
    estado: str
    creada_por_id: int
    acta_bitacora_id: int | None = None
    ya_voto_usuario: bool = False


class ConsultaDetalleResponse(ConsultaResumenResponse):
    opciones: list[OpcionConsultaResultadoResponse]
    mi_voto: VotoReciboResumenResponse | None = None


class VotarConsultaRequest(_SchemaEstricto):
    unidad_id: _IdPositivo
    opcion_id: _IdPositivo


class ReciboVotoResponse(BaseModel):
    voto_id: int
    jti: str = ""
    consulta_id: int
    titulo_consulta: str
    unidad_id: int
    identificador_unidad: str
    usuario_id: int
    opcion_id: int
    opcion_etiqueta: str
    alicuota_capturada: Decimal
    participacion_total_alicuota: Decimal
    quorum_minimo_alicuota: Decimal
    fecha_voto: datetime
    ip_hash: str
    firma_hmac: str
    mensaje_verificacion: str


class CerrarConsultaResponse(BaseModel):
    consulta_id: int
    titulo: str
    estado: str
    regla_quorum: str
    quorum_minimo_alicuota: Decimal
    participacion_alicuota: Decimal
    alicuota_aprobatoria: Decimal
    total_votos: int
    acta_bitacora_id: int
    hash_global_escrutinio: str


# ==============================================================================
# ESQUEMAS DE ACCESOS QR Y PAQUETERÍA EN GARITA (Hito 12)
# ==============================================================================

ModalidadPaseQR = Literal["UNICO_USO", "VENTANA_TEMPORAL"]
EstadoPaseQR = Literal["ACTIVO", "USADO", "REVOCADO", "EXPIRADO"]
EstadoPaquete = Literal["EN_GARITA", "ENTREGADO"]


class PaseVisitaCreate(_SchemaEstricto):
    unidad_id: _IdPositivo
    nombre_visitante: str = Field(..., min_length=3, max_length=120)
    cedula_visitante: str = Field(..., min_length=5, max_length=25)
    placa_vehiculo: str | None = Field(default=None, max_length=20)
    modalidad: ModalidadPaseQR = "UNICO_USO"
    horas_validez: EnteroEstricto = Field(default=24, ge=1, le=72)
    valido_desde: datetime | None = None
    valido_hasta: datetime | None = None

    @field_validator("valido_desde", "valido_hasta")
    @classmethod
    def normalizar_tz(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return None
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v


class PaseVisitaResponse(BaseModel):
    id: int
    jti: str
    unidad_id: int
    identificador_unidad: str
    creado_por_id: int
    nombre_visitante: str
    cedula_visitante: str
    placa_vehiculo: str | None = None
    modalidad: str
    valido_desde: datetime
    valido_hasta: datetime
    estado: str
    usado_en: datetime | None = None
    verificado_por_id: int | None = None
    firma_hmac: str
    qr_token: str


class VerificarPaseQRRequest(_SchemaEstricto):
    qr_token: str = Field(..., min_length=16, max_length=512)


class VerificarPaseQRResponse(BaseModel):
    autorizado: bool
    pase_id: int
    jti: str
    unidad_id: int
    identificador_unidad: str
    nombre_visitante: str
    cedula_visitante: str
    placa_vehiculo: str | None = None
    modalidad: str
    estado: str
    usado_en: datetime
    verificado_por_id: int
    mensaje: str


class PaqueteCreate(_SchemaEstricto):
    unidad_id: _IdPositivo
    empresa_envio: str = Field(..., min_length=2, max_length=60)
    descripcion: str = Field(..., min_length=3, max_length=200)
    url_foto_evidencia: UrlEvidenciaSegura | None = None


class PaqueteResponse(BaseModel):
    id: int
    unidad_id: int
    identificador_unidad: str
    recibido_por_id: int
    empresa_envio: str
    descripcion: str
    url_foto_evidencia: str | None = None
    estado: str
    fecha_recepcion: datetime
    fecha_entrega: datetime | None = None
    retirado_por_id: int | None = None


# ==============================================================================
# ESQUEMAS DE RESERVA DE ÁREAS SOCIALES E INSPECCIÓN POST-EVENTO (Hito 13)
# ==============================================================================

ResultadoInspeccionReserva = Literal["FINALIZADA_SIN_DANOS", "FINALIZADA_CON_DANOS"]


class AreaSocialCreate(_SchemaEstricto):
    nombre: str = Field(..., min_length=3, max_length=100)
    aforo_maximo: EnteroEstricto = Field(ge=1, le=500)
    costo_uso_usd: _MontoAreaSocial = Decimal("0.00")
    deposito_garantia_usd: _MontoAreaSocial = Decimal("0.00")
    requiere_solvencia_estricta: bool = Field(default=True, strict=True)


class AreaSocialResponse(_SchemaORM):
    id: int
    nombre: str
    aforo_maximo: int
    costo_uso_usd: Decimal
    deposito_garantia_usd: Decimal
    requiere_solvencia_estricta: bool
    es_activa: bool


class ReservaAreaCreate(_SchemaEstricto):
    area_id: _IdPositivo
    unidad_id: _IdPositivo
    fecha_evento: date_type
    motivo_evento: str = Field(..., min_length=5, max_length=160)


class ReservaInspeccionarRequest(_SchemaEstricto):
    estado: ResultadoInspeccionReserva
    observaciones_inspeccion: str = Field(..., min_length=3, max_length=500)


class ReservaAreaResponse(BaseModel):
    id: int
    area_id: int
    nombre_area: str
    unidad_id: int
    identificador_unidad: str
    solicitante_id: int
    fecha_evento: date_type
    motivo_evento: str
    estado: str
    tarea_inspeccion_id: int | None = None
    observaciones_inspeccion: str | None = None
    creado_en: datetime


# ==============================================================================
# CONTRATOS DE RESPUESTA TIPADOS (Hito 21)
# ==============================================================================


class HealthResponse(BaseModel):
    status: str


class AuthSessionResponse(BaseModel):
    message: str
    rol: str
    csrf_token: str


class LogoutResponse(BaseModel):
    message: str


class AuthMeResponse(BaseModel):
    id: int
    nombre: str
    cedula: str
    correo: str
    telefono: str
    es_activo: bool
    rol: str
    unidad_activa_id: int | None = None


class EgresoCreatedResponse(BaseModel):
    id: int
    monto_usd: str


class EstadoCobranzaItemResponse(BaseModel):
    recibo_id: int
    unidad_id: int
    periodo: str
    monto_usd: str
    estado: str
    saldo_usd: str


class ResumenFinancieroResponse(BaseModel):
    deuda_total_usd: str
    total_egresos_usd: str
    gastos_por_categoria: dict[str, str]
    estado_cobranza: list[EstadoCobranzaItemResponse]


class CierreMensualResponse(BaseModel):
    periodo: str
    estado: str


class GenerarTareasDiariasResponse(BaseModel):
    tareas_generadas: int


class EvidenciaUploadResponse(BaseModel):
    url: str
    mime_origen: str
    formato_destino: str
    bytes_recibidos: int
    estado: str
