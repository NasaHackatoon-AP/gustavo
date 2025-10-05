# 🔐 Sistema de Reset de Senha - Aura Air

## ✅ **SISTEMA IMPLEMENTADO E FUNCIONANDO**

### 🚀 **Endpoints Disponíveis:**

#### **1. Gerar Token de Reset:**
```
POST /airquality/forgot-password
Content-Type: application/x-www-form-urlencoded

email=usuario@exemplo.com
```

#### **2. Redefinir Senha:**
```
POST /airquality/reset-password
Content-Type: application/x-www-form-urlencoded

token=token_recebido_por_email
nova_senha=nova_senha_123
```

#### **3. Login:**
```
POST /airquality/login
Content-Type: application/json

{
  "email": "usuario@exemplo.com",
  "senha": "senha123"
}
```

#### **4. Perfil do Usuário:**
```
GET /airquality/me
Authorization: Bearer <token>
```

### 📧 **Sistema de E-mail:**

- ✅ **Gmail SMTP**: `smtp.gmail.com:587`
- ✅ **TLS**: Conexão segura
- ✅ **Fallback**: E-mails salvos em `email_fallback/` se SMTP falhar
- ✅ **Token**: Enviado por e-mail com expiração de 60 minutos

### 🔧 **Configuração (.env):**

```env
# E-mail
EMAIL_USER=seu_email@gmail.com
EMAIL_PASS=senha_de_app_gerada

# Banco de dados
DATABASE_URL=mysql+pymysql://gustavo:kaue1537@192.168.1.24:3306/aura-air-db

# APIs
NASA_API_KEY=eed14e14f570e63c44e8db170244c4be01c4021cc492fa10f213136fef4c6dc1
OPENAQ_API=https://api.openaq.org/v3
OPENWEATHER_API_KEY=d7850b94e00a68bac75067fb77e0b177
OPENWEATHER_API_URL=https://api.openweathermap.org/data/2.5/weather
GEMINI_API_KEY=AIzaSyCfr-mnxFaFFqM0BKUwwE-_pH_vEInkXiY

# Segurança
SECRET_KEY=sua_chave_super_secreta_aqui_trocar_em_producao
ALGORITHM=HS256
```

### 🚀 **Como Usar:**

1. **Iniciar API:**
   ```bash
   uvicorn main2:app --reload
   ```

2. **Testar Reset de Senha:**
   - Acesse: `http://localhost:8000/docs`
   - Use o endpoint `/forgot-password`
   - Digite o e-mail
   - Verifique o e-mail recebido
   - Use o token em `/reset-password`

### 🔑 **Para Gmail Funcionar:**

1. Ative verificação em 2 etapas
2. Gere uma senha de app
3. Use a senha de app no `EMAIL_PASS`

### 📁 **Sistema de Fallback:**

Se o e-mail não for enviado, será salvo em:
- `email_fallback/email_YYYYMMDD_HHMMSS.txt`

### ✅ **Status:**
- ✅ Sistema de reset implementado
- ✅ E-mail funcionando
- ✅ Tokens seguros
- ✅ Fallback automático
- ✅ Testes removidos
- ✅ Sistema limpo e organizado
