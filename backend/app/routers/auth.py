# backend/app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
import asyncio

from app.database import get_db
from app.schemas import LoginRequest, TokenResponse, RefreshRequest
from app.repositories import UsuarioRepository
from app.core.auth import (
    create_access_token,
    create_refresh_token,
    SECRET_KEY,
    ALGORITHM,
)
from app.core.passwords import async_verify_password

# Prefix applied by central router: api_router.include_router(auth.router, prefix="/auth")
router = APIRouter(tags=["Autenticação"])

@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, 
    db: AsyncSession = Depends(get_db)
):
    """
    Autentica o usuário usando o login institucional (Intranet) e retorna os tokens JWT.
    
    Args:
        payload (LoginRequest): Contrato contendo login e senha.
        db (AsyncSession): Sessão assíncrona com o SQLite.
        
    Returns:
        TokenResponse: Par de tokens (Access/Refresh) e os metadados do usuário logado.
    """
    repo = UsuarioRepository(db)
    # Totalmente alinhado com o seu core/auth.py que usa o identificador da Intranet
    usuario = await repo.buscar_por_login(payload.login)

    # senha é SecretStr no schema; extrai valor para verificação
    senha_plain = payload.senha.get_secret_value()
    # verify_password usa bcrypt (bloqueante) — use helper que roda em thread pool
    senha_ok = await async_verify_password(senha_plain, usuario.senha_hash) if usuario else False

    if not usuario or not senha_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Injeta o login no 'sub' e o papel (role) para o controle RBAC do PWA
    access_token = create_access_token(data={"sub": usuario.login, "role": usuario.papel})
    refresh_token = create_refresh_token(data={"sub": usuario.login})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        usuario={"nome": usuario.nome, "login": usuario.login, "papel": usuario.papel},
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_route(
    payload: RefreshRequest, 
    db: AsyncSession = Depends(get_db)
):
    """
    Renova o Access Token de curta duração utilizando o Refresh Token salvo no cliente.
    Garante resiliência de sessão quando o PWA transita entre estados online/offline.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token inválido ou expirado.",
    )
    
    try:
        # Decodifica o token usando as constantes mapeadas e expostas pelo seu core/auth.py
        token_payload = jwt.decode(payload.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        login: str = token_payload.get("sub")

        # Validação estrita: além do sub, o token DEVE conter a flag customizada 'refresh' criada no core
        if login is None or token_payload.get("refresh") is not True:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    repo = UsuarioRepository(db)
    usuario = await repo.buscar_por_login(login)
    if not usuario:
        raise credentials_exception

    # Aplica Token Rotation: gera novos tokens invalidando o ciclo anterior para maior segurança
    novo_access_token = create_access_token(data={"sub": usuario.login, "role": usuario.papel})
    novo_refresh_token = create_refresh_token(data={"sub": usuario.login})

    return TokenResponse(
        access_token=novo_access_token,
        refresh_token=novo_refresh_token,
        token_type="bearer",
        usuario={"nome": usuario.nome, "login": usuario.login, "papel": usuario.papel},
    )