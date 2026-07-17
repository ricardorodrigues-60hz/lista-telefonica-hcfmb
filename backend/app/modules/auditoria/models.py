from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditTrail(Base):
    """Trilha de auditoria imutável para qualquer operação de escrita no sistema.

    Generalizada para cobrir múltiplas tabelas (contatos, usuários, autenticação),
    registrando usuário, ação, tabela afetada, registro afetado, timestamp e um
    snapshot (JSON) dos dados modificados.
    """

    __tablename__ = "audit_trail"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    usuario_nome: Mapped[str] = mapped_column(String, nullable=False)
    acao: Mapped[str] = mapped_column(String, nullable=False)  # "CRIAR", "EDITAR", "EXCLUIR"...
    tabela: Mapped[str] = mapped_column(String, nullable=False, default="contatos")
    registro_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    detalhes: Mapped[str] = mapped_column(String, nullable=False)
    dados_modificados: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # JSON serializado

    # Gravado nativamente pelo banco de dados no momento do INSERT, garantindo precisão e consistência mesmo em cenários offline
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
