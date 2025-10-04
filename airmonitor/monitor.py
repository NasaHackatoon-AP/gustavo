import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENAQ_API = os.getenv("OPENAQ_API")
NASA_API_KEY = os.getenv("NASA_API_KEY")

def obter_aqi_nasa_tempo_geo(lat: float, lon: float, raio_em_metros: int = 5000):
    """
    Consulta AQI da NASA TEMPO usando latitude e longitude.
    """
    try:
               
        headers = {
        "accept": "application/json",
        "X-API-Key": NASA_API_KEY
        }
        params = {
            "coordinates": f"{lat},{lon}",
            "radius": raio_em_metros,
            "limit": 100,
            "order_by": "distance"
            }
        print(f"Buscando estações de qualidade do ar perto de ({lat}, {lon})...")
        resp = requests.get(f"{OPENAQ_API}/locations", headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data
    except Exception as e:
        print(f"Erro ao obter AQI da NASA: {e}")
     
