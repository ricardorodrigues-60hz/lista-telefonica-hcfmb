import logging
from contextlib import asynccontextmanager

from app.core.config import settings
from app.modules.contatos.router import router as contatos_router
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core import init_db

    try:
        await init_db.inicializar_banco()
    except Exception:
        logging.exception(
            "init_db.inicializar_banco() failed during startup; continuing without initializing database"
        )

    yield  # Continua com a execução da aplicação


app = FastAPI(title="Aciono Você API", version="1.0.0", lifespan=lifespan)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],  # Em produção, você deve especificar os domínios permitidos para maior segurança
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the contatos router under the RESTful base path
app.include_router(contatos_router, prefix=f"{settings.API_BASE}/contatos", tags=["Contatos"])

# Root endpoint showing API base information
@app.get("/")
async def read_root():
    return {
        "message": "Aciono Você API",
        "api_base": "/lista-telefonica",
        "docs": "/lista-telefonica/docs",
    }
