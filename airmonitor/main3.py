from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from airqualityapp.database import get_db
from airqualityapp.crud import salvar_historico, obter_perfil_usuario
from airqualityapp.utils import calcular_indice_personalizado
from .monitor import obter_aqi_nasa_tempo_geo
from .notifications import enviar_alerta_push

app = FastAPI(title="Air Monitor App – Geolocalização")

@app.get("/monitor/aqi")
def monitor_aqi_live(
    lat: float = Query(..., description="Latitude do usuário"),
    lon: float = Query(..., description="Longitude do usuário"),
    usuario_id: int = Query(None, description="ID do usuário"),
    db: Session = Depends(get_db)
):
    """
    Retorna AQI em tempo real para coordenadas enviadas pelo usuário.
    """
    # Obtem AQI da NASA TEMPO
    aqi_original = obter_aqi_nasa_tempo_geo(lat, lon)

    # Calcula AQI personalizado se houver perfil
    aqi_personalizado = aqi_original
    nivel_alerta = "verde"

    if usuario_id:
        perfil = obter_perfil_usuario(db, usuario_id)
        if perfil:
            perfil_dict = {
                "possui_asma": perfil.possui_asma,
                "possui_dpoc": perfil.possui_dpoc,
                "possui_alergias": perfil.possui_alergias,
                "fumante": perfil.fumante,
                "sensibilidade_alta": perfil.sensibilidade_alta
            }
            aqi_personalizado, nivel_alerta = calcular_indice_personalizado(aqi_original, perfil_dict)
            salvar_historico(db, usuario_id, aqi_original, aqi_personalizado, nivel_alerta)

    # Envia alerta push se AQI estiver alto
    if aqi_personalizado > 100 and usuario_id:
        enviar_alerta_push(usuario_id, f"AQI alto ({aqi_personalizado}) na sua localização!")

    return {
        "latitude": lat,
        "longitude": lon,
        "aqi_original": aqi_original,
        "aqi_personalizado": aqi_personalizado,
        "nivel_alerta": nivel_alerta
    }