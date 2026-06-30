from datetime import datetime
from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class AuditTrail(Base):
    __tablename__ = "audit_trail"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    usuario_nome: Mapped[str] = mapped_column(String, nullable=False)
    acao: Mapped[str] = mapped_column(String, nullable=False)  # "CRIAR", "EDITAR", "EXCLUIR"
    contato_id: Mapped[str] = mapped_column(String, nullable=True)
    detalhes: Mapped[str] = mapped_column(String, nullable=False)
    
    # Gravado nativamente pelo banco de dados no momento do INSERT, garantindo precisão e consistência mesmo em cenários offline
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
