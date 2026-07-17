import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _novo_uuid() -> str:
    return str(uuid.uuid4())


class Usuario(Base):
    """Usuário da aplicação, autenticado via e-mail + senha (JWT)."""

    __tablename__ = "usuarios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_novo_uuid)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String, nullable=False)
    papel: Mapped[str] = mapped_column(String, nullable=False)  # "GESTOR" ou "CONSULTOR"

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    excluido: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
