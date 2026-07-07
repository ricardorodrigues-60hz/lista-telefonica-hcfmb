from fastapi import Depends, HTTPException, Header, status


class UsuarioAutenticado:
    """User object extracted from external JWT headers (hospital system)."""
    def __init__(self, usuario_id_externo: str, papel: str = "GESTOR"):
        self.usuario_id_externo = usuario_id_externo
        self.papel = papel


async def get_current_user(
    x_user_id: str | None = Header(default=None, alias="x-user-id"),
) -> UsuarioAutenticado:
    """Resolve the user from the HTTP Header 'x-user-id' (provided by external JWT from hospital system)."""
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header 'x-user-id' ausente ou inválido.",
        )
    
    # Trust the external JWT from hospital system
    # Default role to GESTOR for simplicity; hospital system handles roles
    return UsuarioAutenticado(usuario_id_externo=x_user_id, papel="GESTOR")


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
