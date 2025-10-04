from .ml_model import carregar_modelo
import pandas as pd
from datetime import timedelta

FEATURES = ["T2M", "WS10M", "ALLSKY_SFC_SW_DWN", "dia_ano", "mes", "possui_asma", "fumante", "sensibilidade_alta"]

def prever_proximos_15_dias(df_ultimo_dia):
    model = carregar_modelo()
    previsoes = []
    ultimo_dia = df_ultimo_dia["data"].max()
    X_last = df_ultimo_dia[FEATURES].iloc[-1:]

    for i in range(1, 16):
        data_pred = ultimo_dia + timedelta(days=i)
        X_pred = X_last.copy()
        X_pred["dia_ano"] = data_pred.timetuple().tm_yday
        X_pred["mes"] = data_pred.month
        aqi_pred = model.predict(X_pred)[0]

        if aqi_pred <= 50:
            nivel = "verde"
        elif aqi_pred <= 100:
            nivel = "amarelo"
        elif aqi_pred <= 150:
            nivel = "laranja"
        else:
            nivel = "vermelho"

        previsoes.append({
            "data": data_pred.strftime("%Y-%m-%d"),
            "aqi_previsto": round(aqi_pred, 2),
            "nivel_alerta": nivel
        })

    return previsoes