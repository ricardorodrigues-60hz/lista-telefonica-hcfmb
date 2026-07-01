from datetime import datetime, timezone
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import engine, Base, async_session_maker
from app.modules.usuarios.models import UsuarioPermissao
from app.modules.contatos.models import Contato

async def inicializar_banco():
    # Cria as tabelas no database se não existirem
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Abre uma sessão para injetar dados testes
    async with async_session_maker() as db:
        # Verifica se os usuários já existem
        await seed_usuarios(db)
        await seed_contatos(db)
        await db.commit()

async def seed_usuarios(db: AsyncSession):
    gestor_id = "admin123"
    
    res_g = await db.execute(select(UsuarioPermissao).filter(UsuarioPermissao.usuario_id_externo == gestor_id))
    if not res_g.scalars().first():
        gestor = UsuarioPermissao(
            usuario_id_externo=gestor_id,
            papel="GESTOR",
        )
        db.add(gestor)

async def seed_contatos(db: AsyncSession):
    # Verifica se a tabela de contatos está vazia
    res = await db.execute(select(Contato))
    if not res.scalars().first():
        now = datetime.now(timezone.utc)
        contatos_iniciais = [
            Contato(
                id="c1b50eb1-e283-4a11-8fa1-b65a440401b3",
                nome="Portaria Principal",
                telefone="(14) 3811-1500",
                email="portaria@hcfmb.unesp.br",
                tipo_numero="publico",
                atualizado_em=now,
                excluido=False,
            ),
            Contato(
                id="f90d1f88-124b-4b13-8cfb-5a1e2f4cb1f4",
                nome="Pronto Socorro - Recepção",
                telefone="(14) 3811-1600",
                email="ps@hcfmb.unesp.br",
                tipo_numero="institucional",
                atualizado_em=now,
                excluido=False,
            ),
            Contato(
                id="d56e7f88-234b-4c13-8dfb-6a2e3f4cb1f5",
                nome="Ambulatório de Especialidades",
                telefone="(14) 3811-1700",
                email="ambulatorio@hcfmb.unesp.br",
                tipo_numero="institucional",
                atualizado_em=now,
                excluido=False,
            ),
        ]
        for c in contatos_iniciais:
            db.add(c)


async def seeds():
    """Compatibility wrapper expected by app.main; initializes DB and seeds data."""
    await inicializar_banco()