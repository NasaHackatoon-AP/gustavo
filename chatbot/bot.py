from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime, timedelta
import pandas as pd
import json
import random
from ml.predict import prever_proximos_15_dias
from chatbot.context import ConversaContexto

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

# Função para responder mensagens
def responder(mensagem: str) -> str:
    msg_lower = mensagem.lower()

    # Checa respostas predefinidas
    for intent in INTENTS["intents"]:
        for keyword in intent["keywords"]:
            if keyword in msg_lower:
                resposta = intent["response"]
                contexto.adicionar(mensagem, resposta)
                return resposta

    # Checa se o usuário especificou um local
    if "cidade" in msg_lower or "local" in msg_lower:
        palavras = msg_lower.split()
        local = palavras[-1].capitalize()  # pega última palavra como local
        contexto.definir_local(local)
        resposta = f"Ok, agora estou considerando '{local}' como seu local."
        contexto.adicionar(mensagem, resposta)
        return resposta

    # Perguntas sobre AQI
    if "aqi" in msg_lower or "qualidade do ar" in msg_lower:
        cidade = contexto.obter_local() or "São Paulo"
        df_ultimo_dia = gerar_df_cidade(cidade)
        previsoes = prever_proximos_15_dias(df_ultimo_dia)
        hoje = datetime.now().date()

        # Datas específicas
        if "hoje" in msg_lower:
            for p in previsoes:
                if p["data"] == hoje.strftime("%Y-%m-%d"):
                    resposta = f"Hoje em {cidade} o AQI previsto é {p['aqi_previsto']} ({p['nivel_alerta']})"
                    contexto.adicionar(mensagem, resposta)
                    return resposta
        elif "amanhã" in msg_lower:
            amanha = hoje + timedelta(days=1)
            for p in previsoes:
                if p["data"] == amanha.strftime("%Y-%m-%d"):
                    resposta = f"Amanhã em {cidade} o AQI previsto é {p['aqi_previsto']} ({p['nivel_alerta']})"
                    contexto.adicionar(mensagem, resposta)
                    return resposta
        else:
            # Detecção de datas YYYY-MM-DD
            import re
            match = re.search(r"\d{4}-\d{2}-\d{2}", msg_lower)
            if match:
                data_str = match.group()
                for p in previsoes:
                    if p["data"] == data_str:
                        resposta = f"No dia {data_str} em {cidade}, o AQI previsto é {p['aqi_previsto']} ({p['nivel_alerta']})"
                        contexto.adicionar(mensagem, resposta)
                        return resposta

            # Caso não tenha data, mostra próximos 7 dias
            resposta = f"Previsão de AQI para os próximos dias em {cidade}:\n"
            for p in previsoes[:7]:
                resposta += f"{p['data']}: {p['aqi_previsto']} ({p['nivel_alerta']})\n"
            contexto.adicionar(mensagem, resposta)
            return resposta.strip()

    # Resposta padrão
    resposta = "Desculpe, não entendi. Pode reformular?"
    contexto.adicionar(mensagem, resposta)
    return resposta
