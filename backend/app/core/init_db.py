"""
Inicialização do banco de dados.

Chamado automaticamente pelo lifespan do FastAPI (app/main.py).
Cria todas as tabelas definidas nos modelos ORM se não existirem.
"""
from app.core.database import engine, Base
from app.modules.contatos.models import Contato  # noqa: F401 — registra o modelo no metadata


async def inicializar_banco():
    """Cria todas as tabelas no banco de dados se não existirem."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
