from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.core.database import get_db
from app.core.auth.schemas import LoginRequest, TokenResponse, RefreshRequest
from app.modules.usuarios.repository import UsuarioRepository
from app.core.auth.service import (
    create_access_token,
    create_refresh_token,
    SECRET_KEY,
    ALGORITHM,
)

router = APIRouter(tags=["Autenticação"])

@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, 
    db: AsyncSession = Depends(get_db)
):
    """
    Simula o recebimento do token do sistema principal. Para testes locais.
    """
    repo = UsuarioRepository(db)
    usuario = await repo.buscar_por_id_externo(payload.usuario_id_externo)

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário sem permissão cadastrada.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(data={"sub": usuario.usuario_id_externo, "role": usuario.papel})
    refresh_token = create_refresh_token(data={"sub": usuario.usuario_id_externo})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        usuario={"usuario_id_externo": usuario.usuario_id_externo, "papel": usuario.papel},
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_route(
    payload: RefreshRequest, 
    db: AsyncSession = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token inválido ou expirado.",
    )
    
    try:
        token_payload = jwt.decode(payload.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id_externo: str = token_payload.get("sub")

        if usuario_id_externo is None or token_payload.get("refresh") is not True:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    repo = UsuarioRepository(db)
    usuario = await repo.buscar_por_id_externo(usuario_id_externo)
    if not usuario:
        raise credentials_exception

    novo_access_token = create_access_token(data={"sub": usuario.usuario_id_externo, "role": usuario.papel})
    novo_refresh_token = create_refresh_token(data={"sub": usuario.usuario_id_externo})

    return TokenResponse(
        access_token=novo_access_token,
        refresh_token=novo_refresh_token,
        token_type="bearer",
        usuario={"usuario_id_externo": usuario.usuario_id_externo, "papel": usuario.papel},
    )
