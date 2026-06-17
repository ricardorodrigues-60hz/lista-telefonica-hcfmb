import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    nome = Column(String, nullable=False)
    senha_hash = Column(String, nullable=False)
    papel = Column(String, nullable=False)  # "GESTOR" ou "CONSULTOR"

class Contato(Base):
    __tablename__ = "contatos"

    id = Column(String, primary_key=True, index=True)  # UUID
    nome = Column(String, nullable=False, index=True)
    telefone = Column(String, nullable=False)
    email = Column(String, nullable=True)
    tipo_numero = Column(String, nullable=False)  # "institucional" ou "publico"
    atualizado_em = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    excluido = Column(Boolean, default=False)

class AuditTrail(Base):
    __tablename__ = "audit_trail"

    id = Column(Integer, primary_key=True, index=True)
    usuario_nome = Column(String, nullable=False)
    acao = Column(String, nullable=False)  # "CRIAR", "EDITAR", "EXCLUIR"
    contato_id = Column(String, nullable=True)
    detalhes = Column(String, nullable=False)
    criado_em = Column(DateTime, default=datetime.datetime.utcnow)
