"""
Modelo simples para previsões de AQI
"""
import numpy as np

class ModeloAQISimples:
    """Modelo simples que gera previsões de AQI"""

    def predict(self, X):
        """Retorna previsões de AQI simuladas"""
        # X esperado: [T2M, WS10M, ALLSKY_SFC_SW_DWN, dia_ano, mes, possui_asma, fumante, sensibilidade_alta]

        # Converter pandas DataFrame para numpy se necessário
        if hasattr(X, 'values'):
            X = X.values

        if not hasattr(X, 'shape'):
            X = np.array(X)

        n_samples = X.shape[0] if len(X.shape) > 1 else 1

        # Gerar valores baseados em seed para consistência
        np.random.seed(42)
        base_aqi = np.random.randint(30, 90, n_samples)

        # Adicionar variação baseada em fatores
        if len(X.shape) > 1 and X.shape[1] >= 5:
            # Temperatura (índice 0) afeta AQI
            temp = X[:, 0]
            temp_effect = ((temp - 20) * 1.5).astype(int)

            # Vento (índice 1) reduz AQI
            wind = X[:, 1]
            wind_effect = -(wind * 0.5).astype(int)

            base_aqi = base_aqi + temp_effect + wind_effect

        # Manter valores realistas
        base_aqi = np.clip(base_aqi, 10, 180)

        return base_aqi
