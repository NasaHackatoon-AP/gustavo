import os
import requests
from dotenv import load_dotenv

load_dotenv()

NASA_TEMPO_API = os.getenv("NASA_TEMPO_API")
NASA_API_KEY = os.getenv("NASA_API_KEY")

def obter_aqi_nasa_tempo_geo(lat: float, lon: float):
    """
    Consulta AQI da NASA TEMPO usando latitude e longitude.
    """
    try:
        params = {
            "lat": lat,
            "lon": lon,
            "api_key": NASA_API_KEY
        }
        resp = requests.get(NASA_TEMPO_API, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return int(data.get("aqi", 50))  # fallback padrão
    except Exception as e:
        print(f"Erro ao obter AQI da NASA: {e}")
        return 50
