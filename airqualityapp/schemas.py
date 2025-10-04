from pydantic import BaseModel
from typing import Optional
from datetime import date

class UsuarioCreate(BaseModel):
    nome: str
    email: str
    senha: str
    data_nascimento: Optional[date]
    cidade: Optional[str]
    estado: Optional[str]

class PerfilSaudeCreate(BaseModel):
    usuario_id: int
    possui_asma: bool = False
    possui_dpoc: bool = False
    possui_alergias: bool = False
    fumante: bool = False
    sensibilidade_alta: bool = False

class AQIResponse(BaseModel):
    aqi_original: int
    aqi_personalizado: int
    nivel_alerta: str