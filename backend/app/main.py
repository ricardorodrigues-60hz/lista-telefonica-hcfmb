"""Ponto de entrada da aplicação FastAPI.

Consolida também o conteúdo de api.py (agregação de routers).
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import configure_logging, register_exception_handlers
from app.modules.auth import router as auth_router
from app.modules.usuarios import router as usuarios_router
from app.modules.contatos import router as contatos_router
from app.modules.sync import router as sync_router

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Importação lazy para evitar efeitos colaterais em tempo de importação (útil em testes)
    from app.core import seeds

    # Only run seeds when explicitly enabled (useful to skip in tests/CI)
    if os.getenv("RUN_SEEDS", "0") == "1":
        try:
            await seeds()
        except Exception:
            logging.exception("seeds() failed during startup; continuing without seeding")

    yield  # Continua com a execução da aplicação


app = FastAPI(title="Aciono Você API", version="1.0.0", lifespan=lifespan)

register_exception_handlers(app)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique os domínios permitidos para maior segurança
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["Autenticação"])
app.include_router(usuarios_router, prefix="/api/usuarios", tags=["Usuários"])
app.include_router(contatos_router, prefix="/api/contatos", tags=["Contatos"])
app.include_router(sync_router, prefix="/api/sync", tags=["Sincronização"])
