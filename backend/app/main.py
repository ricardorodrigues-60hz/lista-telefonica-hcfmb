from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.routers import api_router


# from sqlalchemy.orm import Session
# from typing import List

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Aqui você pode colocar código que será executado no início e no final da aplicação
    # Por exemplo, inicializar o banco de dados, criar tabelas, etc.
    # Import seeds lazily to avoid import-time side effects during tests
    from app.core import init_db
    await init_db.seeds()
    yield  # Continua com a execução da aplicação
    # Código de finalização (se necessário) pode ser colocado aqui
    pass

app = FastAPI(title="Aciono Você API", version="1.0.0", lifespan=lifespan)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produ~ção, você deve especificar os domínios permitidos para maior segurança
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")