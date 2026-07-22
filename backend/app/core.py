"""Núcleo da aplicação: configuração, banco de dados, segurança e exceções.

Consolida o conteúdo de:
  - core/config.py
  - core/logging.py
  - core/database.py
  - core/exceptions.py
  - core/security.py
  - core/init_db.py
"""

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
import asyncio
import hashlib
import importlib.util
import logging
import os
import sys
import uuid
import warnings
from datetime import datetime, timedelta, timezone
from datetime import timezone as _tz
from http import HTTPStatus
from typing import AsyncGenerator, Optional

import bcrypt
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession
from sqlalchemy.future import select as _select
from sqlalchemy.orm import DeclarativeBase


class Settings(BaseSettings):
    """Application settings."""

    DATABASE_URL: str = 'sqlite+aiosqlite:///:memory:'
    SECRET_KEY: str = 'super-secret-key-padrao-caso-nao-exista-no-env'
    ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    TOKEN_URL: str = '/api/auth/login'

    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8', extra='ignore'
    )


settings = Settings()


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
        )
    )
    root.addHandler(handler)
    root.setLevel(level)


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


_env_db = os.getenv('DATABASE_URL')


def _choose_database_url(url: str | None) -> str:
    if not url:
        return 'sqlite+aiosqlite:///:memory:'
    if (
        url.startswith('postgresql+asyncpg')
        and importlib.util.find_spec('asyncpg') is None
    ):
        warnings.warn(
            'asyncpg not installed;'
            ' falling back to in-memory sqlite+aiosqlite for tests',
            RuntimeWarning,
        )
        return 'sqlite+aiosqlite:///:memory:'
    return url


DATABASE_URL = _choose_database_url(_env_db)

engine = create_async_engine(DATABASE_URL, echo=False)

async_session_maker = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AppError(Exception):
    status_code: int = HTTPStatus.BAD_REQUEST
    detail: str = 'Error inesperado.'

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.detail
        super().__init__(self.detail)


class CredenciaisInvalidasError(AppError):
    status_code = HTTPStatus.UNAUTHORIZED
    detail = 'E-mail ou senha inválidos.'


class TokenInvalidoError(AppError):
    status_code = HTTPStatus.UNAUTHORIZED
    detail = 'Refresh token inválido, revogado ou expirado.'


class NaoAutenticadoError(AppError):
    status_code = HTTPStatus.UNAUTHORIZED
    detail = 'Could not validate credentials'


class PermissaoNegadaError(AppError):
    status_code = HTTPStatus.FORBIDDEN
    detail = 'Operação não permitida para o seu papel.'


class RegistroNaoEncontradoError(AppError):
    status_code = HTTPStatus.NOT_FOUND
    detail = 'Registro não encontrado.'


class RegraDeNegocioError(AppError):
    """Violação de uma regra de negócio (ex.: e-mail duplicado)."""

    status_code = HTTPStatus.BAD_REQUEST


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        headers = (
            {'WWW-Authenticate': 'Bearer'}
            if exc.status_code == HTTPStatus.UNAUTHORIZED
            else None
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={'detail': exc.detail},
            headers=headers,
        )


# ---------------------------------------------------------------------------
# Security — JWT e hashing de senha
# ---------------------------------------------------------------------------


SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=settings.TOKEN_URL, auto_error=False
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(
    usuario_id: str, papel: str, expires_delta: Optional[timedelta] = None
) -> str:
    """Gera um access token JWT de curta duração."""
    expire = _now_utc() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode = {
        'sub': usuario_id,
        'role': papel,
        'exp': int(expire.timestamp()),
        'jti': str(uuid.uuid4()),
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(usuario_id: str) -> tuple[str, datetime]:
    """Gera um refresh token JWT de longa duração.

    Retorna o token codificado e seu instante de expiração (UTC).
    """
    expire = _now_utc() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        'sub': usuario_id,
        'refresh': True,
        'exp': int(expire.timestamp()),
        'jti': str(uuid.uuid4()),
    }
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token, expire


def hash_refresh_token(token: str) -> str:
    """Hash (SHA-256) de um refresh token para persistência segura."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def decode_token(token: str) -> dict:
    """Decodifica e valida a assinatura/expiração de um JWT."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token inválido ou expirado.',
        )


def get_password_hash(password: str) -> str:
    """Hash a password with bcrypt (blocking)."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode(
        'utf-8'
    )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash (blocking)."""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), hashed_password.encode('utf-8')
        )
    except Exception:
        return False


async def async_get_password_hash(password: str) -> str:
    """Wrapper assíncrono: offload do hashing bcrypt para uma thread."""
    return await asyncio.to_thread(get_password_hash, password)


async def async_verify_password(
    plain_password: str, hashed_password: str
) -> bool:
    """Wrapper assíncrono: offload da verificação bcrypt para uma thread."""
    return await asyncio.to_thread(
        verify_password, plain_password, hashed_password
    )


# ---------------------------------------------------------------------------
# Init DB / Seeds
# ---------------------------------------------------------------------------


# Contas padrão de desenvolvimento.
# ATENÇÃO: desative essas senhas antes de qualquer deploy em produção.
CONTAS_SEED = [
    {
        'nome': 'Gestor HCFMB',
        'email': 'gestor@hcfmb.unesp.br',
        'senha': 'gestor123',
        'papel': 'GESTOR',
    },
    {
        'nome': 'Consultor HCFMB',
        'email': 'consultor@hcfmb.unesp.br',
        'senha': 'consultor123',
        'papel': 'CONSULTOR',
    },
]


async def inicializar_banco():
    """Cria as tabelas no banco se não existirem e injeta dados iniciais."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as db:
        await _seed_usuarios(db)
        await _seed_contatos(db)
        await db.commit()


async def _seed_usuarios(db: _AsyncSession):
    from app.modules.usuarios import Usuario

    for conta in CONTAS_SEED:
        res = await db.execute(
            _select(Usuario).where(Usuario.email == conta['email'])
        )
        if not res.scalars().first():
            usuario = Usuario(
                nome=conta['nome'],
                email=conta['email'],
                senha_hash=await async_get_password_hash(conta['senha']),
                papel=conta['papel'],
            )
            db.add(usuario)


async def _seed_contatos(db: _AsyncSession):
    from app.modules.contatos import Contato

    res = await db.execute(_select(Contato))
    if not res.scalars().first():
        now = datetime.now(_tz.utc)
        contatos_iniciais = [
            Contato(
                id='c1b50eb1-e283-4a11-8fa1-b65a440401b3',
                nome='Portaria Principal',
                telefone='(14) 3811-1500',
                email='portaria@hcfmb.unesp.br',
                tipo_numero='publico',
                atualizado_em=now,
                excluido=False,
            ),
            Contato(
                id='f90d1f88-124b-4b13-8cfb-5a1e2f4cb1f4',
                nome='Pronto Socorro - Recepção',
                telefone='(14) 3811-1600',
                email='ps@hcfmb.unesp.br',
                tipo_numero='institucional',
                atualizado_em=now,
                excluido=False,
            ),
            Contato(
                id='d56e7f88-234b-4c13-8dfb-6a2e3f4cb1f5',
                nome='Ambulatório de Especialidades',
                telefone='(14) 3811-1700',
                email='ambulatorio@hcfmb.unesp.br',
                tipo_numero='institucional',
                atualizado_em=now,
                excluido=False,
            ),
        ]
        for c in contatos_iniciais:
            db.add(c)


async def seeds():
    await inicializar_banco()
