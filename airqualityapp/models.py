from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from .database import Base  # <-- use ponto para importação relativa

from sqlalchemy.orm import relationship

class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    data_nascimento = Column(Date, nullable=True)
    cidade = Column(String, nullable=True)
    estado = Column(String, nullable=True)


class PerfilSaude(Base):
    __tablename__ = "perfil_saude"
    __table_args__ = {"extend_existing": True}  # <-- importante

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    possui_asma = Column(Boolean, default=False)
    possui_dpoc = Column(Boolean, default=False)
    possui_alergias = Column(Boolean, default=False)
    fumante = Column(Boolean, default=False)
    sensibilidade_alta = Column(Boolean, default=False)

    usuario = relationship("Usuario")  # <--- agora você consegue acessar perfil.usuario

class AQIPersonalizadoHistorico(Base):
    __tablename__ = "aqi_personalizado_historico"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"))
    data_hora = Column(TIMESTAMP, server_default=func.now())
    aqi_original = Column(Integer)
    aqi_personalizado = Column(Integer)
    nivel_alerta = Column(String(100))

class AlertasEnviados(Base):
    __tablename__ = "alertas_enviados"
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"))
    nivel_alerta = Column(String(100))
    data_hora = Column(TIMESTAMP, server_default=func.now())
    metodo = Column(String(50))