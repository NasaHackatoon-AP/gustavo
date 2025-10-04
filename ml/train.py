import pandas as pd
from preprocessing import criar_features
from ml_model import treinar_modelo, salvar_modelo

df = pd.read_csv("ml/dados/dados_aqi.csv", parse_dates=["data"])
df = criar_features(df)

FEATURES = ["T2M", "WS10M", "ALLSKY_SFC_SW_DWN", "dia_ano", "mes", "possui_asma", "fumante", "sensibilidade_alta"]
TARGET = "AQI_personalizado"

X = df[FEATURES]
y = df[TARGET]

model = treinar_modelo(X, y)
salvar_modelo(model)
print("Modelo treinado e salvo com sucesso!")