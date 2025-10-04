import pandas as pd

def criar_features(df):
    df["dia_ano"] = df["data"].dt.dayofyear
    df["mes"] = df["data"].dt.month
    df["possui_asma"] = df.get("possui_asma", 0)
    df["fumante"] = df.get("fumante", 0)
    df["sensibilidade_alta"] = df.get("sensibilidade_alta", 0)
    return df