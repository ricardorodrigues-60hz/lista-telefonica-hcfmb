from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.schemas import LoginRequest, TokenResponse, RefreshRequest, LogoutRequest
from app.modules.auth.service import AuthService

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
