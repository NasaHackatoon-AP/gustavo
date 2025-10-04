from fastapi import FastAPI, Query, HTTPException
from typing import Optional
import requests
import os
from dotenv import load_dotenv

# 🔹 Carrega variáveis do .env
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=dotenv_path)

API_KEY = os.getenv("OPENAQ_API_KEY")

if not API_KEY:
    print("⚠️ Aviso: Chave API não encontrada no .env. Alguns endpoints podem exigir autenticação.")

# 🔹 URL base da OpenAQ v3
BASE_URL = "https://api.openaq.org/v3"

# 🔹 Cria a aplicação FastAPI
app = FastAPI(
    title="API OpenAQ v3 com Swagger",
    description="Consulta dados da qualidade do ar usando a OpenAQ API v3",
    version="1.0.0"
)

# 🌍 Rota raiz
@app.get("/")
def home():
    return {"mensagem": "Bem-vindo à API OpenAQ v3 com Swagger!"}

# 📊 Rota para buscar medições de qualidade do ar
@app.get("/medicoes", summary="Buscar medições de qualidade do ar")
def obter_medicoes(
    cidade: Optional[str] = Query(None, description="Nome da cidade para filtrar"),
    parametro: Optional[str] = Query(None, description="Parâmetro de medição, ex: pm25, pm10, o3"),
    limite: int = Query(5, description="Número máximo de resultados")
):
    url = f"{BASE_URL}/measurements"
    
    # Se houver chave API, envia no header
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    
    params = {"limit": limite}
    if cidade:
        params["city"] = cidade
    if parametro:
        params["parameter"] = parametro

    resposta = requests.get(url, headers=headers, params=params)

    if resposta.status_code != 200:
        raise HTTPException(status_code=resposta.status_code, detail=resposta.text)

    return resposta.json()

# 🌆 Rota para listar cidades disponíveis
@app.get("/cidades", summary="Listar cidades com medições disponíveis")
def listar_cidades(limite: int = Query(10, description="Número de cidades a retornar")):
    url = f"{BASE_URL}/cities"
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    params = {"limit": limite}

    resposta = requests.get(url, headers=headers, params=params)

    if resposta.status_code != 200:
        raise HTTPException(status_code=resposta.status_code, detail=resposta.text)

    return resposta.json()

# 🏭 Rota para listar locais/estações de medição
@app.get("/locais", summary="Listar estações de medição disponíveis")
def listar_locais(
    cidade: Optional[str] = Query(None, description="Nome da cidade para filtrar"),
    limite: int = Query(10, description="Número máximo de locais a retornar")
):
    url = f"{BASE_URL}/locations"
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    params = {"limit": limite}
    if cidade:
        params["city"] = cidade

    resposta = requests.get(url, headers=headers, params=params)

    if resposta.status_code != 200:
        raise HTTPException(status_code=resposta.status_code, detail=resposta.text)

    return resposta.json()