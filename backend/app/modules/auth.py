"""Módulo de autenticação: modelo, schemas, repository, service e router.

Consolida o conteúdo de:
  - modules/auth/models.py   (RefreshToken)
  - modules/auth/schemas.py
  - modules/auth/repository.py
  - modules/auth/service.py
  - modules/auth/router.py
"""

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core import Base


def _novo_uuid() -> str:
    return str(uuid.uuid4())


class RefreshToken(Base):
    """Sessões de refresh token persistidas para permitir rotação e revogação real.

    Nunca armazenamos o JWT em texto puro: apenas o hash (SHA-256) do token,
    de modo que um dump do banco não permita reutilizar sessões.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_novo_uuid)
    usuario_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("usuarios.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revogado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Aponta para o novo token emitido na rotação, formando uma cadeia auditável.
    substituido_por_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Credenciais de login: e-mail funcional + senha."""

    login: EmailStr = Field(..., description="E-mail funcional do usuário")
    senha: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Par de tokens JWT retornado por /auth/login e /auth/refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    papel: Literal["GESTOR", "CONSULTOR"]
    nome: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

from datetime import timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


def _now_naive_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RefreshTokenRepository:
    """Repository responsável pela persistência das sessões de refresh token.

    Habilita rotação (o token usado é revogado e substituído por um novo) e
    revogação explícita (logout), além de detecção de reuso de token já
    rotacionado — um indício de token roubado/comprometido.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def criar(self, usuario_id: str, token_hash: str, expira_em: datetime) -> RefreshToken:
        if expira_em.tzinfo is not None:
            expira_em = expira_em.astimezone(timezone.utc).replace(tzinfo=None)

        registro = RefreshToken(
            id=str(uuid.uuid4()),
            usuario_id=usuario_id,
            token_hash=token_hash,
            expira_em=expira_em,
        )
        self.db.add(registro)
        await self.db.commit()
        await self.db.refresh(registro)
        return registro

    async def buscar_por_hash(self, token_hash: str) -> Optional[RefreshToken]:
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalars().first()

    def esta_valido(self, registro: RefreshToken) -> bool:
        if registro.revogado:
            return False
        return registro.expira_em > _now_naive_utc()

    async def revogar_por_token(self, token_hash: str) -> bool:
        registro = await self.buscar_por_hash(token_hash)
        if not registro:
            return False
        registro.revogado = True
        await self.db.commit()
        return True

    async def revogar_todos_do_usuario(self, usuario_id: str) -> None:
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.usuario_id == usuario_id, RefreshToken.revogado == False
            )
        )
        for registro in result.scalars().all():
            registro.revogado = True
        await self.db.commit()

    async def rotacionar(self, registro_antigo: RefreshToken, novo_registro_id: str) -> None:
        """Marca o token antigo como revogado e aponta para o novo (cadeia de rotação)."""
        registro_antigo.revogado = True
        registro_antigo.substituido_por_id = novo_registro_id
        await self.db.commit()


# ---------------------------------------------------------------------------
# Service + RBAC
# ---------------------------------------------------------------------------

from fastapi import Depends
from sqlalchemy.future import select as _select_usuario

from app.core import (
    CredenciaisInvalidasError,
    NaoAutenticadoError,
    PermissaoNegadaError,
    TokenInvalidoError,
    async_verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_db,
    hash_refresh_token,
    oauth2_scheme,
)


class AuthService:
    """Orquestra login, emissão/rotação de tokens e logout."""

    def __init__(self, db: AsyncSession):
        self.db = db
        # UsuarioRepository é importado no nível do módulo (logo abaixo de require_consultor)
        # para que os testes possam fazer monkeypatch em app.modules.auth.UsuarioRepository.
        self.usuarios = UsuarioRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)

    async def _emitir_par_de_tokens(self, usuario) -> tuple[TokenResponse, RefreshToken]:
        """Gera e persiste um novo par access/refresh token para o usuário informado."""
        access_token = create_access_token(usuario.id, usuario.papel)
        refresh_token_bruto, expira_em = create_refresh_token(usuario.id)

        registro = await self.refresh_tokens.criar(
            usuario.id, hash_refresh_token(refresh_token_bruto), expira_em
        )

        resposta = TokenResponse.model_validate(
            {
                "access_token": access_token,
                "refresh_token": refresh_token_bruto,
                "token_type": "bearer",
                "papel": usuario.papel,
                "nome": usuario.nome,
            }
        )
        return resposta, registro

    async def login(self, login: str, senha: str) -> TokenResponse:
        """Autentica um usuário por e-mail + senha e emite access/refresh tokens."""
        usuario = await self.usuarios.buscar_por_email(login)

        if not usuario or usuario.excluido:
            raise CredenciaisInvalidasError()

        if not await async_verify_password(senha, usuario.senha_hash):
            raise CredenciaisInvalidasError()

        resposta, _ = await self._emitir_par_de_tokens(usuario)
        return resposta

    async def refresh(self, refresh_token: str) -> TokenResponse:
        """Rotaciona o refresh token: o token apresentado é invalidado e um novo par é emitido."""
        token_payload = decode_token(refresh_token)
        usuario_id = token_payload.get("sub")
        if usuario_id is None or token_payload.get("refresh") is not True:
            raise TokenInvalidoError()

        token_hash = hash_refresh_token(refresh_token)
        registro = await self.refresh_tokens.buscar_por_hash(token_hash)

        if not registro or registro.usuario_id != usuario_id:
            raise TokenInvalidoError()

        if not self.refresh_tokens.esta_valido(registro):
            if registro.revogado:
                await self.refresh_tokens.revogar_todos_do_usuario(usuario_id)
            raise TokenInvalidoError()

        usuario = await self.usuarios.buscar_por_id(usuario_id)
        if not usuario or usuario.excluido:
            raise TokenInvalidoError()

        nova_resposta, novo_registro = await self._emitir_par_de_tokens(usuario)
        await self.refresh_tokens.rotacionar(registro, novo_registro.id)

        return nova_resposta

    async def logout(self, refresh_token: str) -> None:
        """Revoga o refresh token informado, encerrando a sessão correspondente."""
        await self.refresh_tokens.revogar_por_token(hash_refresh_token(refresh_token))


# --- RBAC / dependências de FastAPI ----------------------------------------


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
):
    """Resolve o usuário autenticado a partir de um access token JWT."""
    if not token:
        raise NaoAutenticadoError()

    try:
        payload = decode_token(token)
    except Exception:
        raise NaoAutenticadoError()

    usuario_id: Optional[str] = payload.get("sub")
    if usuario_id is None or payload.get("refresh") is True:
        raise NaoAutenticadoError()

    from app.modules.usuarios import Usuario
    result = await db.execute(
        _select_usuario(Usuario).where(Usuario.id == usuario_id, Usuario.excluido == False)
    )
    usuario = result.scalars().first()
    if usuario is None:
        raise NaoAutenticadoError()
    return usuario


def require_roles(*papeis: str):
    """Factory de dependência para restringir um endpoint a papéis específicos (RBAC)."""

    async def dependency(usuario=Depends(get_current_user)):
        if usuario.papel not in papeis:
            raise PermissaoNegadaError()
        return usuario

    return dependency


# GESTOR: leitura + escrita de contatos e gestão de usuários.
require_gestor = require_roles("GESTOR")

# CONSULTOR ou GESTOR: qualquer usuário autenticado e ativo (somente leitura para CONSULTOR).
require_consultor = require_roles("GESTOR", "CONSULTOR")

# Expõe como atributo de módulo para facilitar monkeypatch nos testes.
# A importação aqui é segura porque usuarios.py importa de contatos.py,
# não de auth.py — não há ciclo em nível de módulo.
from app.modules.usuarios import UsuarioRepository  # noqa: E402


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

from fastapi import APIRouter, status

router = APIRouter(tags=["Autenticação"])


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Autentica um usuário por e-mail + senha e emite access/refresh tokens."""
    service = AuthService(db)
    return await service.login(payload.login, payload.senha)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_route(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Rotaciona o refresh token, emitindo um novo par access/refresh."""
    service = AuthService(db)
    return await service.refresh(payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    db: AsyncSession = Depends(get_db),
):
    """Revoga o refresh token informado, encerrando a sessão correspondente."""
    service = AuthService(db)
    await service.logout(payload.refresh_token)
    return None
