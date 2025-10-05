import random
import os
from datetime import datetime, timedelta

# ==============================
# 🔐 Configurações de segurança
# ==============================
SECRET_KEY = os.getenv("SECRET_KEY", "chave_super_secreta_trocar_em_producao")
ALGORITHM = "HS256"

# ==============================
# ✉️ Envio de e-mail (delegado para mail_utils.py)
# ==============================

# ==============================
# 🔑 Segurança e autenticação
# ==============================
from passlib.context import CryptContext

# CryptContext para bcrypt (padrão moderno)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_senha_bcrypt(senha: str) -> str:
    """Gera hash bcrypt (usa truncamento para 72 bytes)."""
    return pwd_context.hash(senha[:72])

# compatibilidade com o hash antigo "HASH_<senha>"
def hash_senha_legacy(senha: str) -> str:
    return "HASH_" + senha

def hash_senha(senha: str) -> str:
    """
    Função pública para criar hash de senha.
    -> Usa bcrypt para novas senhas (recomendado).
    """
    return hash_senha_bcrypt(senha)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica senha com suporte a:
      - formatos bcrypt (recomendado)
      - formato legado "HASH_<senha>" (compatibilidade)
    """
    if hashed_password is None:
        return False

    # Legado: se armazenou como "HASH_<senha>"
    if isinstance(hashed_password, str) and hashed_password.startswith("HASH_"):
        return hashed_password == hash_senha_legacy(plain_password)

    # Caso normal: bcrypt (ou outros suportados pelo pwd_context)
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # se o formato do hash for desconhecido, retorna False
        return False

# Funções JWT removidas - usando tokens seguros no CRUD

# ==============================
# 🌦️ Simulações de dados locais
# ==============================
def obter_dados_tempo(lat, lon):
    # Substitua por API NASA TEMPO
    return {"pm2_5": random.randint(10, 200)}

def obter_dados_meteorologia(lat, lon):
    # Substitua por API real
    return {
        "vento": random.uniform(0, 10),
        "umidade": random.uniform(20, 90),
        "temperatura": random.uniform(15, 35)
    }

# ==============================
# 📊 Cálculos de qualidade do ar
# ==============================
def calcular_indice_personalizado(aqi_original, perfil):
    ajuste = 0

    def get_attr(obj, key):
        if isinstance(obj, dict):
            return obj.get(key, False)
        return getattr(obj, key, False)

    if get_attr(perfil, "possui_asma"): ajuste += 20
    if get_attr(perfil, "possui_dpoc"): ajuste += 15
    if get_attr(perfil, "possui_alergias"): ajuste += 10
    if get_attr(perfil, "fumante"): ajuste += 10
    if get_attr(perfil, "sensibilidade_alta"): ajuste += 5

    aqi_personalizado = aqi_original + ajuste
    if aqi_personalizado <= 50:
        nivel_alerta = "verde"
    elif aqi_personalizado <= 100:
        nivel_alerta = "amarelo"
    elif aqi_personalizado <= 150:
        nivel_alerta = "laranja"
    else:
        nivel_alerta = "vermelho"

    return aqi_personalizado, nivel_alerta

def ajustar_aqi_com_meteorologia(aqi, vento, umidade, temperatura):
    if vento > 5: aqi -= 5
    if umidade > 70: aqi += 5
    if temperatura > 30: aqi += 5
    return max(aqi, 0)