"""Primitivas de segurança genéricas: JWT e hashing de senha.

Este módulo não conhece nenhum modelo de domínio (ex.: ``Usuario``). Regras
de autenticação/autorização específicas do domínio (RBAC, resolução do
usuário autenticado, etc.) vivem em ``app.modules.auth.service``.
"""

import asyncio
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

# Token URL usado pelo esquema OAuth2 (Swagger UI / clientes), lido de settings.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=settings.TOKEN_URL, auto_error=False)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# --- JWT -------------------------------------------------------------------


def create_access_token(usuario_id: str, papel: str, expires_delta: Optional[timedelta] = None) -> str:
    """Gera um access token JWT de curta duração (padrão: ACCESS_TOKEN_EXPIRE_MINUTES)."""
    expire = _now_utc() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {
        "sub": usuario_id,
        "role": papel,
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(usuario_id: str) -> tuple[str, datetime]:
    """Gera um refresh token JWT de longa duração.

    Retorna o token codificado e seu instante de expiração (UTC), para que o
    chamador persista essa sessão em ``RefreshToken`` e viabilize rotação/revogação.

    Inclui um ``jti`` (nonce aleatório) para garantir que dois tokens emitidos
    no mesmo segundo nunca sejam idênticos — essencial para a rotação funcionar.
    """
    expire = _now_utc() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": usuario_id,
        "refresh": True,
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token, expire


def hash_refresh_token(token: str) -> str:
    """Hash (SHA-256) de um refresh token para persistência segura.

    O JWT bruto nunca é salvo no banco: apenas seu hash, para que um dump do
    banco de dados não permita reutilizar sessões ativas.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def decode_token(token: str) -> dict:
    """Decodifica e valida a assinatura/expiração de um JWT (access ou refresh)."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
        )


# --- Senhas ------------------------------------------------------------------


def get_password_hash(password: str) -> str:
    """Hash a password with bcrypt (blocking)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash (blocking)."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


async def async_get_password_hash(password: str) -> str:
    """Wrapper assíncrono: offload do hashing bcrypt (bloqueante) para uma thread."""
    return await asyncio.to_thread(get_password_hash, password)


async def async_verify_password(plain_password: str, hashed_password: str) -> bool:
    """Wrapper assíncrono: offload da verificação bcrypt (bloqueante) para uma thread."""
    return await asyncio.to_thread(verify_password, plain_password, hashed_password)
