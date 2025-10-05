import random

# Função de hash simples (substituir por bcrypt na produção)
def hash_senha(senha: str):
    return "HASH_" + senha

# Simulação de dados TEMPO + sensores locais
def obter_dados_tempo(lat, lon):
    # Substitua por API NASA TEMPO
    return {"pm2_5": random.randint(10, 200)}

def obter_dados_meteorologia(lat, lon):
    # Substitua por API real
    return {"vento": random.uniform(0, 10), "umidade": random.uniform(20, 90), "temperatura": random.uniform(15, 35)}

# Calcula AQI personalizado com base no perfil de saúde
def calcular_indice_personalizado(aqi_original, perfil):
    ajuste = 0

    # Suporta tanto objetos ORM quanto dicionários
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

# Ajuste meteorológico
def ajustar_aqi_com_meteorologia(aqi, vento, umidade, temperatura):
    if vento > 5: aqi -= 5
    if umidade > 70: aqi += 5
    if temperatura > 30: aqi += 5
    return max(aqi, 0)