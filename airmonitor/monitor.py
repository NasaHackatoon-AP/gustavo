import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

OPENAQ_API = os.getenv("OPENAQ_API")
NASA_API_KEY = os.getenv("NASA_API_KEY")

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def obter_aqi_nasa_tempo_geo(lat: float, lon: float, raio_em_metros: int = 25000):
    """
    Consulta AQI da NASA TEMPO usando latitude e longitude.
    Retorna um valor numérico de AQI ou None se houver erro.
    """
    try:
        headers = {
            "accept": "application/json",
            "X-API-Key": NASA_API_KEY
        }

        # Garantir que coordinates está no formato correto
        coordinates = f"{lat},{lon}"

        # Garantir que radius é numérico (OpenAQ aceita até 100000m = 100km)
        raio_valido = min(int(raio_em_metros), 100000)

        params = {
            "coordinates": coordinates,
            "radius": raio_valido,
            "limit": 10
        }

        logger.info(f"Buscando estações de qualidade do ar perto de ({lat}, {lon}) com raio {raio_valido}m...")

        resp = requests.get(f"{OPENAQ_API}/locations", headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        num_results = len(data.get("results", []))
        logger.info(f"API retornou {num_results} estações")

        # Extrair valor AQI da resposta
        if "results" in data and num_results > 0:
            # Tentar encontrar PM2.5 em qualquer estação retornada
            for idx, location in enumerate(data["results"]):
                location_name = location.get("name", "Unknown")
                measurements = location.get("measurements", [])

                logger.info(f"Estação {idx+1}: {location_name} - {len(measurements)} medições")

                if len(measurements) > 0:
                    # Extrair PM2.5 que é o principal indicador de AQI
                    for measurement in measurements:
                        param = measurement.get("parameter")
                        if param in ["pm25", "pm2.5"]:
                            value = measurement.get("value")
                            if value is not None:
                                # Converter PM2.5 em AQI
                                aqi = pm25_to_aqi(value)
                                logger.info(f"✓ PM2.5 encontrado na estação '{location_name}': {value} µg/m³ → AQI {aqi}")
                                return aqi

            # Se não encontrar PM2.5, tentar outros poluentes
            logger.warning("PM2.5 não encontrado, tentando outros poluentes...")
            for location in data["results"]:
                measurements = location.get("measurements", [])
                for measurement in measurements:
                    param = measurement.get("parameter")
                    value = measurement.get("value")
                    if param in ["pm10", "no2", "o3", "so2", "co"] and value is not None:
                        logger.info(f"Usando {param}: {value}")
                        # Conversão simplificada (não é ideal, mas evita fallback)
                        return min(int(value), 200)

            logger.warning("Nenhum poluente mensurável encontrado")
            return 50

        logger.warning("Nenhuma estação encontrada próxima às coordenadas")
        return 50

    except requests.exceptions.HTTPError as e:
        logger.error(f"Erro HTTP ao obter AQI da NASA: {e}")
        logger.error(f"Status code: {e.response.status_code}")
        logger.error(f"Response: {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro de requisição ao obter AQI da NASA: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao obter AQI da NASA: {e}")
        return None


def pm25_to_aqi(pm25):
    """
    Converte concentração de PM2.5 (µg/m³) para AQI usando a fórmula padrão EPA.
    """
    if pm25 <= 12.0:
        return int((50 - 0) / (12.0 - 0) * (pm25 - 0) + 0)
    elif pm25 <= 35.4:
        return int((100 - 51) / (35.4 - 12.1) * (pm25 - 12.1) + 51)
    elif pm25 <= 55.4:
        return int((150 - 101) / (55.4 - 35.5) * (pm25 - 35.5) + 101)
    elif pm25 <= 150.4:
        return int((200 - 151) / (150.4 - 55.5) * (pm25 - 55.5) + 151)
    elif pm25 <= 250.4:
        return int((300 - 201) / (250.4 - 150.5) * (pm25 - 150.5) + 201)
    elif pm25 <= 350.4:
        return int((400 - 301) / (350.4 - 250.5) * (pm25 - 250.5) + 301)
    else:
        return int((500 - 401) / (500.4 - 350.5) * (pm25 - 350.5) + 401)

