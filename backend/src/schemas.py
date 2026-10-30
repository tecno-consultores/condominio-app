from datetime import date as date_type
from decimal import Decimal
from typing import Annotated, Literal

import email_validator
from pydantic import AfterValidator, BaseModel, ConfigDict, Field


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
