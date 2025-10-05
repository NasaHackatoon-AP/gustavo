from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from airqualityapp.database import get_db
from airqualityapp.crud import salvar_historico, obter_perfil_usuario
from airqualityapp.utils import calcular_indice_personalizado
from .monitor import obter_aqi_nasa_tempo_geo
from .notifications import enviar_alerta_push
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = APIRouter()

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
    try:
        logger.info(f"Requisição AQI recebida: lat={lat}, lon={lon}, usuario_id={usuario_id}")

        # Obtem AQI da NASA TEMPO
        aqi_original = obter_aqi_nasa_tempo_geo(lat, lon)

        # Verificar se a API retornou um valor válido
        if aqi_original is None:
            logger.error("API OpenAQ/NASA não retornou dados válidos")
            raise HTTPException(
                status_code=503,
                detail="Serviço de qualidade do ar temporariamente indisponível. Tente novamente mais tarde."
            )

        # Calcula AQI personalizado se houver perfil
        aqi_personalizado = aqi_original
        nivel_alerta = "verde"

        if usuario_id:
            try:
                perfil = obter_perfil_usuario(db, usuario_id)
                if perfil:
                    logger.info(f"Perfil do usuário {usuario_id} encontrado")

                    perfil_dict = {
                        "possui_asma": perfil.possui_asma,
                        "possui_dpoc": perfil.possui_dpoc,
                        "possui_alergias": perfil.possui_alergias,
                        "fumante": perfil.fumante,
                        "sensibilidade_alta": perfil.sensibilidade_alta
                    }

                    aqi_personalizado, nivel_alerta = calcular_indice_personalizado(aqi_original, perfil_dict)
                    logger.info(f"AQI personalizado calculado: {aqi_personalizado} (nível: {nivel_alerta})")

                    # Salvar histórico
                    try:
                        salvar_historico(db, usuario_id, aqi_original, aqi_personalizado, nivel_alerta)
                    except Exception as e:
                        logger.error(f"Erro ao salvar histórico: {e}")
                        # Não interrompe a execução se falhar ao salvar histórico

                else:
                    logger.warning(f"Perfil não encontrado para usuário {usuario_id}")

            except Exception as e:
                logger.error(f"Erro ao processar perfil do usuário: {e}")
                # Continua com AQI não personalizado se houver erro ao buscar perfil

        # Envia alerta push se AQI estiver alto
        if aqi_personalizado > 100 and usuario_id:
            try:
                enviar_alerta_push(usuario_id, f"AQI alto ({aqi_personalizado}) na sua localização!")
            except Exception as e:
                logger.error(f"Erro ao enviar alerta push: {e}")
                # Não interrompe a execução se falhar ao enviar alerta

        logger.info(f"Resposta enviada com sucesso: AQI original={aqi_original}, AQI personalizado={aqi_personalizado}")

        return {
            "latitude": lat,
            "longitude": lon,
            "aqi_original": aqi_original,
            "aqi_personalizado": aqi_personalizado,
            "nivel_alerta": nivel_alerta,
            "usuario_id": usuario_id
        }

    except HTTPException:
        # Re-raise HTTPException para manter o status code correto
        raise

    except Exception as e:
        logger.error(f"Erro inesperado no endpoint /monitor/aqi: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao processar requisição de qualidade do ar"
        )