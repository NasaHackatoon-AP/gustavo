import joblib
import numpy as np
from sklearn.linear_model import LinearRegression
import os

# Certifica que a pasta "ml" existe
os.makedirs("ml", exist_ok=True)

# Criar dados fictícios (8 features)
# ["T2M", "WS10M", "ALLSKY_SFC_SW_DWN", "dia_ano", "mes", "possui_asma", "fumante", "sensibilidade_alta"]
X = np.random.rand(100, 8) * 100

# Criar alvo (AQI) com alguma relação simples entre as features
y = (50
     + X[:, 0]*0.3  # T2M
     + X[:, 1]*0.2  # WS10M
     - X[:, 2]*0.1  # ALLSKY
     + X[:, 3]*0.05 # dia_ano
     + X[:, 4]*0.1  # mes
     + X[:, 5]*0.2  # possui_asma
     + X[:, 6]*0.1  # fumante
     + X[:, 7]*0.15 # sensibilidade_alta
    )

# Treinar modelo
modelo = LinearRegression()
modelo.fit(X, y)

# Salvar modelo
joblib.dump(modelo, "ml/modelo_aqi.pkl")
print("✅ Modelo fake de 8 features salvo em ml/modelo_aqi.pkl")