from pydantic import BaseModel, EmailStr
from typing import Optional

class UsuarioBase(BaseModel):
    nombre: str
    cedula: str
    correo: EmailStr
    telefono: str

class UsuarioCreate(UsuarioBase):
    password: str
    unidad_solicitada_id: int
    tipo_ocupante_solicitado: str

class UsuarioResponse(UsuarioBase):
    id: int
    es_activo: bool
    rol: str

    class Config:
        from_attributes = True