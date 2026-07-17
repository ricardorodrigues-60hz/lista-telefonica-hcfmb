"""Agrega os routers de todos os módulos de domínio em um único ``api_router``."""

from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.usuarios.router import router as usuarios_router
from app.modules.contatos.router import router as contatos_router
from app.modules.sync.router import router as sync_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Autenticação"])
api_router.include_router(usuarios_router, prefix="/usuarios", tags=["Usuários"])
api_router.include_router(contatos_router, prefix="/contatos", tags=["Contatos"])
api_router.include_router(sync_router, prefix="/sync", tags=["Sincronização"])
