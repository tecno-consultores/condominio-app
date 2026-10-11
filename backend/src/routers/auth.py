from fastapi import APIRouter, Depends, HTTPException, Response, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.database import get_db
from src.models import Usuario, ContratoOcupacion
from src.schemas import UsuarioCreate, UsuarioResponse
from src.security import create_access_token, get_password_hash, verify_password
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])

class LoginData(BaseModel):
    correo: str
    password: str

@router.post("/register", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user: UsuarioCreate, 
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db)
):
    try:
        # TODO: Implementar validación de idempotencia real con Redis
        
        result = await db.execute(select(Usuario).where((Usuario.correo == user.correo) | (Usuario.cedula == user.cedula)))
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Usuario ya registrado")
        
        new_user = Usuario(
            nombre=user.nombre,
            cedula=user.cedula,
            correo=user.correo,
            telefono=user.telefono,
            password_hash=get_password_hash(user.password),
            es_activo=False,
            rol="FANTASMA"
        )
        db.add(new_user)
        await db.flush()
        
        nuevo_contrato = ContratoOcupacion(
            usuario_id=new_user.id,
            unidad_id=user.unidad_solicitada_id,
            tipo_ocupante=user.tipo_ocupante_solicitado,
            es_activo=False
        )
        db.add(nuevo_contrato)
        await db.commit()
        await db.refresh(new_user)
        
        # TODO: worker.notify_junta.delay(new_user.id)
        
        return new_user
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error en base de datos al registrar")

@router.post("/login")
async def login(response: Response, login_data: LoginData, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Usuario).where(Usuario.correo == login_data.correo))
    user = result.scalars().first()
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
        
    access_token = create_access_token(data={"sub": user.correo, "rol": user.rol})
    response.set_cookie(
        key="access_token", 
        value=f"Bearer {access_token}", 
        httponly=True, 
        secure=True, 
        samesite="lax"
    )
    return {"message": "Login exitoso", "rol": user.rol}

@router.get("/me")
async def get_me(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="No autenticado")
    # TODO: Validar firma del token JWT real
    return {"status": "authenticated", "token_present": True}