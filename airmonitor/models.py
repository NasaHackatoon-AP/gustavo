from sqlalchemy import Column, Integer, Float, String, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from airqualityapp.database import Base

class AQILocalHistorico(Base):
    """
    Histórico de AQI por localização e usuário
    """
    __tablename__ = "aqi_local_historico"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)  # opcional
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    aqi_original = Column(Integer, nullable=False)
    aqi_personalizado = Column(Integer, nullable=False)
    nivel_alerta = Column(String, nullable=False)
    data_hora = Column(TIMESTAMP(timezone=True), server_default=func.now())
