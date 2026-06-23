from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import SecretStr
import asyncio

from app.models.models import Usuario


class UsuarioRepository:
    """Repository for user operations using AsyncSession."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def listar(self) -> List[Usuario]:
        result = await self.db.execute(select(Usuario))
        return result.scalars().all()

    async def buscar_por_id_externo(self, usuario_id_externo: str) -> Optional[Usuario]:
        result = await self.db.execute(select(Usuario).where(Usuario.usuario_id_externo == usuario_id_externo))
        return result.scalars().first()

    async def salvar_permissao(self, usuario_id_externo: str, papel: str) -> Usuario:
        usuario = await self.buscar_por_id_externo(usuario_id_externo)
        if not usuario:
            usuario = Usuario(usuario_id_externo=usuario_id_externo, papel=papel)
            self.db.add(usuario)
        else:
            usuario.papel = papel
        await self.db.commit()
        await self.db.refresh(usuario)
        return usuario

    async def deletar_permissao(self, usuario_id_externo: str) -> bool:
        usuario = await self.buscar_por_id_externo(usuario_id_externo)
        if not usuario:
            return False
        await self.db.delete(usuario)
        await self.db.commit()
        return True
