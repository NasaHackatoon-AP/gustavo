from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import requests
import os
import logging

from airqualityapp.database import get_db
from airqualityapp.crud import salvar_historico, obter_perfil_usuario
from airqualityapp.utils import calcular_indice_personalizado
from .monitor import obter_aqi_nasa_tempo_geo
from .notifications import enviar_alerta_push

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = APIRouter()

# Variável de API
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# --- Modelos Pydantic para resposta ---
class Clima(BaseModel):
    cidade: Optional[str]
    temperatura: Optional[float]
    umidade: Optional[int]
    vento: Optional[float]
    descricao: Optional[str]

class AqiResponse(BaseModel):
    latitude: float
    longitude: float
    aqi_original: float
    aqi_personalizado: float
    nivel_alerta: str
    usuario_id: Optional[int]
    clima: Optional[Clima]


# --- Função para buscar dados da OpenWeather ---
def obter_dados_openweather(lat: float, lon: float):
    if not OPENWEATHER_API_KEY:
        logger.error("Chave da OpenWeather não encontrada no ambiente")
        return None

    url = (
        f"https://api.openweathermap.org/data/2.5/weather?"
        f"lat={lat}&lon={lon}&units=metric&appid={OPENWEATHER_API_KEY}&lang=pt_br"
    )
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        return {
            "cidade": data.get("name"),
            "temperatura": data["main"]["temp"],
            "umidade": data["main"]["humidity"],
            "vento": data["wind"]["speed"],
            "descricao": data["weather"][0]["description"]
        }
    except Exception as e:
        logger.error(f"Erro ao buscar dados do OpenWeather: {e}")
        return None


# --- Função para processar AQI personalizado ---
def processar_aqi_para_usuario(db: Session, usuario_id: int, aqi_original: float):
    try:
        perfil = obter_perfil_usuario(db, usuario_id)
        if perfil:
            perfil_dict = {
                "possui_asma": perfil.possui_asma,
                "possui_dpoc": perfil.possui_dpoc,
                "possui_alergias": perfil.possui_alergias,
                "fumante": perfil.fumante,
                "sensibilidade_alta": perfil.sensibilidade_alta
            }
            aqi_personalizado, nivel_alerta = calcular_indice_personalizado(aqi_original, perfil_dict)

            try:
                salvar_historico(db, usuario_id, aqi_original, aqi_personalizado, nivel_alerta)
            except Exception as e:
                logger.error(f"Erro ao salvar histórico: {e}")

            return aqi_personalizado, nivel_alerta
        else:
            logger.warning(f"Perfil não encontrado para usuário {usuario_id}")
            return aqi_original, "verde"
    except Exception as e:
        logger.error(f"Erro ao processar perfil do usuário: {e}")
        return aqi_original, "verde"

@app.get("/monitor/aqi", response_model=AqiResponse)
def monitor_aqi_live(
    lat: float = Query(..., description="Latitude do usuário"),
    lon: float = Query(..., description="Longitude do usuário"),
    usuario_id: Optional[int] = Query(None, description="ID do usuário"),
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"Requisição AQI recebida: lat={lat}, lon={lon}, usuario_id={usuario_id}")

        # Obter AQI da NASA TEMPO
        aqi_original = obter_aqi_nasa_tempo_geo(lat, lon)
        if aqi_original is None:
            logger.error("API NASA TEMPO não retornou dados válidos")
            raise HTTPException(status_code=503, detail="Serviço temporariamente indisponível")

        # Processar AQI personalizado
        aqi_personalizado, nivel_alerta = (
            processar_aqi_para_usuario(db, usuario_id, aqi_original)
            if usuario_id else (aqi_original, "verde")
        )

        # Enviar alerta push se AQI alto
        if aqi_personalizado > 100 and usuario_id:
            try:
                enviar_alerta_push(usuario_id, f"AQI alto ({aqi_personalizado}) na sua localização!")
            except Exception as e:
                logger.error(f"Erro ao enviar alerta push: {e}")

        # Obter dados meteorológicos da OpenWeather
        clima = obter_dados_openweather(lat, lon)

        logger.info(f"Resposta enviada com sucesso: AQI original={aqi_original}, AQI personalizado={aqi_personalizado}")

        return {
            "latitude": lat,
            "longitude": lon,
            "aqi_original": aqi_original,
            "aqi_personalizado": aqi_personalizado,
            "nivel_alerta": nivel_alerta,
            "usuario_id": usuario_id,
            "clima": clima
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro inesperado no endpoint /monitor/aqi: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao processar requisição de qualidade do ar")