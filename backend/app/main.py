from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging

from app.core.auth.router import router as auth_router
from app.modules.usuarios.router import router as usuarios_router
from app.modules.contatos.router import router as contatos_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core import init_db

    # Only run seeds when explicitly enabled (useful to skip in tests/CI)
    if os.getenv("RUN_SEEDS", "0") == "1":
        try:
            await init_db.seeds()
        except Exception:
            logging.exception("init_db.seeds() failed during startup; continuing without seeding")

    yield  # Continua com a execução da aplicação

app = FastAPI(title="Aciono Você API", version="1.0.0", lifespan=lifespan)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, você deve especificar os domínios permitidos para maior segurança
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Aggregate API router with prefixes compatible with existing paths
api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["Autenticação"])
api_router.include_router(usuarios_router, prefix="/usuarios", tags=["Usuários"])
api_router.include_router(contatos_router, prefix="/contatos", tags=["Contatos"])

app.include_router(api_router, prefix="/api")