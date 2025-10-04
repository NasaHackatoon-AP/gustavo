# test_api.py
from sqlalchemy.orm import Session
from airqualityapp.models import Usuario, AQIPersonalizadoHistorico
from airqualityapp.database import SessionLocal, engine

# Cria as tabelas se não existirem (opcional)
# Base.metadata.create_all(bind=engine)

def main():
    # Cria uma sessão do banco
    db: Session = SessionLocal()
    
    try:
        # 1️⃣ Criar um usuário de teste
        usuario = Usuario(
            nome="Gustavo Teste",
            email="gustavo_teste@example.com",
            senha_hash="123456",
            data_nascimento="1990-01-01",
            cidade="Cidade Teste",
            estado="Estado Teste"
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        print(f"✅ Usuário criado: id={usuario.id}, nome={usuario.nome}")

        # 2️⃣ Criar um registro de AQI personalizado
        aqi = AQIPersonalizadoHistorico(
            usuario_id=usuario.id,
            aqi_original=50,
            aqi_personalizado=45,
            nivel_alerta="Moderado"
        )
        db.add(aqi)
        db.commit()
        db.refresh(aqi)
        print(f"✅ AQI criado: id={aqi.id}, usuario_id={aqi.usuario_id}, nivel_alerta={aqi.nivel_alerta}")

        # 3️⃣ Listar todos os registros de AQI no banco
        registros = db.query(AQIPersonalizadoHistorico).all()
        print("\n📋 Lista de registros de AQI:")
        for r in registros:
            print(f"id={r.id}, usuario_id={r.usuario_id}, aqi_original={r.aqi_original}, aqi_personalizado={r.aqi_personalizado}, nivel_alerta={r.nivel_alerta}")

    except Exception as e:
        print("❌ Ocorreu um erro:", e)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()