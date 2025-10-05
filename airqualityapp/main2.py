from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import get_db, Base, engine
from .schemas import UsuarioCreate, PerfilSaudeCreate, AQIResponse
from .crud import criar_usuario, criar_perfil_saude, obter_perfil_usuario, salvar_historico
from .utils import calcular_indice_personalizado, ajustar_aqi_com_meteorologia
from .mail_utils import enviar_alerta_email
import requests
import os
from dotenv import load_dotenv
from ml.predict import prever_proximos_15_dias
import pandas as pd
from datetime import datetime
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from chatbot.bot import responder, contexto
import random
import json

load_dotenv()

print("Aplicativo iniciado!")

# Criação das tabelas com retry (aguarda o banco estar pronto)
import time
max_retries = 10
retry_interval = 5

for attempt in range(max_retries):
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tabelas criadas com sucesso!")
        break
    except Exception as e:
        if attempt < max_retries - 1:
            print(f"⏳ Tentativa {attempt + 1}/{max_retries} falhou. Aguardando banco de dados... ({e})")
            time.sleep(retry_interval)
        else:
            print(f"❌ Erro ao conectar ao banco após {max_retries} tentativas: {e}")
            raise

app = APIRouter()

@app.get("/")
def root():
    return JSONResponse(content={
        "mensagem": "🌍 API NASA Air Quality ativa e pronta para previsões 🚀",
        "endpoints": {
            "documentação": "/docs",
            "previsão_15_dias": "/prever_aqi_15_dias"
        }
    })

# APIs
OPENAQ_API = os.getenv("OPENAQ_API")
NASA_API_KEY = os.getenv("NASA_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_API_URL = os.getenv("OPENWEATHER_API_URL")

# Modelo da requisição
class Mensagem(BaseModel):
    texto: str

# Carregar intents com caminho absoluto
import pathlib
base_dir = pathlib.Path(__file__).parent.parent
intents_path = base_dir / "chatbot" / "intents.json"

try:
    with open(intents_path, "r", encoding="utf-8") as f:
        INTENTS = json.load(f)
    print(f"✅ Intents carregados de: {intents_path}")
except FileNotFoundError:
    print(f"⚠️ Arquivo intents.json não encontrado em: {intents_path}")
    INTENTS = {"intents": []}

# Função para gerar df_ultimo_dia simulado por cidade
def gerar_df_cidade(cidade: str):
    hoje = pd.Timestamp.now()
    return pd.DataFrame([{
        "data": hoje,
        "T2M": random.uniform(15, 35),                 # temperatura
        "WS10M": random.uniform(0, 10),               # velocidade do vento
        "ALLSKY_SFC_SW_DWN": random.uniform(100, 300), # radiação solar
        "dia_ano": hoje.timetuple().tm_yday,
        "mes": hoje.month,
        "possui_asma": random.randint(0,1),
        "fumante": random.randint(0,1),
        "sensibilidade_alta": random.randint(0,1),
        "cidade": cidade
    }])

@app.post("/chatbot/")
def chat(mensagem: Mensagem):
    resposta = responder(mensagem.texto, mensagem.usuario_id)
    return {
        "resposta": resposta,
        "local_atual": contexto.obter_local(mensagem.usuario_id),
        "historico": contexto.obter_historico(mensagem.usuario_id)[-5:]  # últimos 5 registros
    }
    
# ----------------------------
# Funções auxiliares
# ----------------------------

def obter_dados_meteorologia(cidade: str):

    try:
        params = {
        "q": cidade,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric"
        }
        resp = requests.get(OPENWEATHER_API_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        return {
            "vento": data.get("wind_speed", 0),
            "umidade": data.get("humidity", 50),
            "temperatura": data.get("temperature", 25)
        }

    except Exception as e:
        print(f"Erro NASA TEMPO: {e}")
        return {
            "vento": 4.5,
            "umidade": 65,
            "temperatura": 28
        }

# ----------------------------
# Endpoints de usuário
# ----------------------------

@app.post("/usuario", summary="Criar novo usuário")
def criar_usuario_endpoint(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    return criar_usuario(db, usuario)

@app.post("/perfil", summary="Criar perfil de saúde")
def criar_perfil_endpoint(perfil: PerfilSaudeCreate, db: Session = Depends(get_db)):
    return criar_perfil_saude(db, perfil)

@app.get("/aqi/previsao/{usuario_id}", summary="Previsão de AQI personalizado para 15 dias")
def previsao_aqi_15_dias(usuario_id: int, db: Session = Depends(get_db)):
    # 1. Busca perfil do usuário
    perfil = obter_perfil_usuario(db, usuario_id)
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil de saúde não encontrado")
    
    df_ultimo_dia = pd.DataFrame([{
        "data": pd.Timestamp.today(),
        "T2M": 25,  # temperatura média
        "WS10M": 5, # vento médio
        "ALLSKY_SFC_SW_DWN": 200, # radiação média
        "possui_asma": int(perfil.possui_asma),
        "fumante": int(perfil.fumante),
        "sensibilidade_alta": int(perfil.sensibilidade_alta)
    }])
    
    if "dia_ano" not in df_ultimo_dia.columns:
        df_ultimo_dia["dia_ano"] = datetime.now().timetuple().tm_yday
    if "mes" not in df_ultimo_dia.columns: 
        df_ultimo_dia["mes"] = datetime.now().month

    # 3. Chama a função de previsão do ML
    previsoes = prever_proximos_15_dias(df_ultimo_dia)

    return {"usuario": perfil.usuario.nome, "previsoes": previsoes}

# ----------------------------
# Endpoint AQI personalizado
# ----------------------------

@app.get("/aqi/{usuario_id}", response_model=AQIResponse, summary="Obter AQI personalizado")
def obter_aqi_personalizado(usuario_id: int, db: Session = Depends(get_db)):
    # Busca perfil do usuário
    perfil = obter_perfil_usuario(db, usuario_id)
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil de saúde não encontrado")

    cidade = perfil.usuario.cidade or "São Paulo"

    # Obter AQI original da OpenAQ
    try:
        headers = {"X-API-Key": NASA_API_KEY}
        params = {"city": cidade}
        resp = requests.get(f"{OPENAQ_API}/locations", params=params, headers=headers )
        dados = resp.json()
        aqi_original = int(dados['results'][0]['measurements'][0]['value'])
    except Exception:
        aqi_original = 50  # valor default se API falhar

    # Calcula AQI personalizado baseado em saúde (passando o objeto PerfilSaude)
    aqi_personalizado, nivel_alerta = calcular_indice_personalizado(aqi_original, perfil)

    # Ajusta AQI com meteorologia real
    meteorologia = obter_dados_meteorologia(cidade)
    aqi_personalizado = ajustar_aqi_com_meteorologia(
        aqi_personalizado,
        meteorologia["vento"],
        meteorologia["umidade"],
        meteorologia["temperatura"]
    )

    # Atualiza nível de alerta baseado em AQI final
    if aqi_personalizado <= 50:
        nivel_alerta = "verde"
    elif aqi_personalizado <= 100:
        nivel_alerta = "amarelo"
    elif aqi_personalizado <= 150:
        nivel_alerta = "laranja"
    else:
        nivel_alerta = "vermelho"

    # Salva histórico no banco
    salvar_historico(db, usuario_id, aqi_original, aqi_personalizado, nivel_alerta)

    # Envia alerta por email se AQI for alto
    if nivel_alerta in ["laranja", "vermelho"]:
        assunto = f"Alerta de qualidade do ar: {nivel_alerta.upper()}"
        mensagem = f"Olá {perfil.usuario.nome}, a qualidade do ar em {cidade} está {nivel_alerta}. AQI personalizado: {aqi_personalizado}"
        enviar_alerta_email(perfil.usuario.email, assunto, mensagem)

    return {
        "aqi_original": aqi_original,
        "aqi_personalizado": aqi_personalizado,
        "nivel_alerta": nivel_alerta
    }
