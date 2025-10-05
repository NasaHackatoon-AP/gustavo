# Exemplo de Integração com Gemini
# Cole este código na função gerar_resposta_llm() do bot.py

"""
PASSO 1: Instalar a biblioteca do Gemini
pip install google-generativeai

PASSO 2: Configurar sua API Key
Obtenha sua chave em: https://makersuite.google.com/app/apikey
"""

import google.generativeai as genai
import os

# Configuração do Gemini (faça isso no início do bot.py)
def configurar_gemini():
    # Opção 1: Variável de ambiente (mais seguro)
    api_key = os.getenv("GEMINI_API_KEY")

    # Opção 2: Hardcoded (apenas para testes)
    # api_key = "sua-api-key-aqui"

    genai.configure(api_key=api_key)

    # Configurações do modelo para respostas baseadas apenas em contexto
    generation_config = {
        "temperature": 0.3,  # Baixa temperatura = mais focado no contexto
        "top_p": 0.8,
        "top_k": 40,
        "max_output_tokens": 1024,
    }

    # Instruções de segurança para não inventar dados
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",  # ou "gemini-1.5-pro" para melhor qualidade
        generation_config=generation_config,
        safety_settings=safety_settings
    )

    return model

# Substitua a função gerar_resposta_llm() no bot.py por esta:
def gerar_resposta_llm(contexto_completo: str) -> str:
    """
    Gera resposta usando Gemini baseado APENAS no contexto fornecido.
    """
    try:
        # Inicializar modelo (você pode fazer isso uma vez no início do arquivo)
        model = configurar_gemini()

        # Gerar resposta
        response = model.generate_content(contexto_completo)

        return response.text

    except Exception as e:
        # Log do erro
        print(f"Erro ao gerar resposta com Gemini: {e}")

        # Retornar mensagem de erro para usar fallback
        return "Sistema LLM não configurado. Configure o Gemini para ativar respostas inteligentes."

# VERSÃO OTIMIZADA: Reutilizar modelo (mais eficiente)
# Adicione no início do bot.py, após as importações:

GEMINI_MODEL = None

def obter_modelo_gemini():
    """Singleton para reutilizar o modelo do Gemini"""
    global GEMINI_MODEL
    if GEMINI_MODEL is None:
        GEMINI_MODEL = configurar_gemini()
    return GEMINI_MODEL

def gerar_resposta_llm_otimizado(contexto_completo: str) -> str:
    """
    Versão otimizada que reutiliza o modelo.
    """
    try:
        model = obter_modelo_gemini()
        response = model.generate_content(contexto_completo)
        return response.text
    except Exception as e:
        print(f"Erro ao gerar resposta com Gemini: {e}")
        return "Sistema LLM não configurado. Configure o Gemini para ativar respostas inteligentes."
