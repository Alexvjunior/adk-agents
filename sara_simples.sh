#!/bin/bash

# 🏥 Script Simples para Sara - Sem gerenciamento manual de sessão
# Uso: ./sara_simples.sh "Sua pergunta aqui"

API_URL="http://localhost:5001"  # Mude a porta se necessário
PERGUNTA="$1"

# Verificar se pergunta foi fornecida
if [ -z "$PERGUNTA" ]; then
    echo "❌ Uso: ./sara_simples.sh \"Sua pergunta aqui\""
    echo ""
    echo "Exemplos:"
    echo "./sara_simples.sh \"Quais são os direitos dos pacientes?\""
    echo "./sara_simples.sh \"Como funciona o sigilo médico?\""
    exit 1
fi

# Gerar usuário único
USER_ID="user_$(date +%s)_$$"

# Criar sessão automaticamente
SESSION_RESPONSE=$(curl -s -X POST "$API_URL/apps/sara-medical-law-agent/users/$USER_ID/sessions" \
  -H "Content-Type: application/json" \
  -d '{"state": {}}' 2>/dev/null)

if [ $? -ne 0 ]; then
    echo "❌ Erro: API não está rodando em $API_URL"
    echo "💡 Execute: adk api_server --port=5001"
    exit 1
fi

# Extrair Session ID
SESSION_ID=$(echo "$SESSION_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

if [ -z "$SESSION_ID" ]; then
    echo "❌ Erro ao criar sessão"
    exit 1
fi

# Enviar pergunta e extrair só a resposta
RESPONSE=$(curl -s -X POST "$API_URL/run" \
  -H "Content-Type: application/json" \
  -d "{
    \"appName\": \"sara-medical-law-agent\",
    \"userId\": \"$USER_ID\",
    \"sessionId\": \"$SESSION_ID\",
    \"newMessage\": {
      \"parts\": [{\"text\": \"$PERGUNTA\"}]
    }
  }" 2>/dev/null)

# Extrair e exibir apenas a resposta da Sara
echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data and len(data) > 0:
        response_text = data[0]['content']['parts'][0]['text']
        print(response_text)
    else:
        print('❌ Erro: Resposta vazia da Sara')
except Exception as e:
    print('❌ Erro ao processar resposta da Sara')
" 2>/dev/null 