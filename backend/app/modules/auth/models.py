import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _novo_uuid() -> str:
    return str(uuid.uuid4())


class RefreshToken(Base):
    """Sessões de refresh token persistidas para permitir rotação e revogação real.

    Nunca armazenamos o JWT em texto puro: apenas o hash (SHA-256) do token,
    de modo que um dump do banco não permita reutilizar sessões.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_novo_uuid)
    usuario_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("usuarios.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revogado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Aponta para o novo token emitido na rotação, formando uma cadeia auditável.
    substituido_por_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
