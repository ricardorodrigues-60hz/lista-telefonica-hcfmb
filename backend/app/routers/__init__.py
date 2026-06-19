from fastapi import APIRouter
from app.routers import auth, contatos, usuarios

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Autenticação"])
api_router.include_router(usuarios.router, prefix="/usuarios", tags=["Usuários"])
api_router.include_router(contatos.router, prefix="/contatos", tags=["Contatos"])