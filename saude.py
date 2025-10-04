from fastapi import FastAPI, Depends
import requests

app = FastAPI()

def calcular_indice_personalizado(aqi, perfil):
    fator_risco = 1.0
    if perfil["possui_asma"]:
        fator_risco *= 1.4
    if perfil["possui_dpoc"]:
        fator_risco *= 1.5
    if perfil["fumante"]:
        fator_risco *= 1.3
    if perfil["sensibilidade_alta"]:
        fator_risco *= 1.2
    return min(int(aqi * fator_risco), 500)

@app.get("/alerta")
def gerar_alerta(usuario_id: int):
    perfil = obter_perfil_saude(usuario_id)
    dados_aqi = obter_dados_qualidade_ar(perfil["cidade"])

    indice_personalizado = calcular_indice_personalizado(dados_aqi["aqi"], perfil)
    nivel = classificar_aqi(indice_personalizado)
    return {"aqi_personalizado": indice_personalizado, "nivel_alerta": nivel}
