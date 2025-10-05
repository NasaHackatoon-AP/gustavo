"""
Script para criar um modelo mock para o chatbot funcionar
"""
import numpy as np
import joblib

print("Criando modelo mock para AQI...")

class ModeloAQIMock:
    """Modelo mock que simula previsões de AQI"""

    def predict(self, X):
        """Retorna valores simulados de AQI baseados em temperatura e outros fatores"""
        # X tem formato: [T2M, WS10M, ALLSKY_SFC_SW_DWN, dia_ano, mes, possui_asma, fumante, sensibilidade_alta]
        n_samples = X.shape[0] if len(X.shape) > 1 else 1

        # Gerar AQI simulado entre 30-150 (normalmente Bom a Moderado)
        np.random.seed(42)
        base_aqi = np.random.randint(40, 100, n_samples)

        # Adicionar variação baseada em temperatura se disponível
        if len(X.shape) > 1:
            temp_factor = (X[:, 0] - 20) * 2  # Temperatura afeta AQI
            base_aqi = base_aqi + temp_factor.astype(int)

        # Manter valores dentro do range realista
        base_aqi = np.clip(base_aqi, 10, 180)

        return base_aqi

# Criar e salvar modelo
model = ModeloAQIMock()
caminho = "ml/modelo_aqi.pkl"
joblib.dump(model, caminho)

print(f"✅ Modelo mock criado e salvo em: {caminho}")
print("Agora o chatbot pode fazer previsões!")
