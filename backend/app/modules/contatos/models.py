from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Contato(Base):
    __tablename__ = "contatos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)  # UUID
    nome: Mapped[str] = mapped_column(String, nullable=False, index=True)
    telefone: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tipo_numero: Mapped[str] = mapped_column(String, nullable=False)  # "institucional" ou "publico"

    # O server_default cria a data no INSERT, o onupdate atualiza a data automaticamente no UPDATE
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    excluido: Mapped[bool] = mapped_column(Boolean, default=False)
