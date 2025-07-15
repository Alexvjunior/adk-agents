# 🚀 Deploy Sara no EasyPanel com Docker Compose

## 📦 Arquivos Necessários

Certifique-se de que você tem estes arquivos no seu repositório:

```
projeto/
├── docker-compose.yml        # ✅ Criado
├── Dockerfile               # ✅ Criado  
├── requirements.txt         # ✅ Criado
├── env-config.md            # ✅ Configurações
├── sara-medical-law-agent/  # ✅ Agente Sara
│   ├── __init__.py
│   └── agent.py
└── outros-agentes/          # ✅ Outros (opcional)
```

## 🔧 Passo a Passo no EasyPanel

### 1. 📂 Preparar Repositório

```bash
# Adicionar docker-compose.yml ao git
git add docker-compose.yml env-config.md EASYPANEL_DEPLOY.md
git commit -m "Add Docker Compose for EasyPanel deploy"
git push origin main
```

### 2. 🐳 Criar Projeto no EasyPanel

1. **Login no EasyPanel**
2. **Criar Novo Projeto**
3. **Escolher "Docker Compose"** (não Docker simples)

### 3. ⚙️ Configuração do Projeto

**A. Repository Settings:**
- **Repository URL:** `https://github.com/SEU-USUARIO/sara-medical-agent.git`
- **Branch:** `main`
- **Docker Compose File:** `docker-compose.yml`

**B. Build Settings:**
- **Build Context:** `.` (raiz do projeto)
- **Service Name:** `sara-medical-agent`

### 4. 🔑 Variáveis de Ambiente

No EasyPanel, vá em **"Environment Variables"** e adicione:

| Nome | Valor | Obrigatório |
|------|-------|-------------|
| `GOOGLE_API_KEY` | sua-chave-google-aqui | ✅ Sim |
| `PORT` | `5000` | ✅ Sim |
| `PYTHONPATH` | `/app` | ✅ Sim |

**🔑 Como obter GOOGLE_API_KEY:**
1. Acesse [Google AI Studio](https://aistudio.google.com/)
2. Clique em "Get API Key"
3. Crie nova chave
4. Copie para o EasyPanel

### 5. 🌐 Configuração de Rede

- **Port Mapping:** `5000:5000`
- **Protocol:** `HTTP`
- **Health Check:** Habilitado (já configurado no compose)

### 6. 🚀 Deploy

1. Clique em **"Deploy"**
2. Aguarde build (2-4 minutos)
3. EasyPanel gerará URL: `https://sara-xyz123.easypanel.host`

## ✅ Verificar se Funcionou

### Teste 1: Lista de Agentes
```bash
curl https://sua-url.easypanel.host/list-apps
# Resposta: ["sara-medical-law-agent", ...]
```

### Teste 2: Documentação
```
https://sua-url.easypanel.host/docs
```

### Teste 3: Conversa com Sara
```bash
# 1. Criar sessão
curl -X POST https://sua-url.easypanel.host/apps/sara-medical-law-agent/users/test/sessions \
  -H "Content-Type: application/json" \
  -d '{"state": {}}'

# 2. Fazer pergunta (use o sessionId retornado)
curl -X POST https://sua-url.easypanel.host/run \
  -H "Content-Type: application/json" \
  -d '{
    "appName": "sara-medical-law-agent",
    "userId": "test",
    "sessionId": "COLE-SESSION-ID-AQUI",
    "newMessage": {"parts": [{"text": "Quais são os direitos dos pacientes?"}]}
  }'
```

## 🎯 Vantagens do Docker Compose

✅ **Health Checks automáticos**  
✅ **Restart automático** se container falhar  
✅ **Logs persistentes**  
✅ **Rede isolada** para segurança  
✅ **Labels para proxy reverso**  
✅ **Configuração mais flexível**  

## 🔧 Troubleshooting

### Container não inicia
```bash
# Ver logs no EasyPanel
docker-compose logs sara-medical-agent
```

### API não responde
1. **Verificar porta 5000** exposta
2. **Conferir GOOGLE_API_KEY** válida
3. **Checar health check** nos logs

### Rebuild forçado
1. No EasyPanel: **"Force Rebuild"**
2. Ou: **"Restart Service"**

## 📊 Monitoramento

O Docker Compose inclui:
- **Health Check** automático (`/list-apps`)
- **Restart Policy** (`unless-stopped`)
- **Logs estruturados**
- **Metrics** via labels Traefik

## 🎉 Resultado Final

Após deploy bem-sucedido:
- **🌐 API:** `https://sua-url.easypanel.host`
- **📚 Docs:** `https://sua-url.easypanel.host/docs`  
- **💚 Health:** `https://sua-url.easypanel.host/list-apps`
- **🏥 Sara:** Pronta para consultas de direito médico!

---

**🚀 Sara está online e pronta para atender! Deploy concluído com sucesso!** 