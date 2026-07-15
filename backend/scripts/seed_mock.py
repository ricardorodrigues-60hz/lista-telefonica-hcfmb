"""
Script de seed com dados mock para desenvolvimento e testes.

Popula o banco com contatos fictícios de um hospital, cobrindo ramais de TI,
recepção, apoio, corpo clínico, unidades externas e parceiros.

Uso:
    cd backend/
    .venv\\Scripts\\python -m scripts.seed_mock

    # Para apagar tudo e re-popular do zero:
    .venv\\Scripts\\python -m scripts.seed_mock --reset
"""
import asyncio
import sys
import os
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.future import select
from app.core.database import engine, Base, async_session_maker
from app.modules.contatos.models import Contato


# ---------------------------------------------------------------------------
# Dados mock
# ---------------------------------------------------------------------------

MOCK_CONTATOS: list[tuple[str, str, str]] = [
    # (nome, telefone, tipo_numero)

    # Ramais de Tecnologia e Inovação
    ("NÚCLEO DE INOVAÇÃO TECNOLÓGICA",      "6800",           "institucional"),
    ("TI - DESENVOLVIMENTO DE SISTEMAS",    "6810",           "institucional"),
    ("TI - SUPORTE E INFRAESTRUTURA",       "6812",           "institucional"),
    ("TELEMEDICINA E TELESSAÚDE",           "6820",           "institucional"),

    # Setores de Atendimento e Recepção
    ("ACOLHIMENTO E TRIAGEM PRINCIPAL",          "6701",      "institucional"),
    ("AMBULATÓRIO DE ESPECIALIDADES MOCK",        "6702",      "institucional"),
    ("RECEPÇÃO CENTRAL - PORTARIA A",             "6703",      "institucional"),

    # Áreas de Apoio e Logística
    ("ALMOXARIFADO CENTRAL",                      "6910",      "institucional"),
    ("FARMÁCIA DE ALTO CUSTO (MOCK)",             "3899-1000", "institucional"),
    ("BANCO DE SANGUE - ATENDIMENTO",             "3899-2000", "institucional"),
    ("BRINQUEDOTECA HOSPITALAR",                  "6922",      "institucional"),

    # Corpo Clínico e UTIs
    ("UTI ADULTO GERAL (MOCK)",                   "6950",      "institucional"),
    ("POSTO DE ENFERMAGEM - ALA SUL",             "6961",      "institucional"),
    ("POSTO DE ENFERMAGEM - ALA NORTE",           "6962",      "institucional"),
    ("SALA DE ESTUDOS - RESIDÊNCIA MÉDICA",       "6970",      "institucional"),

    # Serviços de Apoio e Bem-Estar
    ("SERVIÇO DE CAPELANIA",                      "6980",      "institucional"),
    ("VOLUNTARIADO HOSPITALAR",                   "6981",      "institucional"),
    ("REFEITÓRIO DOS COLABORADORES",              "6990",      "institucional"),

    # Unidades Externas Fictícias
    ("POSTO DE SAÚDE JARDIM DAS FLORES",          "3899-3010", "institucional"),
    ("POSTO DE SAÚDE VILA ESPERANÇA",             "3899-3020", "institucional"),
    ("POSTO DE SAÚDE BAIRRO VERDE",               "3899-3030", "institucional"),
    ("AMBULÂNCIA DE EMERGÊNCIA - BASE 1",         "99888-1122","institucional"),
    ("OUVIDORIA GERAL (0800 FICTÍCIO)",           "0800-999-9999","institucional"),

    # Parceiros e Terceirizados Fictícios
    ("CAFETERIA DO BOULEVARD (MOCK)",             "99888-3344","institucional"),
    ("COOPERATIVA DE CRÉDITO EXEMPLO",            "99888-5566","institucional"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _drop_and_create_tables():
    """Apaga e recria todas as tabelas (somente com --reset)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("[RESET] Tabelas recriadas do zero.")


async def _ensure_tables():
    """Cria as tabelas se não existirem."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed(reset: bool = False):
    if reset:
        await _drop_and_create_tables()
    else:
        await _ensure_tables()

    now = datetime.now(timezone.utc)

    async with async_session_maker() as db:
        # Verifica se já há dados para evitar duplicatas
        res = await db.execute(select(Contato).limit(1))
        if res.scalars().first() and not reset:
            print("[AVISO] Banco ja contem registros. Use --reset para re-popular.")
            return

        inseridos = 0
        for nome, telefone, tipo_numero in MOCK_CONTATOS:
            contato = Contato(
                id=str(uuid.uuid4()),
                nome=nome,
                telefone=telefone,
                email=None,
                tipo_numero=tipo_numero,
                atualizado_em=now,
                excluido=False,
            )
            db.add(contato)
            inseridos += 1

        await db.commit()
        print(f"[OK] {inseridos} contatos mock inseridos com sucesso.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    reset = "--reset" in sys.argv
    asyncio.run(seed(reset=reset))
