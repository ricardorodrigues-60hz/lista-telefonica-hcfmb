from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.modules.usuarios.models import UsuarioPermissao
from app.core.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

# Token URL should be absolute path used by the client, read dynamically from settings
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=settings.TOKEN_URL, auto_error=False)

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = _now_utc() + expires_delta
    else:
        expire = _now_utc() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # JWT standard requires 'exp' as a numeric timestamp
    to_encode.update({"exp": int(expire.timestamp()), "role": data.get("role") or data.get("papel")})
    # keep both keys for compatibility: 'role' is preferred but some code may use 'papel'
    if "papel" not in to_encode and data.get("papel"):
        to_encode["papel"] = data.get("papel")
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = _now_utc() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": int(expire.timestamp()), "refresh": True})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> UsuarioPermissao:
    """Resolve the current user from a JWT token asynchronously.

    Raises HTTPException 401 when token is invalid or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id_externo: Optional[str] = payload.get("sub")
        if usuario_id_externo is None or payload.get("refresh") is True:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(UsuarioPermissao).where(UsuarioPermissao.usuario_id_externo == usuario_id_externo))
    usuario = result.scalars().first()
    if usuario is None:
        raise credentials_exception
    return usuario


def require_gestor(usuario: UsuarioPermissao = Depends(get_current_user)) -> UsuarioPermissao:
    if usuario.papel != "GESTOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operação permitida apenas para Gestores.",
        )
    return usuario
