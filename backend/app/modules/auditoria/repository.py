import json
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.modules.auditoria.models import AuditTrail


def serializar(dados: dict) -> str:
    return json.dumps(dados, default=str, ensure_ascii=False)


class AuditoriaRepository:
    """Repository responsável por registrar e consultar a trilha de auditoria.

    ``registrar`` apenas prepara (``add``) o registro na sessão corrente e não
    executa commit: cabe ao chamador (outro repository) commitar a transação,
    garantindo que a mudança de dado e sua auditoria sejam atômicas.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def registrar(
        self,
        *,
        usuario_nome: str,
        acao: str,
        tabela: str,
        registro_id: Optional[str],
        detalhes: str,
        dados_modificados: Optional[dict] = None,
    ) -> AuditTrail:
        entrada = AuditTrail(
            usuario_nome=usuario_nome,
            acao=acao,
            tabela=tabela,
            registro_id=registro_id,
            detalhes=detalhes,
            dados_modificados=serializar(dados_modificados) if dados_modificados is not None else None,
        )
        self.db.add(entrada)
        return entrada

    async def listar_por_tabela(self, tabela: str) -> List[AuditTrail]:
        result = await self.db.execute(
            select(AuditTrail).where(AuditTrail.tabela == tabela).order_by(AuditTrail.criado_em.desc())
        )
        return list(result.scalars().all())
