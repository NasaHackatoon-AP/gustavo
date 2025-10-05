from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import requests
import numpy as np
import joblib
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Air Quality Monitor")

# Carregar modelo fake
modelo = joblib.load("ml/modelo_aqi.pkl")

# Exemplo de "usuários" fictício
USUARIOS = {
    1: {"possui_asma": 1, "fumante": 0, "sensibilidade_alta": 1},
    2: {"possui_asma": 0, "fumante": 1, "sensibilidade_alta": 0},
}

class AQIResponse(BaseModel):
    aqi_original: float
    aqi_personalizado: float

@app.get("/airmonitor/monitor/aqi", response_model=AQIResponse)
def obter_aqi(
    lat: float = Query(..., description="Latitude do local"),
    lon: float = Query(..., description="Longitude do local"),
    usuario_id: int = Query(..., description="ID do usuário")
):
    # Buscar dados do usuário
    usuario = USUARIOS.get(usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Consultar API OpenAQ
    try:
        url = "https://api.openaq.org/v3/locations"
        params = {
            "coordinates": f"{lat},{lon}",
            "radius": 25000,  # Aumentar raio para 25km
            "limit": 10
        }
        logger.info(f"Buscando dados OpenAQ para coordenadas: {lat},{lon} com raio 25km")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        logger.info(f"Resposta OpenAQ: {len(data.get('results', []))} estações encontradas")

        if "results" not in data or len(data["results"]) == 0:
            logger.warning("Nenhuma estação encontrada próxima às coordenadas")
            aqi_original = 50  # fallback default
        else:
            # Pegar medições da estação mais próxima
            aqi_original = 50  # default

            for location in data["results"]:
                location_name = location.get("name", "Unknown")
                measurements = location.get("measurements", [])

                logger.info(f"Estação: {location_name} - {len(measurements)} medições")

                # Procurar PM2.5
                for measurement in measurements:
                    param = measurement.get("parameter")
                    if param in ["pm25", "pm2.5"]:
                        value = measurement.get("value")
                        logger.info(f"PM2.5 encontrado na estação {location_name}: {value}")

                        if value is not None:
                            # Converter PM2.5 para AQI (simplificado)
                            if value <= 12.0:
                                aqi_original = int((50 / 12.0) * value)
                            elif value <= 35.4:
                                aqi_original = int(51 + ((100 - 51) / (35.4 - 12.1)) * (value - 12.1))
                            elif value <= 55.4:
                                aqi_original = int(101 + ((150 - 101) / (55.4 - 35.5)) * (value - 35.5))
                            else:
                                aqi_original = int(151 + ((200 - 151) / (150.4 - 55.5)) * min(value - 55.5, 95))

                            logger.info(f"AQI calculado: {aqi_original} (PM2.5: {value})")
                            break

                if aqi_original != 50:  # Se encontrou dados, parar de procurar
                    break

            if aqi_original == 50:
                logger.warning("PM2.5 não encontrado em nenhuma estação, usando fallback")

    except Exception as e:
        logger.error(f"Erro ao consultar OpenAQ: {e}")
        aqi_original = 50  # fallback caso API falhe

    # Criar features para o modelo fake
    now = datetime.utcnow()
    dia_ano = now.timetuple().tm_yday
    mes = now.month
    
    # Features: ["T2M", "WS10M", "ALLSKY_SFC_SW_DWN", "dia_ano", "mes", "possui_asma", "fumante", "sensibilidade_alta"]
    # Como não temos dados reais de T2M, WS10M e ALLSKY, vamos usar placeholders
    features = np.array([[
        aqi_original,       # T2M aproximado
        5.0,                # WS10M placeholder
        80.0,               # ALLSKY placeholder
        dia_ano,
        mes,
        usuario["possui_asma"],
        usuario["fumante"],
        usuario["sensibilidade_alta"]
    ]])

    # Calcular AQI personalizado
    aqi_personalizado = float(modelo.predict(features)[0])

    return AQIResponse(aqi_original=aqi_original, aqi_personalizado=aqi_personalizado)
