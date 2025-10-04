import requests
from datetime import datetime, timedelta
import os

# ================================
# CONFIGURAÇÃO
# ================================
EARTHDATA_TOKEN = os.getenv("NASA_TEMPO_API")  # seu token no .env
LATITUDE = -23.55
LONGITUDE = -46.63
PARAMETERS = "T2M,WS10M"  # Temperatura e Velocidade do vento
FORMAT = "JSON"

# Ajusta datas: últimos 7 dias
END_DATE = datetime.today()
START_DATE = END_DATE - timedelta(days=6)
start_str = START_DATE.strftime("%Y%m%d")
end_str = END_DATE.strftime("%Y%m%d")

# Monta URL da API
url = (
    f"https://power.larc.nasa.gov/api/temporal/daily/point"
    f"?start={start_str}&end={end_str}"
    f"&latitude={LATITUDE}&longitude={LONGITUDE}"
    f"&parameters={PARAMETERS}&format={FORMAT}"
)

# ================================
# REQUISIÇÃO COM TOKEN
# ================================
headers = {
    "Authorization": f"Bearer {EARTHDATA_TOKEN}"
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()  # levanta erro se não for 200
    data = response.json()
    print("✅ Conexão OK! Status:", response.status_code)
    print("Conteúdo do dataset (resumido):")
    # Mostra apenas os primeiros dias para não poluir a tela
    for dia, valores in list(data['properties']['parameter']['T2M'].items())[0:5]:
        temp = valores
        vento = data['properties']['parameter']['WS10M'][dia]
        print(f"{dia} -> Temperatura: {temp}°C, Vento: {vento} m/s")

except requests.exceptions.HTTPError as e:
    print(f"Erro HTTP: {e}")
except Exception as e:
    print(f"Erro geral: {e}")