from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String, nullable=False)
    papel: Mapped[str] = mapped_column(String, nullable=False)  # "GESTOR" ou "CONSULTOR"

class Contato(Base):
    __tablename__ = "contatos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)  # UUID
    nome: Mapped[str] = mapped_column(String, nullable=False, index=True)
    telefone: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=True)
    tipo_numero: Mapped[str] = mapped_column(String, nullable=False)  # "institucional" ou "publico"
    
    # CRUCIAL PARA OFFLINE: Força o PostgreSQL a usar TIMESTAMP WITH TIME ZONE
    # O server_default cria a data no INSERT, o onupdate atualiza a data automaticamente no UPDATE
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    excluido: Mapped[str] = mapped_column(Boolean, default=False)

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
