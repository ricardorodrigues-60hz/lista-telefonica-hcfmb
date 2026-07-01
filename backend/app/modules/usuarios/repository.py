from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.modules.usuarios.models import UsuarioPermissao

class UsuarioRepository:
    """Repository for user permissions mapping."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def buscar_papel_por_id_externo(self, usuario_id_externo: str) -> str:
        """Fetch the role (papel) for an external user ID. Return 'CONSULTOR' by default."""
        if not usuario_id_externo:
            return "CONSULTOR"
        result = await self.db.execute(
            select(UsuarioPermissao.papel).where(UsuarioPermissao.usuario_id_externo == usuario_id_externo)
        )
        papel = result.scalars().first()
        return papel if papel else "CONSULTOR"

    async def salvar_permissao(self, usuario_id_externo: str, papel: str) -> UsuarioPermissao:
        """Helper to create or update permissions, useful for seeds and tests."""
        result = await self.db.execute(
            select(UsuarioPermissao).where(UsuarioPermissao.usuario_id_externo == usuario_id_externo)
        )
        permissao = result.scalars().first()
        if not permissao:
            permissao = UsuarioPermissao(usuario_id_externo=usuario_id_externo, papel=papel)
            self.db.add(permissao)
        else:
            permissao.papel = papel
        await self.db.commit()
        await self.db.refresh(permissao)
        return permissao
