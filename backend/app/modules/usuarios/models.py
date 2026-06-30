from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    usuario_id_externo: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    papel: Mapped[str] = mapped_column(String, nullable=False)  # "GESTOR" ou "CONSULTOR"
