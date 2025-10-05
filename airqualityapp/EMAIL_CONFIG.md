# Configuração de E-mail

## Problema: Erro de Conexão SMTP

O erro `[WinError 10060]` indica problemas de conectividade com o servidor SMTP.

## Soluções Implementadas

### 1. Sistema de Fallback
- Quando SMTP falha, os e-mails são salvos em arquivos na pasta `email_fallback/`
- Permite que o sistema continue funcionando mesmo sem conectividade

### 2. Configuração Correta do .env

Crie um arquivo `.env` na raiz do projeto com:

```env
# Configurações de E-mail
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_USER=seu_email@gmail.com
EMAIL_PASS=sua_senha_de_app
```

### 3. Para Gmail (Recomendado)

1. **Ative a verificação em 2 etapas** na sua conta Google
2. **Gere uma senha de app**:
   - Vá em "Gerenciar sua Conta Google"
   - Segurança → Verificação em duas etapas
   - Senhas de app → Gerar senha de app
   - Use essa senha no `EMAIL_PASS`

### 4. Outros Provedores

#### Outlook/Hotmail:
```env
EMAIL_HOST=smtp-mail.outlook.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
```

#### Yahoo:
```env
EMAIL_HOST=smtp.mail.yahoo.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
```

## Teste de Conectividade

O sistema agora testa a conectividade antes de tentar enviar e-mails.

## Fallback Automático

Se o SMTP falhar, os e-mails são salvos em:
- `email_fallback/email_YYYYMMDD_HHMMSS.txt`

Você pode enviar esses e-mails manualmente depois.
