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
    nombre: str
    cedula: str
    correo: CorreoValido
    telefono: str


class UsuarioCreate(UsuarioBase):
    password: str
    unidad_solicitada_id: int = Field(strict=True)
    tipo_ocupante_solicitado: str


class UsuarioResponse(UsuarioBase):
    id: int
    es_activo: bool
    rol: str

    model_config = ConfigDict(from_attributes=True)


Moneda = Literal["USD", "VES"]


class TasaCambioCreate(BaseModel):
    fecha: date_type | None = None
    tasa_usd_ves: Decimal = Field(gt=0)


class TasaCambioResponse(BaseModel):
    fecha: date_type
    tasa_usd_ves: Decimal

    model_config = ConfigDict(from_attributes=True)


class ReciboCreate(BaseModel):
    unidad_id: int = Field(strict=True)
    periodo: str = Field(pattern=r"^\d{4}-\d{2}$")
    monto_usd: Decimal = Field(gt=0)


class ReciboResponse(BaseModel):
    id: int
    unidad_id: int
    periodo: str
    monto_usd: Decimal
    monto_pagado_usd: Decimal
    estado: str
    bloqueado: bool

    model_config = ConfigDict(from_attributes=True)


class PagoReportar(BaseModel):
    recibo_id: int = Field(strict=True)
    monto: Decimal = Field(gt=0)
    moneda: Moneda
    metodo_pago: str
    numero_referencia: str | None = None
    url_comprobante: str | None = None


class PagoResponse(BaseModel):
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

    model_config = ConfigDict(from_attributes=True)


class PagoRechazo(BaseModel):
    motivo: str = Field(min_length=1)


class EgresoCreate(BaseModel):
    periodo: str = Field(pattern=r"^\d{4}-\d{2}$")
    categoria: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)
    monto: Decimal = Field(gt=0)
    moneda: Moneda
    url_factura: str | None = None


class CierreMensualRequest(BaseModel):
    periodo: str = Field(pattern=r"^\d{4}-\d{2}$")
