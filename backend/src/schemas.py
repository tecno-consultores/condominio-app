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


CorreoValido = Annotated[str, Field(json_schema_extra={"format": "email"}), AfterValidator(_validar_correo)]


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
    url_comprobante: str | None = None


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
    url_factura: str | None = None


class CierreMensualRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    periodo: str = Field(pattern=r"^\d{4}-\d{2}$")
