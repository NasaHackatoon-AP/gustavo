from fastapi import APIRouter, Depends, HTTPException, Form
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
from ml.predict import prever_proximos_15_dias
import pandas as pd
from datetime import datetime, timedelta
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from chatbot.context import ConversaContexto
import random
import json
from .crud import gerar_token_redefinicao
from .crud import redefinir_senha
from . import crud
from typing import Dict, List, Optional

# Carregar variáveis de ambiente
load_dotenv()

print("Aplicativo iniciado!")

# Criação das tabelas (executa apenas uma vez)
Base.metadata.create_all(bind=engine)

app = APIRouter()

# Configuração OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/airquality/token")

# APIs
OPENAQ_API = os.getenv("OPENAQ_API")
NASA_API_KEY = os.getenv("NASA_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_API_URL = os.getenv("OPENWEATHER_API_URL")

# =============================================================================
# CONFIGURAÇÃO DO CHATBOT
# =============================================================================

# Modelo da requisição do chatbot
class Mensagem(BaseModel):
    texto: str
    
class AQIResponse(BaseModel):
    aqi_original: int
    aqi_personalizado: int
    nivel_alerta: str
    
class PrevisaoDia(BaseModel):
    data: str
    aqi_previsto: int
    nivel_alerta: str

class PrevisaoAQIResponse(BaseModel):
    usuario: str
    previsoes: List[PrevisaoDia]

# Carregar intents
intents_path = os.path.join(os.path.dirname(__file__), "..", "chatbot", "intents.json")
try:
    with open(intents_path, "r", encoding="utf-8") as f:
        INTENTS = json.load(f)
except FileNotFoundError:
    print(f"⚠️ Arquivo intents.json não encontrado em: {intents_path}")
    INTENTS = {"intents": []}

# Contexto global do chatbot
contexto = ConversaContexto()

# Prompt do Sistema
PROMPT_SISTEMA = """Você é o assistente virtual do projeto AURA AIR - um sistema de monitoramento e previsão de qualidade do ar.

VOÇE DEVE PRICIPALMENTE EVITAR RESPOSTAS DUPLICADAS!

SOBRE O PROJETO AURA AIR:
O AURA AIR é uma plataforma que monitora e prevê a qualidade do ar (AQI - Air Quality Index) em diferentes cidades usando:
- Dados meteorológicos da NASA
- Algoritmos de Machine Learning (XGBoost)
- Monitoramento de poluentes atmosféricos
- Previsões de AQI para os próximos 15 dias

SUAS RESPONSABILIDADES:
1. Responder APENAS sobre qualidade do ar, AQI, poluição e tópicos relacionados
2. Fornecer informações baseadas SOMENTE nos dados que você recebe
3. Ajudar usuários a entender os níveis de AQI e alertas
4. Ser amigável e prestativo
5. Deve falar Olá apenas na primeira interação
6. deve responder na linguagem que o usuário utilizar

O QUE VOCÊ PODE AJUDAR:
✅ Qualidade do ar (AQI) em diferentes cidades
✅ Previsões de AQI para os próximos dias
✅ Explicar níveis de alerta e o que significam
✅ Impactos da poluição na saúde
✅ Dados meteorológicos relacionados à qualidade do ar
✅ Recomendações baseadas no nível de AQI

NÍVEIS DE AQI:
- 0-50: Bom (Verde) - Qualidade do ar satisfatória
- 51-100: Moderado (Amarelo) - Aceitável para a maioria
- 101-150: Não saudável para grupos sensíveis (Laranja) - Pode afetar pessoas com problemas respiratórios
- 151-200: Não saudável (Vermelho) - Todos podem começar a sentir efeitos na saúde
- 201-300: Muito não saudável (Roxo) - Alerta de saúde, todos podem ter efeitos mais sérios
- 301+: Perigoso (Marrom) - Emergência de saúde

REGRAS IMPORTANTES:
- NUNCA invente dados ou previsões
- Se não tiver dados suficientes, informe o usuário claramente
- Se a pergunta NÃO for sobre qualidade do ar ou tópicos relacionados:
  * Informe educadamente que você é especializado em qualidade do ar
  * Sugira tópicos sobre os quais você pode ajudar
"""

# Configuração do Gemini
GEMINI_MODEL = None

def configurar_gemini():
    """Configura e retorna modelo do Gemini"""
    try:
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "sua-chave-api-aqui":
            print("⚠️ GEMINI_API_KEY não configurada no .env")
            return None

        genai.configure(api_key=api_key)

        generation_config = {
            "temperature": 0.3,  # Baixa temperatura = mais focado no contexto
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 1024,
        }

        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]

        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        print("✅ Gemini configurado com sucesso!")
        return model
        
    except ImportError:
        print("❌ Erro: google-generativeai não instalado. Execute: pip install google-generativeai")
        return None
    except Exception as e:
        print(f"❌ Erro ao configurar Gemini: {e}")
        return None

def obter_modelo_gemini():
    """Singleton para reutilizar o modelo"""
    global GEMINI_MODEL
    if GEMINI_MODEL is None:
        GEMINI_MODEL = configurar_gemini()
    return GEMINI_MODEL

# Função para gerar df_ultimo_dia simulado por cidade
def gerar_df_cidade(cidade: str):
    hoje = pd.Timestamp.now()
    return pd.DataFrame([{
        "data": hoje,
        "T2M": random.uniform(15, 35),
        "WS10M": random.uniform(0, 10),
        "ALLSKY_SFC_SW_DWN": random.uniform(100, 300),
        "dia_ano": hoje.timetuple().tm_yday,
        "mes": hoje.month,
        "possui_asma": random.randint(0, 1),
        "fumante": random.randint(0, 1),
        "sensibilidade_alta": random.randint(0, 1),
        "cidade": cidade
    }])

# Obter dados de AQI para contexto
def obter_dados_aqi(cidade: str) -> Dict:
    df_ultimo_dia = gerar_df_cidade(cidade)
    try:
        previsoes = prever_proximos_15_dias(df_ultimo_dia)
    except Exception as e:
        print(f"⚠️ Erro ao obter previsões: {e}")
        previsoes = []
    
    return {
        "cidade": cidade,
        "previsoes": previsoes,
        "dados_atuais": df_ultimo_dia.to_dict('records')[0]
    }

# Extrair informações relevantes da mensagem
def extrair_contexto_mensagem(mensagem: str) -> Dict:
    msg_lower = mensagem.lower()
    hoje = datetime.now().date()

    contexto_msg = {
        "menciona_aqi": "aqi" in msg_lower or "qualidade do ar" in msg_lower or "poluição" in msg_lower,
        "menciona_local": "cidade" in msg_lower or "local" in msg_lower,
        "data_referencia": None,
        "periodo": None
    }

    # Detectar data específica
    if "hoje" in msg_lower:
        contexto_msg["data_referencia"] = hoje.strftime("%Y-%m-%d")
        contexto_msg["periodo"] = "hoje"
    elif "amanhã" in msg_lower:
        amanha = hoje + timedelta(days=1)
        contexto_msg["data_referencia"] = amanha.strftime("%Y-%m-%d")
        contexto_msg["periodo"] = "amanhã"
    else:
        import re
        match = re.search(r"\d{4}-\d{2}-\d{2}", msg_lower)
        if match:
            contexto_msg["data_referencia"] = match.group()
            contexto_msg["periodo"] = "data_especifica"

    return contexto_msg

# Construir contexto completo para LLM
def construir_contexto_llm(mensagem: str) -> str:
    cidade = contexto.obter_local() or "São Paulo"
    historico = contexto.obter_historico()
    ctx_msg = extrair_contexto_mensagem(mensagem)

    # Montar contexto base
    contexto_texto = PROMPT_SISTEMA + f"""

LOCALIZAÇÃO ATUAL: {cidade}

HISTÓRICO DA CONVERSA:
"""

    # Adicionar histórico
    for item in historico[-5:]:  # Últimas 5 mensagens
        contexto_texto += f"Usuário: {item['usuario']}\nAssistente: {item['bot']}\n"

    # Adicionar dados de AQI se relevante
    if ctx_msg["menciona_aqi"]:
        try:
            dados_aqi = obter_dados_aqi(cidade)
            contexto_texto += f"\nDADOS DE QUALIDADE DO AR - {cidade}:\n"

            if ctx_msg["data_referencia"]:
                # Buscar previsão específica
                for p in dados_aqi["previsoes"]:
                    if p["data"] == ctx_msg["data_referencia"]:
                        contexto_texto += f"Data: {p['data']}\n"
                        contexto_texto += f"AQI Previsto: {p['aqi_previsto']}\n"
                        contexto_texto += f"Nível de Alerta: {p['nivel_alerta']}\n"
                        break
            else:
                # Mostrar próximos 7 dias
                contexto_texto += "Previsões para os próximos 7 dias:\n"
                for p in dados_aqi["previsoes"][:7]:
                    contexto_texto += f"- {p['data']}: AQI {p['aqi_previsto']} ({p['nivel_alerta']})\n"
        except FileNotFoundError:
            contexto_texto += f"\n[NOTA: Modelo de previsão não disponível. Informe ao usuário que o sistema está em manutenção.]\n"
        except Exception as e:
            contexto_texto += f"\n[NOTA: Erro ao obter previsões. Informe ao usuário que os dados não estão disponíveis no momento.]\n"

    contexto_texto += f"\nPERGUNTA ATUAL: {mensagem}\n"
    contexto_texto += "\nINSTRUÇÕES: Responda APENAS com base nos dados acima. Não invente informações. Se não tiver dados suficientes, informe o usuário."

    return contexto_texto

# Função para gerar resposta com LLM (Gemini)
def gerar_resposta_llm(contexto_completo: str) -> str:
    """
    Gera resposta usando Gemini baseado APENAS no contexto fornecido.
    """
    try:
        model = obter_modelo_gemini()
        if model is None:
            return "Sistema LLM não configurado. Configure o Gemini para ativar respostas inteligentes."

        response = model.generate_content(contexto_completo)
        return response.text

    except Exception as e:
        print(f"❌ Erro ao gerar resposta com Gemini: {e}")
        return "Sistema LLM não configurado. Configure o Gemini para ativar respostas inteligentes."

# Função de fallback (lógica atual)
def responder_fallback(mensagem: str) -> str:
    msg_lower = mensagem.lower()

    # Checar intents predefinidos
    for intent in INTENTS.get("intents", []):
        for keyword in intent.get("keywords", []):
            if keyword in msg_lower:
                return intent.get("response", "Desculpe, não entendi.")

    # Perguntas sobre AQI
    if "aqi" in msg_lower or "qualidade do ar" in msg_lower:
        cidade = contexto.obter_local() or "São Paulo"
        try:
            dados_aqi = obter_dados_aqi(cidade)
            previsoes = dados_aqi["previsoes"]
            hoje = datetime.now().date()

            if "hoje" in msg_lower:
                for p in previsoes:
                    if p["data"] == hoje.strftime("%Y-%m-%d"):
                        return f"Hoje em {cidade} o AQI previsto é {p['aqi_previsto']} ({p['nivel_alerta']})"

            elif "amanhã" in msg_lower:
                amanha = hoje + timedelta(days=1)
                for p in previsoes:
                    if p["data"] == amanha.strftime("%Y-%m-%d"):
                        return f"Amanhã em {cidade} o AQI previsto é {p['aqi_previsto']} ({p['nivel_alerta']})"

            else:
                import re
                match = re.search(r"\d{4}-\d{2}-\d{2}", msg_lower)
                if match:
                    data_str = match.group()
                    for p in previsoes:
                        if p["data"] == data_str:
                            return f"No dia {data_str} em {cidade}, o AQI previsto é {p['aqi_previsto']} ({p['nivel_alerta']})"

                resposta = f"Previsão de AQI para os próximos dias em {cidade}:\n"
                for p in previsoes[:7]:
                    resposta += f"{p['data']}: {p['aqi_previsto']} ({p['nivel_alerta']})\n"
                return resposta.strip()
        except Exception as e:
            print(f"⚠️ Erro no fallback: {e}")
            return f"Desculpe, não consegui obter os dados de AQI para {cidade} no momento."

    return "Desculpe, não entendi. Pode reformular?"

# Função principal de resposta
def responder(mensagem: str) -> str:
    msg_lower = mensagem.lower()

    # 1. Checar se é definição de local
    if "cidade" in msg_lower or "local" in msg_lower:
        palavras = msg_lower.split()
        local = palavras[-1].capitalize()
        contexto.definir_local(local)
        resposta = f"Ok, agora estou considerando '{local}' como seu local."
        contexto.adicionar(mensagem, resposta)
        return resposta

    # 2. Construir contexto completo
    contexto_completo = construir_contexto_llm(mensagem)

    # 3. Gerar resposta com LLM (preparado para Gemini)
    resposta = gerar_resposta_llm(contexto_completo)

    # 4. Se LLM não estiver configurado, usar lógica de fallback
    if "não configurado" in resposta:
        resposta = responder_fallback(mensagem)

    # 5. Salvar no contexto
    contexto.adicionar(mensagem, resposta)
    return resposta

# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/")
def root():
    return JSONResponse(content={
        "mensagem": "🌍 API NASA Air Quality ativa e pronta para previsões 🚀",
        "endpoints": {
            "documentação": "/docs",
            "previsão_15_dias": "/prever_aqi_15_dias",
            "chatbot": "/chatbot/"
        }
    })

# =============================================================================
# ENDPOINT DO CHATBOT
# =============================================================================

@app.post("/chatbot/")
def chat(mensagem: Mensagem):
    """
    Endpoint do chatbot com integração Gemini.
    Responde perguntas sobre qualidade do ar, AQI e tópicos relacionados.
    """
    try:
        resposta_texto = responder(mensagem.texto)
        
        return {
            "resposta": resposta_texto,
            "local_atual": contexto.obter_local() or "São Paulo",
            "historico": contexto.obter_historico()[-5:]  # Últimas 5 mensagens
        }
    except Exception as e:
        print(f"❌ Erro no chatbot: {e}")
        return {
            "resposta": "Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente.",
            "local_atual": contexto.obter_local() or "São Paulo",
            "historico": []
        }

# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

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

# =============================================================================
# ENDPOINTS DE USUÁRIO
# =============================================================================

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

# =============================================================================
# RECUPERAÇÃO DE SENHA
# =============================================================================

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

# =============================================================================
# DELETAR USUÁRIO
# =============================================================================

@app.delete("/delete-account")
def delete_account(
    email: str = Form(...),
    senha: str = Form(...),
    db: Session = Depends(get_db)
):
    """Deleta conta do usuário após verificar credenciais"""
    return crud.deletar_usuario(db, email, senha)

# =============================================================================
# PREVISÃO DE AQI
# =============================================================================

@app.get("/aqi/previsao/{usuario_id}", response_model=PrevisaoAQIResponse, summary="Previsão de AQI personalizado para 15 dias")
def previsao_aqi_15_dias(usuario_id: int, db: Session = Depends(get_db)):
    # 1. Busca perfil do usuário
    perfil = obter_perfil_usuario(db, usuario_id)
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil de saúde não encontrado")
    
    # 2. Criar DataFrame com dados do usuário
    df_ultimo_dia = pd.DataFrame([{
        "data": pd.Timestamp.today(),
        "T2M": 25,  # temperatura média
        "WS10M": 5,  # vento médio
        "ALLSKY_SFC_SW_DWN": 200,  # radiação média
        "possui_asma": int(perfil.possui_asma),
        "fumante": int(perfil.fumante),
        "sensibilidade_alta": int(perfil.sensibilidade_alta),
        "dia_ano": datetime.now().timetuple().tm_yday,
        "mes": datetime.now().month
    }])
    
    # 3. Chama a função de previsão do ML
    try:
        previsoes_raw = prever_proximos_15_dias(df_ultimo_dia)
    except Exception as e:
        print(f"⚠️ Erro na previsão: {e}")
        previsoes_raw = []

    # 4. Converter previsões para objetos Pydantic
    previsoes = []
    for p in previsoes_raw:
        previsoes.append(PrevisaoDia(
            data=p.get("data", ""),
            aqi_previsto=int(p.get("aqi_previsto", 0)),
            nivel_alerta=p.get("nivel_alerta", "desconhecido")
        ))

    # 5. Retornar objeto Pydantic completo
    return PrevisaoAQIResponse(
        usuario=perfil.usuario.nome,
        previsoes=previsoes
    )

# =============================================================================
# ENDPOINT AQI PERSONALIZADO
# =============================================================================

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
        resp = requests.get(f"{OPENAQ_API}/locations", params=params, headers=headers)
        dados = resp.json()
        aqi_original = int(dados['results'][0]['measurements'][0]['value'])
    except Exception:
        aqi_original = 50  # valor default se API falhar

    # Calcula AQI personalizado
    aqi_personalizado, nivel_alerta = calcular_indice_personalizado(aqi_original, perfil)

    # Ajusta AQI com meteorologia
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
        mensagem_email = f"Olá {perfil.usuario.nome}, a qualidade do ar em {cidade} está {nivel_alerta}. AQI personalizado: {aqi_personalizado}"
        try:
            enviar_alerta_email(perfil.usuario.email, assunto, mensagem_email)
        except Exception as e:
            print(f"⚠️ Aviso: Não foi possível enviar alerta por e-mail: {e}")

    # Retorna *objeto Pydantic*, que será convertido automaticamente em JSON
    return AQIResponse(
        aqi_original=int(aqi_original),
        aqi_personalizado=int(aqi_personalizado),
        nivel_alerta=nivel_alerta
    )