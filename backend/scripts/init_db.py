"""
Script de inicialização do banco de dados.

Uso:
    cd backend/
    .venv\\Scripts\\python -m scripts.init_db
"""
import asyncio
import sys
import os



if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Garante que o diretório raiz do backend esteja no PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine, Base


async def inicializar_banco():
    """Cria todas as tabelas no banco de dados se não existirem."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Banco de dados inicializado com sucesso.")


if __name__ == "__main__":
    asyncio.run(inicializar_banco())
