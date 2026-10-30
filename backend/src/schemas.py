from datetime import UTC, datetime
from datetime import date as date_type
from decimal import Decimal
from typing import Annotated, Any, Literal

import email_validator
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator


def _validar_correo(valor: str) -> str:
    """Valida el correo con las mismas reglas que el contrato (format: email), permitiendo
    dominios de prueba reservados (RFC 2606) que schemathesis envía en el fuzzing."""
    try:
        email_validator.validate_email(valor, check_deliverability=False, test_environment=True)
    except email_validator.EmailNotValidError as exc:
        raise ValueError(f"correo electrónico inválido: {exc}") from exc
    return valor


def _validar_url_evidencia_segura(valor: str) -> str:
    """Bloquea esquemas peligrosos (XSS / LFI: javascript:, data:, vbscript:, file:) en URLs de adjuntos."""
    limpio = valor.strip()
    if not limpio:
        raise ValueError("La URL de evidencia no puede estar vacía.")
    minus = limpio.lower()
    if minus.startswith(("javascript:", "data:", "vbscript:", "file:")):
        raise ValueError("Esquema de URL no permitido por seguridad (Anti-XSS/LFI).")
    if not (minus.startswith(("https://", "http://", "s3://", "/"))):
        raise ValueError("La URL de evidencia debe iniciar con https://, http://, s3:// o ruta relativa '/'.")
    return limpio


CorreoValido = Annotated[str, Field(json_schema_extra={"format": "email"}), AfterValidator(_validar_correo)]
UrlEvidenciaSegura = Annotated[str, Field(min_length=1), AfterValidator(_validar_url_evidencia_segura)]


class UsuarioBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str
    cedula: str
    correo: CorreoValido
    telefono: str


class UsuarioCreate(UsuarioBase):
    password: str
    unidad_solicitada_id: int = Field(strict=True)
    tipo_ocupante_solicitado: str


class UsuarioResponse(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    es_activo: bool
    rol: str


Moneda = Literal["USD", "VES"]


class TasaCambioCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha: date_type | None = None
    tasa_usd_ves: Decimal = Field(gt=0)


class TasaCambioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fecha: date_type
    tasa_usd_ves: Decimal


class ReciboCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unidad_id: int = Field(strict=True)
    periodo: str = Field(pattern=r"^\d{4}-\d{2}$")
    monto_usd: Decimal = Field(gt=0)


class ReciboResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unidad_id: int
    periodo: str
    monto_usd: Decimal
    monto_pagado_usd: Decimal
    estado: str
    bloqueado: bool


class PagoReportar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recibo_id: int = Field(strict=True)
    monto: Decimal = Field(gt=0)
    moneda: Moneda
    metodo_pago: str
    numero_referencia: str | None = None
    url_comprobante: UrlEvidenciaSegura | None = None


class PagoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recibo_id: int
    usuario_id: int
    monto: Decimal
    moneda: str
    monto_usd: Decimal
    tasa_cambio: Decimal
    metodo_pago: str
    numero_referencia: str | None
    estado: str


class PagoRechazo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: str = Field(min_length=1)


class EgresoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    periodo: str = Field(pattern=r"^\d{4}-\d{2}$")
    categoria: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)
    monto: Decimal = Field(gt=0)
    moneda: Moneda
    url_factura: UrlEvidenciaSegura | None = None
    incidencia_id: int | None = Field(default=None, strict=True)
    es_gasto_comun: bool = True


class CierreMensualRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    periodo: str = Field(pattern=r"^\d{4}-\d{2}$")


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


class EstructuraGenerarRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1)
    tipo: TipoEstructura
    identificadores: list[str] = Field(min_length=1)


class UnidadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
        return data


class AlicuotaUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alicuota: Decimal = Field(..., ge=Decimal("0.0000"), le=Decimal("100.0000"))
    cuota_fija_usd: Decimal | None = Field(default=None, ge=Decimal("0.00"))


class EstructuraGenerarResponse(BaseModel):
    estructura_id: int
    nombre: str
    tipo: str
    unidades_creadas: int
    unidades: list[UnidadResponse]


class UsuarioAsignarRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unidad_id: int = Field(strict=True)
    tipo_ocupante: TipoOcupante
    rol: RolResidente = "PROPIETARIO"
    puede_votar_asamblea: bool | None = None


class JuntaCargoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    usuario_id: int = Field(strict=True)
    cargo: CargoJunta


class IncidenciaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    area: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)
    url_foto: UrlEvidenciaSegura | None = None


class IncidenciaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_creador_id: int
    area: str
    descripcion: str
    url_foto: str | None
    estado: str
    adhesiones_count: int


class PlantillaTareaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(min_length=1)
    area: str = Field(min_length=1)
    frecuencia: FrecuenciaTarea = "DIARIA"


class PlantillaTareaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    area: str
    frecuencia: str
    activa: bool


class TareaDiariaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(min_length=1)
    area: str = Field(min_length=1)
    fecha: date_type | None = None
    incidencia_id: int | None = Field(default=None, strict=True)


class TareaCompletarRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url_evidencia: UrlEvidenciaSegura | None = None


class TareaDiariaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plantilla_id: int | None
    incidencia_id: int | None
    titulo: str
    area: str
    fecha: date_type
    completada: bool
    url_evidencia: str | None


class FotoVoceroCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    periodo: str = Field(pattern=r"^\d{4}-\d{2}$")
    area: str = Field(min_length=1)
    comentario: str = Field(min_length=1)
    url_foto: UrlEvidenciaSegura


class FotoVoceroResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class BitacoraActaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha: date_type
    hora: str = Field(min_length=1)
    ubicacion: str = Field(min_length=1)
    contenido: str = Field(min_length=1)


class BitacoraActaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha: date_type
    hora: str
    ubicacion: str
    contenido: str
    autor_id: int


class ComunicadoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(min_length=1)
    contenido: str = Field(min_length=1)
    enlace_externo: str | None = None


class ComunicadoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    contenido: str
    enlace_externo: str | None
    activo: bool


TipoFondoCondominio = Literal["RESERVA_LEGAL", "CAJA_CHICA", "ESPECIAL"]
ModalidadFacturacion = Literal["ALICUOTA", "CUOTA_FIJA", "PARTES_IGUALES"]
TipoReciboItem = Literal[
    "CUOTA_FIJA",
    "GASTO_COMUN",
    "FONDO_RESERVA",
    "CUOTA_EXTRAORDINARIA",
    "CARGO_INDIVIDUAL",
    "ABONO_CREDITO_PREVIO",
]


class FondoCondominioCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(..., min_length=3, max_length=100)
    tipo: TipoFondoCondominio = "RESERVA_LEGAL"
    porcentaje_recargo: Decimal = Field(default=Decimal("10.00"), ge=Decimal("0.00"), le=Decimal("100.00"))


class FondoCondominioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    tipo: str
    porcentaje_recargo: Decimal
    saldo_actual_usd: Decimal
    es_activo: bool


class FacturarPeriodoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    periodo: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    modalidad: ModalidadFacturacion = "ALICUOTA"
    monto_cuota_fija_usd: Decimal | None = Field(default=None, gt=Decimal("0.00"))
    incluir_fondo_reserva: bool = True
    cuota_extraordinaria_total_usd: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    descripcion_cuota_extraordinaria: str | None = Field(default=None, max_length=200)


class ReciboItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class CertificadoSolvenciaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
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
    folio: str
    unidad_id: int
    identificador_unidad: str
    fecha_vencimiento: date_type
    vigente: bool
    deuda_verificada_usd: Decimal
    firma_hmac: str


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


class OpcionConsultaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    etiqueta: str = Field(..., min_length=2, max_length=120)
    es_opcion_aprobatoria: bool = False


class ConsultaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

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


class VotarConsultaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unidad_id: int = Field(..., strict=True, gt=0)
    opcion_id: int = Field(..., strict=True, gt=0)


class ReciboVotoResponse(BaseModel):
    voto_id: int
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


class PaseVisitaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unidad_id: int = Field(..., strict=True, gt=0)
    nombre_visitante: str = Field(..., min_length=3, max_length=120)
    cedula_visitante: str = Field(..., min_length=5, max_length=25)
    placa_vehiculo: str | None = Field(default=None, max_length=20)
    modalidad: ModalidadPaseQR = "UNICO_USO"
    horas_validez: int = Field(default=24, strict=True, ge=1, le=72)
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


class VerificarPaseQRRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

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


class PaqueteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unidad_id: int = Field(..., strict=True, gt=0)
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
