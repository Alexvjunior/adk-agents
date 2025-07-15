# 🚀 Comandos cURL para Conversar com Sara

## 📋 Passo a Passo Simples

### 1. 🔍 Verificar se API está funcionando

```bash
curl http://localhost:5000/list-apps
```

**Resposta esperada:**
```json
["basic-agent","email-agent","question_answering_agent","sara-medical-law-agent","tools-agents"]
```

### 2. 🆔 Criar sessão

```bash
curl -X POST http://localhost:5000/apps/sara-medical-law-agent/users/meu-usuario/sessions \
  -H "Content-Type: application/json" \
  -d '{"state": {}}'
```

**Resposta esperada:**
```json
{
  "id": "a2d9642d-9fab-4ef3-be1b-75c1f58078be",
  "appName": "sara-medical-law-agent",
  "userId": "meu-usuario",
  "state": {},
  "events": [],
  "lastUpdateTime": 1752618701.0861795
}
```

⚠️ **IMPORTANTE:** Copie o valor do campo `"id"` - esse é seu `SESSION_ID`!

### 3. 💬 Enviar mensagem para Sara

**Cole o SESSION_ID que você copiou no comando abaixo:**

```bash
curl -X POST http://localhost:5000/run \
  -H "Content-Type: application/json" \
  -d '{
    "appName": "sara-medical-law-agent",
    "userId": "meu-usuario",
    "sessionId": "COLE_SEU_SESSION_ID_AQUI",
    "newMessage": {
      "parts": [{"text": "Quais são os direitos dos pacientes no Brasil?"}]
    }
  }'
```

## 🎯 Exemplos Prontos para Testar

### Exemplo 1: Direitos dos Pacientes
```bash
curl -X POST http://localhost:5000/run \
  -H "Content-Type: application/json" \
  -d '{
    "appName": "sara-medical-law-agent",
    "userId": "meu-usuario", 
    "sessionId": "SEU_SESSION_ID",
    "newMessage": {
      "parts": [{"text": "Quais são os direitos básicos dos pacientes?"}]
    }
  }'
```

### Exemplo 2: Sigilo Médico
```bash
curl -X POST http://localhost:5000/run \
  -H "Content-Type: application/json" \
  -d '{
    "appName": "sara-medical-law-agent",
    "userId": "meu-usuario",
    "sessionId": "SEU_SESSION_ID", 
    "newMessage": {
      "parts": [{"text": "Como funciona o sigilo médico no Brasil?"}]
    }
  }'
```

### Exemplo 3: Prontuário Médico
```bash
curl -X POST http://localhost:5000/run \
  -H "Content-Type: application/json" \
  -d '{
    "appName": "sara-medical-law-agent",
    "userId": "meu-usuario",
    "sessionId": "SEU_SESSION_ID",
    "newMessage": {
      "parts": [{"text": "O que diz a lei sobre prontuário médico?"}]
    }
  }'
```

### Exemplo 4: Telemedicina
```bash
curl -X POST http://localhost:5000/run \
  -H "Content-Type: application/json" \
  -d '{
    "appName": "sara-medical-law-agent",
    "userId": "meu-usuario",
    "sessionId": "SEU_SESSION_ID",
    "newMessage": {
      "parts": [{"text": "Quais são as regras da telemedicina no Brasil?"}]
    }
  }'
```

## 🔄 Script Automático Completo

**Execute este comando para testar tudo automaticamente:**

```bash
bash curl_exemplo_sara.sh
```

## ☁️ Para EasyPanel

**Se você já fez deploy no EasyPanel, substitua a URL:**

```bash
# Em vez de: http://localhost:5000
# Use: https://seu-dominio.easypanel.host

curl https://seu-dominio.easypanel.host/list-apps
```

## 📱 Formato da Resposta

A Sara responde neste formato:
```json
[
  {
    "content": {
      "parts": [
        {
          "text": "Resposta da Sara aqui..."
        }
      ],
      "role": "model"
    },
    "usageMetadata": {...},
    "invocationId": "...",
    "author": "sara_medical_law_agent",
    "id": "...",
    "timestamp": 1752618519.119264
  }
]
```

**Para extrair apenas a resposta:**
```bash
curl ... | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['content']['parts'][0]['text'])"
```

## 🎯 Dicas Importantes

1. **Use sempre o mesmo `userId` e `sessionId`** para manter contexto da conversa
2. **Sara só responde sobre direito médico e da saúde**
3. **Cada sessão mantém histórico** - perguntas relacionadas funcionam melhor
4. **Se der erro "Session not found"** - crie nova sessão

## 🚨 Troubleshooting

**Erro: "Connection refused"**
→ Verifique se `adk api_server` está rodando

**Erro: "Session not found"** 
→ Crie nova sessão ou verifique se SESSION_ID está correto

**Sara não responde perguntas específicas**
→ Verifique se a pergunta é sobre direito médico/saúde

**🎉 Agora você pode conversar com Sara via cURL!** 