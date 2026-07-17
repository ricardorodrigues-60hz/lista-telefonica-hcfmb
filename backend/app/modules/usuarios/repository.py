import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.modules.usuarios.models import Usuario
from app.modules.auditoria.repository import AuditoriaRepository
from app.core.security import async_get_password_hash


def _now_naive_utc() -> datetime:
    """UTC "naive" (sem tzinfo), padrão adotado no projeto para colunas DateTime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class UsuarioRepository:
    """Repository for user (Usuario) CRUD, using AsyncSession."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.auditoria = AuditoriaRepository(db)

    async def listar_ativos(self) -> List[Usuario]:
        result = await self.db.execute(select(Usuario).where(Usuario.excluido == False))
        return list(result.scalars().all())

    async def buscar_por_id(self, usuario_id: str) -> Optional[Usuario]:
        result = await self.db.execute(select(Usuario).where(Usuario.id == usuario_id))
        return result.scalars().first()

    async def buscar_por_email(self, email: str) -> Optional[Usuario]:
        result = await self.db.execute(select(Usuario).where(Usuario.email == email))
        return result.scalars().first()

    async def criar(self, *, nome: str, email: str, senha: str, papel: str, autor: str) -> Usuario:
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
            acao="CRIAR",
            tabela="usuarios",
            registro_id=usuario.id,
            detalhes=f"Usuário {usuario.email} criado com papel {usuario.papel}.",
            dados_modificados={"nome": nome, "email": email, "papel": papel},
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
            alteracoes["nome"] = nome
            usuario.nome = nome
        if papel is not None and papel != usuario.papel:
            alteracoes["papel"] = papel
            usuario.papel = papel
        if senha is not None:
            alteracoes["senha"] = "***alterada***"
            usuario.senha_hash = await async_get_password_hash(senha)

        usuario.atualizado_em = _now_naive_utc()

        self.auditoria.registrar(
            usuario_nome=autor,
            acao="EDITAR",
            tabela="usuarios",
            registro_id=usuario.id,
            detalhes=f"Usuário {usuario.email} atualizado.",
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
            acao="EXCLUIR",
            tabela="usuarios",
            registro_id=usuario.id,
            detalhes=f"Usuário {usuario.email} marcado como excluído.",
            dados_modificados={"excluido": True},
        )

        await self.db.commit()
