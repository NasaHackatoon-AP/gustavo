from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import get_db, Base, engine
from .schemas import UsuarioCreate, PerfilSaudeCreate, AQIResponse
from .crud import criar_usuario, criar_perfil_saude, obter_perfil_usuario, salvar_historico
from .utils import calcular_indice_personalizado, ajustar_aqi_com_meteorologia
from .mail_utils import enviar_alerta_email
import requests
import os
from dotenv import load_dotenv

load_dotenv()

print("Aplicativo iniciado!")

# Criação das tabelas (executa apenas uma vez)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Air Quality App - Parte 1")

# APIs
OPENAQ_API = os.getenv("OPENAQ_API")
NASA_TEMPO_API = os.getenv("NASA_TEMPO_API")
NASA_API_KEY = os.getenv("NASA_API_KEY")

# ----------------------------
# Funções auxiliares
# ----------------------------

def obter_dados_meteorologia(cidade: str):
    """
    Busca dados meteorológicos em tempo real via NASA TEMPO.
    """
    try:
        params = {
            "city": cidade,
            "api_key": NASA_API_KEY
        }
        resp = requests.get(NASA_TEMPO_API, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # Ajuste de acordo com o formato real do JSON da NASA TEMPO
        vento = data.get("wind_speed", 0)
        umidade = data.get("humidity", 50)
        temperatura = data.get("temperature", 25)

        return {
            "vento": vento,
            "umidade": umidade,
            "temperatura": temperatura
        }

    except Exception as e:
        print(f"Erro NASA TEMPO: {e}")
        # fallback para valores padrão se API falhar
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
        resp = requests.get(f"{OPENAQ_API}?city={cidade}&limit=1")
        dados = resp.json()
        aqi_original = int(dados['results'][0]['measurements'][0]['value'])
    except:
        aqi_original = 50  # valor default se API falhar

    # Monta dicionário do perfil
    perfil_dict = {
        "possui_asma": perfil.possui_asma,
        "possui_dpoc": perfil.possui_dpoc,
        "possui_alergias": perfil.possui_alergias,
        "fumante": perfil.fumante,
        "sensibilidade_alta": perfil.sensibilidade_alta
    }

    # Calcula AQI personalizado baseado em saúde
    aqi_personalizado, nivel_alerta = calcular_indice_personalizado(aqi_original, perfil_dict)

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