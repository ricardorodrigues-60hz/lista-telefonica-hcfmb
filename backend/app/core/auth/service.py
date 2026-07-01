from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.usuarios.repository import UsuarioRepository

class UsuarioAutenticado:
    """Mock user object to preserve attribute compatibility with existing endpoints."""
    def __init__(self, usuario_id_externo: str, papel: str):
        self.usuario_id_externo = usuario_id_externo
        self.papel = papel


async def get_current_user(
    x_user_id: str | None = Header(default=None, alias="x-user-id"),
    db: AsyncSession = Depends(get_db)
) -> UsuarioAutenticado:
    """Resolve the user from the HTTP Header 'x-user-id' and fetch their mapped role."""
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header 'x-user-id' ausente ou inválido.",
        )
    
    repo = UsuarioRepository(db)
    papel = await repo.buscar_papel_por_id_externo(x_user_id)
    return UsuarioAutenticado(usuario_id_externo=x_user_id, papel=papel)


async def require_gestor(
    usuario: UsuarioAutenticado = Depends(get_current_user)
) -> UsuarioAutenticado:
    """Require GESTOR role for protected actions."""
    if usuario.papel != "GESTOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operação permitida apenas para Gestores.",
        )
    return usuario
