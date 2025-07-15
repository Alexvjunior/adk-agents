# 🏥 Sara - Guia de Deploy Otimizado com ADK

## 🎉 Grandes Melhorias Implementadas!

### ✅ API Nativa do Google ADK (vs. Flask personalizada)

**ANTES:**
- API Flask personalizada (`api.py`)
- Endpoints manuais (`/ask`, `/health`, `/info`)
- Tratamento de erros manual
- Sistema de sessões limitado

**AGORA:**
- **API FastAPI nativa** do Google ADK
- **Endpoints otimizados** automaticamente
- **Documentação OpenAPI** integrada
- **Sistema de sessões robusto**
- **Suporte multi-agentes** automático

## 🚀 Como Usar (Super Simples)

### 1. Deploy Local
```bash
# Servidor API puro (recomendado para produção)
adk api_server --port=5000 --host=0.0.0.0 .

# Servidor com interface web
adk web --port=5000 --host=0.0.0.0 .
```

### 2. Deploy no EasyPanel

**Dockerfile Otimizado:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=5000
EXPOSE 5000
CMD ["adk", "api_server", "--port=5000", "--host=0.0.0.0", "."]
```

**No EasyPanel:**
1. Novo projeto → Docker
2. Conectar repositório Git
3. Porta: `5000`
4. Variáveis: `GOOGLE_API_KEY=sua-chave`

## 📡 Endpoints Nativos Poderosos

| Endpoint | Método | Descrição |
|----------|---------|-----------|
| `/list-apps` | GET | Lista todos os agentes |
| `/apps/{app}/users/{user}/sessions` | POST | Cria sessão |
| `/run` | POST | Executa interação |
| `/docs` | GET | Documentação OpenAPI |
| `/apps/{app}/users/{user}/sessions/{id}` | GET | Info da sessão |

## 💬 Exemplo de Uso Simplificado

```bash
# 1. Ver agentes disponíveis
curl http://sua-url/list-apps

# 2. Criar sessão
curl -X POST http://sua-url/apps/sara-medical-law-agent/users/user1/sessions \
  -H "Content-Type: application/json" \
  -d '{"state": {}}'

# 3. Falar com Sara
curl -X POST http://sua-url/run \
  -H "Content-Type: application/json" \
  -d '{
    "appName": "sara-medical-law-agent",
    "userId": "user1",
    "sessionId": "session-id-retornado",
    "newMessage": {"parts": [{"text": "Direitos do paciente?"}]}
  }'
```

## 🔧 Arquivos Criados/Atualizados

### ✅ Novos Arquivos
- `sara-medical-law-agent/adk_client_example.py` - Cliente otimizado
- `SARA_DEPLOY_GUIDE.md` - Este guia

### ✅ Arquivos Atualizados
- `Dockerfile` - Usa comando ADK nativo
- `sara-medical-law-agent/README.md` - Documentação completa
- `requirements.txt` - Dependências otimizadas

### ❌ Arquivos Removidos
- `sara-medical-law-agent/api.py` - API Flask não é mais necessária

## 🎯 Benefícios da Nova Abordagem

| Recurso | Flask Manual | ADK Nativo |
|---------|-------------|------------|
| Performance | Básica | **Otimizada** |
| Documentação | Manual | **Automática** |
| Sessões | Limitadas | **Robustas** |
| Multi-agentes | Não | **Sim** |
| Monitoramento | Manual | **Integrado** |
| Escalabilidade | Limitada | **Enterprise** |
| Interface Web | Não | **Opcional** |
| Autenticação | Manual | **Integrada** |

## 🚀 Próximos Passos Recomendados

1. **Teste local:**
   ```bash
   adk api_server --port=5000 .
   ```

2. **Deploy no EasyPanel:**
   - Use o Dockerfile otimizado
   - Configure variáveis de ambiente

3. **Acesse documentação:**
   ```
   http://sua-url/docs
   ```

4. **Teste com cliente:**
   ```bash
   python sara-medical-law-agent/adk_client_example.py
   ```

## 📊 Estrutura Final do Projeto

```
projeto/
├── sara-medical-law-agent/
│   ├── __init__.py
│   ├── agent.py                    # ✅ Agente Sara
│   ├── test_example.py             # ✅ Testes locais  
│   ├── adk_client_example.py       # 🆕 Cliente ADK
│   └── README.md                   # ✅ Docs atualizadas
├── outros-agentes/                 # ✅ Suporte automático
├── Dockerfile                      # ✅ ADK otimizado
├── requirements.txt                # ✅ Deps atualizadas
└── SARA_DEPLOY_GUIDE.md           # 🆕 Este guia
```

## 🏆 Resultado Final

**Sara agora é uma aplicação enterprise-ready usando:**
- ✅ **Google ADK nativo** (infraestrutura Google)
- ✅ **FastAPI otimizada** (performance superior)
- ✅ **Documentação automática** (OpenAPI)
- ✅ **Deploy simplificado** (um comando)
- ✅ **Escalabilidade real** (produção)

**🎯 Deploy no EasyPanel = Copiar repositório + Configure porta 5000 + Done!**

A Sara está pronta para receber milhares de consultas sobre direito médico! 🏥⚖️ 