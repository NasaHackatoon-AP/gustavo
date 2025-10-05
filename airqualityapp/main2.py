from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from .database import get_db, Base, engine
from .schemas import UsuarioCreate, PerfilSaudeCreate, AQIResponse, LoginRequest, LoginResponse, UsuarioResponse
from .crud import criar_usuario, criar_perfil_saude, obter_perfil_usuario, salvar_historico, login_usuario, get_current_user
from .utils import calcular_indice_personalizado, ajustar_aqi_com_meteorologia
from .mail_utils import enviar_alerta_email
import requests
import os
from dotenv import load_dotenv
# from ml.predict import prever_proximos_15_dias  # Comentado - caminho incorreto
import pandas as pd
from datetime import datetime
from fastapi.responses import JSONResponse
from pydantic import BaseModel
# from chatbot.bot import responder, contexto  # Comentado - caminho incorreto
import random
import json
from .crud import gerar_token_redefinicao
from .crud import redefinir_senha
from fastapi import FastAPI, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from . import crud
from .database import get_db


load_dotenv()

print("Aplicativo iniciado!")

# Criação das tabelas (executa apenas uma vez)
Base.metadata.create_all(bind=engine)

app = APIRouter()

# Configuração OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/airquality/token")

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

# Carregar intents (comentado - caminho incorreto)
# with open("chatbot/intents.json", "r", encoding="utf-8") as f:
#     INTENTS = json.load(f)
INTENTS = {}  # Placeholder

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
    # Função temporária até corrigir importação
    resposta = f"Chatbot temporariamente indisponível. Mensagem recebida: {mensagem.texto}"
    return {
        "resposta": resposta,
        "local_atual": "Não disponível",
        "historico": []
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

@app.post("/token", response_model=LoginResponse, summary="OAuth2 Token (para Swagger)")
def token_endpoint(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Endpoint OAuth2 para autenticação no Swagger"""
    return login_usuario(db, form_data.username, form_data.password)

@app.post("/login", response_model=LoginResponse, summary="Fazer login (JSON)")
def login_endpoint(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Autentica usuário e retorna token JWT (JSON)"""
    return login_usuario(db, login_data.email, login_data.senha)

@app.get("/me", response_model=UsuarioResponse, summary="Obter perfil do usuário logado")
def get_me_endpoint(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Retorna dados do usuário autenticado"""
    return get_current_user(db, token)

@app.post("/perfil", summary="Criar perfil de saúde")
def criar_perfil_endpoint(perfil: PerfilSaudeCreate, db: Session = Depends(get_db)):
    return criar_perfil_saude(db, perfil)

# ----------------------------
# Recuperação de senha
# ----------------------------

@app.post("/forgot-password", summary="Gerar link de redefinição de senha")
def forgot_password(email: str = Form(...), db: Session = Depends(get_db)):
    """
    Gera um token de redefinição de senha (expira em 15 minutos)
    e envia um link por e-mail ao usuário.
    """
    return gerar_token_redefinicao(db, email)

@app.post("/reset-password", summary="Redefinir senha com token de verificação")
def reset_password(
    token: str = Form(...),
    nova_senha: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Permite redefinir a senha de um usuário com base no token enviado por e-mail.
    """
    return redefinir_senha(db, token, nova_senha)

# ----------------------------
# Deletar usuário
# ----------------------------

@app.delete("/delete-account")
def delete_account(
    email: str = Form(...),
    senha: str = Form(...),
    db: Session = Depends(get_db)
):
    """Deleta conta do usuário após verificar credenciais"""
    return crud.deletar_usuario(db, email, senha)

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

    # 3. Chama a função de previsão do ML (temporariamente desabilitada)
    # previsoes = prever_proximos_15_dias(df_ultimo_dia)
    previsoes = {"mensagem": "Previsão temporariamente indisponível - importação ML corrigir"}

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
        
        # Tentar enviar e-mail, mas não falhar se não conseguir
        try:
            enviar_alerta_email(perfil.usuario.email, assunto, mensagem)
        except Exception as e:
            print(f"⚠️ Aviso: Não foi possível enviar alerta por e-mail: {e}")
            # Continuar mesmo se e-mail falhar

    return {
        "aqi_original": aqi_original,
        "aqi_personalizado": aqi_personalizado,
        "nivel_alerta": nivel_alerta
    }
