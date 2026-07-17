"""Lógica de autenticação: login, rotação de refresh token, logout e RBAC.

Concentra aqui toda a regra de negócio de autenticação/autorização para que
``router.py`` permaneça responsável apenas por HTTP, e para que outros
módulos (usuarios, contatos, sync) reutilizem as dependências de RBAC
(``get_current_user``, ``require_gestor``, ``require_consultor``) sem
precisar conhecer detalhes de JWT.
"""

from typing import Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.exceptions import CredenciaisInvalidasError, NaoAutenticadoError, PermissaoNegadaError, TokenInvalidoError
from app.core.security import (
    async_verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_refresh_token,
    oauth2_scheme,
)
from app.modules.auth.models import RefreshToken
from app.modules.auth.repository import RefreshTokenRepository
from app.modules.auth.schemas import TokenResponse
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.repository import UsuarioRepository


class AuthService:
    """Orquestra login, emissão/rotação de tokens e logout."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.usuarios = UsuarioRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)

    async def _emitir_par_de_tokens(self, usuario: Usuario) -> tuple[TokenResponse, RefreshToken]:
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
        """Rotaciona o refresh token: o token apresentado é invalidado e um novo par é emitido.

        Caso o token apresentado já tenha sido rotacionado/revogado anteriormente
        (indício de reuso/roubo de token), todas as sessões do usuário são revogadas
        por segurança.
        """
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
                # Token já usado/rotacionado sendo reapresentado: possível token roubado.
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
) -> Usuario:
    """Resolve o usuário autenticado a partir de um access token JWT.

    Levanta 401 quando o token é inválido, do tipo refresh, ou quando o
    usuário não existe/está desativado (soft delete).
    """
    if not token:
        raise NaoAutenticadoError()

    try:
        payload = decode_token(token)
    except Exception:
        raise NaoAutenticadoError()

    usuario_id: Optional[str] = payload.get("sub")
    if usuario_id is None or payload.get("refresh") is True:
        raise NaoAutenticadoError()

    result = await db.execute(
        select(Usuario).where(Usuario.id == usuario_id, Usuario.excluido == False)
    )
    usuario = result.scalars().first()
    if usuario is None:
        raise NaoAutenticadoError()
    return usuario


def require_roles(*papeis: str):
    """Factory de dependência para restringir um endpoint a papéis específicos (RBAC)."""

    async def dependency(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        if usuario.papel not in papeis:
            raise PermissaoNegadaError()
        return usuario

    return dependency


# GESTOR: leitura + escrita de contatos e gestão de usuários.
require_gestor = require_roles("GESTOR")

# CONSULTOR ou GESTOR: qualquer usuário autenticado e ativo (somente leitura para CONSULTOR).
require_consultor = require_roles("GESTOR", "CONSULTOR")
