from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging

from app.modules.contatos.router import router as contatos_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core import init_db

    try:
        await init_db.inicializar_banco()
    except Exception:
        logging.exception("init_db.inicializar_banco() failed during startup; continuing without initializing database")

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
api_router.include_router(contatos_router, prefix="/contatos", tags=["Contatos"])

app.include_router(api_router, prefix="/api")

@app.get("/")
async def read_root():
    return {
        "message": "Aciono Você API",
        "api_base": "/api",
        "docs": "/docs",
    }

@app.get("/api")
async def read_api_root():
    return {"message": "Aciono Você API!"}