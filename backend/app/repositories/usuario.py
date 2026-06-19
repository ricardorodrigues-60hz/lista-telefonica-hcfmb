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

    async def buscar_por_id(self, user_id: int) -> Optional[Usuario]:
        result = await self.db.execute(select(Usuario).where(Usuario.id == user_id))
        return result.scalars().first()

    async def buscar_por_login(self, login: str) -> Optional[Usuario]:
        result = await self.db.execute(select(Usuario).where(Usuario.email == login))
        return result.scalars().first()

    async def criar(self, email: str, nome: str, senha_hash: str, papel: str) -> Usuario:
        novo = Usuario(email=email, nome=nome, senha_hash=senha_hash, papel=papel)
        self.db.add(novo)
        await self.db.commit()
        await self.db.refresh(novo)
        return novo

    async def atualizar(self, user_id: int, **fields) -> Optional[Usuario]:
        usuario = await self.buscar_por_id(user_id)
        if not usuario:
            return None
        for k, v in fields.items():
            if hasattr(usuario, k) and v is not None:
                setattr(usuario, k, v)
        self.db.add(usuario)
        await self.db.commit()
        await self.db.refresh(usuario)
        return usuario

    async def atualizar_senha(self, user_id: int, senha_hash: str) -> bool:
        usuario = await self.buscar_por_id(user_id)
        if not usuario:
            return False
        usuario.senha_hash = senha_hash
        self.db.add(usuario)
        await self.db.commit()
        return True

    async def deletar_soft(self, user_id: int) -> bool:
        usuario = await self.buscar_por_id(user_id)
        if not usuario:
            return False
        # implement soft-delete flag if the model had one; fallback to delete
        await self.db.delete(usuario)
        await self.db.commit()
        return True
