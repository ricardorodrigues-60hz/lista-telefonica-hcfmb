"""Módulo de usuários: modelo, schemas, repository e router.

Consolida o conteúdo de:
  - modules/usuarios/models.py
  - modules/usuarios/schemas.py
  - modules/usuarios/repository.py
  - modules/usuarios/router.py
"""

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Mapped, mapped_column

from app.core import Base, async_get_password_hash, get_db


def _novo_uuid() -> str:
    return str(uuid.uuid4())


class Usuario(Base):
    """Usuário da aplicação, autenticado via e-mail + senha (JWT)."""

    __tablename__ = 'usuarios'

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_novo_uuid
    )
    nome: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(
        String, nullable=False, unique=True, index=True
    )
    senha_hash: Mapped[str] = mapped_column(String, nullable=False)
    papel: Mapped[str] = mapped_column(
        String, nullable=False
    )  # "GESTOR" ou "CONSULTOR"

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    excluido: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


PapelUsuario = Literal['GESTOR', 'CONSULTOR']


class UsuarioBase(BaseModel):
    """Base fields shared by user schemas."""

    nome: str
    email: EmailStr
    papel: PapelUsuario


class UsuarioCreate(UsuarioBase):
    """Payload para o GESTOR criar um novo usuário (com senha em texto puro, hasheada no backend)."""

    senha: str = Field(..., min_length=6, max_length=72)


class UsuarioUpdate(BaseModel):
    """Payload para o GESTOR atualizar um usuário existente. Todos os campos são opcionais."""

    nome: Optional[str]
    papel: Optional[PapelUsuario] = None
    senha: Optional[str] = Field(default=None, min_length=6, max_length=72)


class UsuarioResponse(UsuarioBase):
    """ORM-style response for user retrieval. Nunca expõe `senha_hash`."""

    id: str
    criado_em: datetime
    atualizado_em: datetime
    excluido: bool = False

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


def _now_naive_utc() -> datetime:
    """UTC "naive" (sem tzinfo), padrão adotado no projeto para colunas DateTime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class UsuarioRepository:
    """Repository for user (Usuario) CRUD, using AsyncSession."""

    def __init__(self, db: AsyncSession):
        self.db = db
        # Importação tardia para evitar ciclo entre usuarios <-> contatos
        from app.modules.contatos import AuditoriaRepository

        self.auditoria = AuditoriaRepository(db)

    async def listar_ativos(self) -> List[Usuario]:
        result = await self.db.execute(
            select(Usuario).where(not Usuario.excluido)
        )
        return list(result.scalars().all())

    async def buscar_por_id(self, usuario_id: str) -> Optional[Usuario]:
        result = await self.db.execute(
            select(Usuario).where(Usuario.id == usuario_id)
        )
        return result.scalars().first()

    async def buscar_por_email(self, email: str) -> Optional[Usuario]:
        result = await self.db.execute(
            select(Usuario).where(Usuario.email == email)
        )
        return result.scalars().first()

    async def criar(
        self, *, nome: str, email: str, senha: str, papel: str, autor: str
    ) -> Usuario:
        """Cria um novo usuário e registra a auditoria da criação."""
        usuario = Usuario(
            id=str(uuid.uuid4()),
            nome=nome,
            email=email,
            senha_hash=await async_get_password_hash(senha),
            papel=papel,
        )
        self.db.add(usuario)

        self.auditoria.registrar(
            usuario_nome=autor,
            acao='CRIAR',
            tabela='usuarios',
            registro_id=usuario.id,
            detalhes=f'Usuário {usuario.email} criado com papel {usuario.papel}.',
            dados_modificados={'nome': nome, 'email': email, 'papel': papel},
        )

        await self.db.commit()
        await self.db.refresh(usuario)
        return usuario

    async def atualizar(
        self,
        usuario: Usuario,
        *,
        autor: str,
        nome: Optional[str] = None,
        papel: Optional[str] = None,
        senha: Optional[str] = None,
    ) -> Usuario:
        """Atualiza campos de um usuário existente e registra a auditoria da alteração."""
        alteracoes: dict = {}

        if nome is not None and nome != usuario.nome:
            alteracoes['nome'] = nome
            usuario.nome = nome
        if papel is not None and papel != usuario.papel:
            alteracoes['papel'] = papel
            usuario.papel = papel
        if senha is not None:
            alteracoes['senha'] = '***alterada***'
            usuario.senha_hash = await async_get_password_hash(senha)

        usuario.atualizado_em = _now_naive_utc()

        self.auditoria.registrar(
            usuario_nome=autor,
            acao='EDITAR',
            tabela='usuarios',
            registro_id=usuario.id,
            detalhes=f'Usuário {usuario.email} atualizado.',
            dados_modificados=alteracoes or None,
        )

        await self.db.commit()
        await self.db.refresh(usuario)
        return usuario

    async def deletar_soft(self, usuario: Usuario, *, autor: str) -> None:
        """Exclusão lógica (soft delete) de um usuário."""
        usuario.excluido = True
        usuario.atualizado_em = _now_naive_utc()

        self.auditoria.registrar(
            usuario_nome=autor,
            acao='EXCLUIR',
            tabela='usuarios',
            registro_id=usuario.id,
            detalhes=f'Usuário {usuario.email} marcado como excluído.',
            dados_modificados={'excluido': True},
        )

        await self.db.commit()


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


router = APIRouter(tags=['Usuários'])


# Redefine a rota /me com a dependência correta após o módulo auth ser carregado
def _build_router() -> APIRouter:
    from app.modules.auth import require_gestor

    @router.get('/', response_model=List[UsuarioResponse])
    async def listar_usuarios(
        usuario: Usuario = Depends(require_gestor),
        db: AsyncSession = Depends(get_db),
    ):
        repo = UsuarioRepository(db)
        usuarios = await repo.listar_ativos()
        return [UsuarioResponse.model_validate(u) for u in usuarios]

    @router.get('/{usuario_id}', response_model=UsuarioResponse)
    async def obter_usuario(
        usuario_id: str,
        usuario: Usuario = Depends(require_gestor),
        db: AsyncSession = Depends(get_db),
    ):
        repo = UsuarioRepository(db)
        encontrado = await repo.buscar_por_id(usuario_id)
        if not encontrado or encontrado.excluido:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Usuário não encontrado.',
            )
        return UsuarioResponse.model_validate(encontrado)

    @router.post(
        '/',
        response_model=UsuarioResponse,
        status_code=HTTPStatus.CREATED,
    )
    async def criar_usuario(
        payload: UsuarioCreate,
        usuario: Usuario = Depends(require_gestor),
        db: AsyncSession = Depends(get_db),
    ):
        repo = UsuarioRepository(db)
        if await repo.buscar_por_email(payload.email):
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail='Já existe um usuário com este e-mail.',
            )

        novo = await repo.criar(
            nome=payload.nome,
            email=payload.email,
            senha=payload.senha,
            papel=payload.papel,
            autor=usuario.email,
        )
        return UsuarioResponse.model_validate(novo)

    @router.put('/{usuario_id}', response_model=UsuarioResponse)
    async def atualizar_usuario(
        usuario_id: str,
        payload: UsuarioUpdate,
        usuario: Usuario = Depends(require_gestor),
        db: AsyncSession = Depends(get_db),
    ):
        """Atualiza nome, papel e/ou senha de um usuário existente. Restrito a GESTOR."""
        repo = UsuarioRepository(db)
        encontrado = await repo.buscar_por_id(usuario_id)
        if not encontrado or encontrado.excluido:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Usuário não encontrado.',
            )

        atualizado = await repo.atualizar(
            encontrado,
            autor=usuario.email,
            nome=payload.nome,
            papel=payload.papel,
            senha=payload.senha,
        )
        return UsuarioResponse.model_validate(atualizado)

    @router.delete('/{usuario_id}', status_code=status.HTTP_204_NO_CONTENT)
    async def excluir_usuario(
        usuario_id: str,
        usuario: Usuario = Depends(require_gestor),
        db: AsyncSession = Depends(get_db),
    ):
        """Exclusão lógica (soft delete) de um usuário. Restrito a GESTOR."""
        repo = UsuarioRepository(db)
        encontrado = await repo.buscar_por_id(usuario_id)
        if not encontrado or encontrado.excluido:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Usuário não encontrado.',
            )

        if encontrado.id == usuario.id:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail='Não é possível excluir o próprio usuário autenticado.',
            )

        await repo.deletar_soft(encontrado, autor=usuario.email)

    return router


router = _build_router()
