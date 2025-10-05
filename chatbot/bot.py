from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime, timedelta
import pandas as pd
import json
import random
import os
from typing import Dict, List, Optional
from ml.predict import prever_proximos_15_dias
from chatbot.context import ConversaContexto
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

app = APIRouter()

# Modelo da requisição
class Mensagem(BaseModel):
    texto: str

# Carregar intents
with open("chatbot/intents.json", "r", encoding="utf-8") as f:
    INTENTS = json.load(f)

# Contexto global
contexto = ConversaContexto()

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
        "possui_asma": random.randint(0,1),
        "fumante": random.randint(0,1),
        "sensibilidade_alta": random.randint(0,1),
        "cidade": cidade
    }])

# Obter dados de AQI para contexto
def obter_dados_aqi(cidade: str) -> Dict:
    df_ultimo_dia = gerar_df_cidade(cidade)
    previsoes = prever_proximos_15_dias(df_ultimo_dia)
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
  * Exemplo: "Sou especializado em qualidade do ar e monitoramento de AQI. Posso ajudar você com informações sobre a qualidade do ar na sua cidade, previsões de poluição, níveis de AQI e recomendações de saúde. Como posso ajudar?"
- Seja sempre educado, útil e amigável
"""

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

# Configuração do Gemini
GEMINI_MODEL = None

def configurar_gemini():
    """Configura e retorna modelo do Gemini"""
    try:
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "sua-chave-api-aqui":
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

        return genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config=generation_config,
            safety_settings=safety_settings
        )
    except ImportError:
        print("Erro: google-generativeai não instalado. Execute: pip install google-generativeai")
        return None
    except Exception as e:
        print(f"Erro ao configurar Gemini: {e}")
        return None

def obter_modelo_gemini():
    """Singleton para reutilizar o modelo"""
    global GEMINI_MODEL
    if GEMINI_MODEL is None:
        GEMINI_MODEL = configurar_gemini()
    return GEMINI_MODEL

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
        print(f"Erro ao gerar resposta com Gemini: {e}")
        return "Sistema LLM não configurado. Configure o Gemini para ativar respostas inteligentes."

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

# Função de fallback (lógica atual)
def responder_fallback(mensagem: str) -> str:
    msg_lower = mensagem.lower()

    # Checar intents predefinidos
    for intent in INTENTS["intents"]:
        for keyword in intent["keywords"]:
            if keyword in msg_lower:
                return intent["response"]

    # Perguntas sobre AQI
    if "aqi" in msg_lower or "qualidade do ar" in msg_lower:
        cidade = contexto.obter_local() or "São Paulo"
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

    return "Desculpe, não entendi. Pode reformular?"
