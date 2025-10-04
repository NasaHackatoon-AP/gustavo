from xgboost import XGBRegressor
import joblib

def treinar_modelo(X_train, y_train):
    model = XGBRegressor(n_estimators=200, learning_rate=0.1, max_depth=5, random_state=42)
    model.fit(X_train, y_train)
    return model

def salvar_modelo(model, caminho="ml/modelo_aqi.pkl"):
    joblib.dump(model, caminho)

def carregar_modelo(caminho="ml/modelo_aqi.pkl"):
    return joblib.load(caminho)