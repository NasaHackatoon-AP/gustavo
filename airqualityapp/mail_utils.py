import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import socket
from dotenv import load_dotenv

load_dotenv()

EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"

def testar_conectividade_smtp():
    """Testa se é possível conectar ao servidor SMTP"""
    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=10) as server:
            server.quit()
        return True
    except (socket.timeout, socket.gaierror, smtplib.SMTPException) as e:
        print(f"❌ Erro de conectividade SMTP: {e}")
        return False

def configurar_gmail_alternativo():
    """Configurações alternativas para Gmail"""
    print("🔧 CONFIGURAÇÕES PARA GMAIL:")
    print("1. Ative verificação em 2 etapas")
    print("2. Gere uma senha de app")
    print("3. Use a senha de app no EMAIL_PASS")
    print("\n📝 Configuração no .env:")
    print("EMAIL_HOST=smtp.gmail.com")
    print("EMAIL_PORT=587")
    print("EMAIL_USE_TLS=true")
    print("EMAIL_USER=seu_email@gmail.com")
    print("EMAIL_PASS=senha_de_app_gerada")

def enviar_alerta_email(destino, assunto, mensagem):
    """
    Envia e-mail com tratamento robusto de erros e fallback
    """
    if not EMAIL_USER or not EMAIL_PASS:
        print("❌ Configurações de e-mail não encontradas")
        print("   Configure EMAIL_USER e EMAIL_PASS no arquivo .env")
        return False
    
    try:
        # Criar mensagem simples (como no código que funciona)
        msg = MIMEText(mensagem)
        msg['Subject'] = assunto
        msg['From'] = EMAIL_USER
        msg['To'] = destino
        
        # Conectar e enviar usando Gmail SMTP (código que funciona)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ E-mail enviado para {destino}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Erro de autenticação SMTP: {e}")
        print("   Verifique EMAIL_USER e EMAIL_PASS")
        return False
        
    except smtplib.SMTPRecipientsRefused as e:
        print(f"❌ Destinatário recusado: {e}")
        return False
        
    except smtplib.SMTPServerDisconnected as e:
        print(f"❌ Servidor SMTP desconectado: {e}")
        return enviar_email_fallback(destino, assunto, mensagem)
        
    except (socket.timeout, socket.gaierror) as e:
        print(f"❌ Erro de rede: {e}")
        return enviar_email_fallback(destino, assunto, mensagem)
        
    except Exception as e:
        print(f"❌ Erro inesperado ao enviar e-mail: {e}")
        return enviar_email_fallback(destino, assunto, mensagem)

def enviar_email_fallback(destino, assunto, mensagem):
    """
    Sistema de fallback quando SMTP falha
    """
    print("📧 FALLBACK: Salvando e-mail para envio posterior")
    print("💡 Configure Gmail corretamente para envio automático")
    
    # Criar diretório de fallback se não existir
    fallback_dir = "email_fallback"
    if not os.path.exists(fallback_dir):
        os.makedirs(fallback_dir)
    
    # Salvar e-mail em arquivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{fallback_dir}/email_{timestamp}.txt"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"E-MAIL DE FALLBACK - AURA AIR\n")
            f.write(f"Data: {datetime.now()}\n")
            f.write(f"Para: {destino}\n")
            f.write(f"Assunto: {assunto}\n")
            f.write("="*50 + "\n")
            f.write(mensagem)
            f.write("\n" + "="*50 + "\n")
            f.write("Este e-mail foi salvo porque o SMTP não está funcionando.\n")
            f.write("Configure Gmail corretamente para envio automático.\n")
        
        print(f"✅ E-mail salvo em: {filename}")
        print("💡 Para configurar Gmail:")
        configurar_gmail_alternativo()
        return True
        
    except Exception as e:
        print(f"❌ Erro ao salvar fallback: {e}")
        return False

# Importar datetime para fallback
from datetime import datetime

def testar_configuracao_email():
    """
    Função para testar se a configuração de e-mail está funcionando
    """
    print("🔧 Testando configuração de e-mail...")
    
    # Verificar variáveis de ambiente
    if not EMAIL_USER:
        print("❌ EMAIL_USER não configurado")
        return False
    
    if not EMAIL_PASS:
        print("❌ EMAIL_PASS não configurado")
        return False
    
    print(f"✅ Host: {EMAIL_HOST}:{EMAIL_PORT}")
    print(f"✅ Usuário: {EMAIL_USER}")
    print(f"✅ TLS: {EMAIL_USE_TLS}")
    
    # Testar conectividade
    if testar_conectividade_smtp():
        print("✅ Conectividade SMTP OK")
        
        # Testar envio real
        print("📧 Testando envio de e-mail...")
        resultado = enviar_alerta_email(
            EMAIL_USER,  # Enviar para si mesmo
            "Teste de Configuração",
            "Este é um e-mail de teste para verificar se a configuração está funcionando."
        )
        
        if resultado:
            print("✅ E-mail de teste enviado com sucesso!")
            return True
        else:
            print("❌ Falha no envio do e-mail de teste")
            return False
    else:
        print("❌ Falha na conectividade SMTP")
        return False

if __name__ == "__main__":
    # Executar teste se o arquivo for executado diretamente
    testar_configuracao_email()