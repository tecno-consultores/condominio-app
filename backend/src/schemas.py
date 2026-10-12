from pydantic import BaseModel, ConfigDict, EmailStr


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

    model_config = ConfigDict(from_attributes=True)
