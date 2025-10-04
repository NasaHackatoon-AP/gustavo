from sqlalchemy.orm import Session
from .models import Usuario, PerfilSaude, AQIPersonalizadoHistorico, AlertasEnviados
from .utils import hash_senha
from sqlalchemy.orm import joinedload

def criar_usuario(db: Session, usuario):
    db_usuario = Usuario(
        nome=usuario.nome,
        email=usuario.email,
        data_nascimento=usuario.data_nascimento,
        cidade=usuario.cidade,
        estado=usuario.estado,
        senha_hash=hash_senha(usuario.senha)
    )
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

def criar_perfil_saude(db: Session, perfil):
    db_perfil = PerfilSaude(**perfil.dict())
    db.add(db_perfil)
    db.commit()
    db.refresh(db_perfil)
    return db_perfil

def obter_perfil_usuario(db: Session, usuario_id: int):
    return db.query(PerfilSaude)\
             .options(joinedload(PerfilSaude.usuario))\
             .filter(PerfilSaude.usuario_id == usuario_id)\
             .first()

def salvar_historico(db: Session, usuario_id: int, aqi_original: int, aqi_personalizado: int, nivel_alerta: str):
    registro = AQIPersonalizadoHistorico(
        usuario_id=usuario_id,
        aqi_original=aqi_original,
        aqi_personalizado=aqi_personalizado,
        nivel_alerta=nivel_alerta
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro

def registrar_alerta(db: Session, usuario_id: int, nivel_alerta: str, metodo: str):
    alerta = AlertasEnviados(
        usuario_id=usuario_id,
        nivel_alerta=nivel_alerta,
        metodo=metodo
    )
    db.add(alerta)
    db.commit()
    db.refresh(alerta)
    return alerta