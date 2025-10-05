from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from passlib.context import CryptContext
import secrets, hashlib
from jose import JWTError, jwt
from .models import Usuario, PerfilSaude, AQIPersonalizadoHistorico, AlertasEnviados
from .utils import verify_password, hash_senha
from .mail_utils import enviar_alerta_email

# Configurações
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
RESET_TOKEN_EXP_MINUTES = 60  # tempo de validade do token

# Configurações JWT
SECRET_KEY = "segredo-super-seguro-aura-air"  # Em produção, use uma chave mais segura
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# -----------------------------
# Autenticação JWT
# -----------------------------

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Cria token JWT de acesso"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(db: Session, token: str):
    """Obtém usuário atual baseado no token JWT"""
    print(f"🔍 Token recebido: {token[:50]}...")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"✅ Token decodificado: {payload}")
        email = payload.get("sub")
        if email is None:
            print("❌ Email não encontrado no token")
            raise HTTPException(status_code=401, detail="Token inválido")
        
        usuario = db.query(Usuario).filter(Usuario.email == email).first()
        if not usuario:
            print(f"❌ Usuário não encontrado: {email}")
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        print(f"✅ Usuário encontrado: {usuario.nome}")
        return usuario
    except JWTError as e:
        print(f"❌ Erro JWT: {e}")
        raise HTTPException(status_code=401, detail="Token inválido")

def autenticar_usuario(db: Session, email: str, senha: str):
    """Autentica usuário com email e senha"""
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        return False
    if not verify_password(senha, usuario.senha_hash):
        return False
    return usuario

# -----------------------------
# Usuários
# -----------------------------

def criar_usuario(db: Session, usuario):
    # Verificar se o email já existe
    usuario_existente = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado"
        )

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

def login_usuario(db: Session, email: str, senha: str):
    """Autentica usuário e retorna token JWT"""
    usuario = autenticar_usuario(db, email, senha)
    if not usuario:
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")
    
    # Criar token JWT
    access_token = create_access_token(data={"sub": usuario.email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "usuario": {
            "id": usuario.id,
            "nome": usuario.nome,
            "email": usuario.email,
            "cidade": usuario.cidade,
            "estado": usuario.estado
        }
    }

def deletar_usuario(db: Session, email: str, senha: str):
    """Deleta usuário após verificar credenciais"""
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario or not verify_password(senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")

    # Migrar hash legado para bcrypt automaticamente
    if usuario.senha_hash.startswith("HASH_"):
        usuario.senha_hash = hash_senha(senha)
        db.commit()

    # Deletar registros relacionados primeiro
    # Deletar perfil de saúde
    db.query(PerfilSaude).filter(PerfilSaude.usuario_id == usuario.id).delete()
    # Deletar histórico AQI
    db.query(AQIPersonalizadoHistorico).filter(AQIPersonalizadoHistorico.usuario_id == usuario.id).delete()
    # Deletar alertas enviados
    db.query(AlertasEnviados).filter(AlertasEnviados.usuario_id == usuario.id).delete()
    
    # Agora pode deletar o usuário
    db.delete(usuario)
    db.commit()
    return {"msg": "Conta deletada com sucesso!"}

# -----------------------------
# Perfil de saúde
# -----------------------------

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

# -----------------------------
# Histórico e alertas
# -----------------------------

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

# -----------------------------
# Forgot Password / Reset
# -----------------------------

def gerar_token_redefinicao(db: Session, email: str):
    """Gera token de redefinição e envia por e-mail"""
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if usuario:
        # Gerar token seguro
        token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Salvar no banco
        usuario.reset_token_hash = token_hash
        usuario.reset_expires_at = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXP_MINUTES)
        db.add(usuario)
        db.commit()

        # Preparar e-mail
        assunto = "🔐 Redefinição de senha - Aura Air"
        corpo = f"""
        Olá {usuario.nome},

        Recebemos uma solicitação de redefinição de senha para sua conta Aura Air.

        🔑 Seu token de redefinição: {token}

        ⏰ Este token expira em {RESET_TOKEN_EXP_MINUTES} minutos.

        Para redefinir sua senha, use este token no endpoint /reset-password.

        Se não foi você quem solicitou, ignore este e-mail.

        ---
        Sistema Aura Air - Qualidade do Ar Personalizada
        """

        # Enviar e-mail
        try:
            resultado = enviar_alerta_email(usuario.email, assunto, corpo)
            if resultado:
                print(f"✅ E-mail de reset enviado para: {usuario.email}")
            else:
                print(f"⚠️ E-mail salvo em fallback para: {usuario.email}")
        except Exception as e:
            print(f"⚠️ Erro ao enviar e-mail: {e}")
            # Continuar mesmo se e-mail falhar

    # Resposta genérica para segurança
    return {"msg": "Se o e-mail existir no sistema, você receberá instruções para resetar a senha."}

def redefinir_senha(db: Session, token: str, nova_senha: str):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    agora = datetime.utcnow()

    usuario = db.query(Usuario).filter(
        Usuario.reset_token_hash == token_hash,
        Usuario.reset_expires_at != None,
        Usuario.reset_expires_at >= agora
    ).first()

    if not usuario:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado")

    # Atualizar senha com bcrypt
    usuario.senha_hash = pwd_context.hash(nova_senha)

    # Invalidar token
    usuario.reset_token_hash = None
    usuario.reset_expires_at = None

    db.add(usuario)
    db.commit()
    return {"msg": "Senha redefinida com sucesso!"}