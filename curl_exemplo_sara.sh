#!/bin/bash

# 🏥 EXEMPLO COMPLETO: Como conversar com Sara via cURL
# Execute: bash curl_exemplo_sara.sh

# Configurações
API_URL="http://localhost:5000"  # Mude para sua URL do EasyPanel se necessário
USER_ID="user_$(date +%s)"

echo "🔗 Testando conexão com Sara..."

# 1. Verificar se API está funcionando
echo "📡 1. Verificando agentes disponíveis:"
curl -s "$API_URL/list-apps" | python3 -m json.tool
echo ""

# 2. Criar sessão
echo "🆔 2. Criando sessão para usuário: $USER_ID"
SESSION_RESPONSE=$(curl -s -X POST "$API_URL/apps/sara-medical-law-agent/users/$USER_ID/sessions" \
  -H "Content-Type: application/json" \
  -d '{"state": {}}')

echo "Resposta da criação de sessão:"
echo "$SESSION_RESPONSE" | python3 -m json.tool
echo ""

# Extrair Session ID
SESSION_ID=$(echo "$SESSION_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "✅ Session ID criado: $SESSION_ID"
echo ""

# 3. Enviar mensagem para Sara
echo "💬 3. Enviando pergunta para Sara:"
PERGUNTA="Quais são os direitos básicos dos pacientes no Brasil?"
echo "Pergunta: $PERGUNTA"
echo ""

RESPONSE=$(curl -s -X POST "$API_URL/run" \
  -H "Content-Type: application/json" \
  -d "{
    \"appName\": \"sara-medical-law-agent\",
    \"userId\": \"$USER_ID\",
    \"sessionId\": \"$SESSION_ID\",
    \"newMessage\": {
      \"parts\": [{\"text\": \"$PERGUNTA\"}]
    }
  }")

echo "🎯 Resposta da Sara:"
echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data and len(data) > 0:
        response_text = data[0]['content']['parts'][0]['text']
        print('💬 Sara:', response_text)
    else:
        print('❌ Resposta vazia')
except Exception as e:
    print('❌ Erro ao processar resposta:', e)
    print('Resposta bruta:', data)
"

echo ""
echo "🎉 Exemplo concluído!"
echo ""
echo "🔄 Para fazer mais perguntas, use este comando:"
echo "curl -X POST '$API_URL/run' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo "    \"appName\": \"sara-medical-law-agent\","
echo "    \"userId\": \"$USER_ID\","
echo "    \"sessionId\": \"$SESSION_ID\","
echo "    \"newMessage\": {"
echo "      \"parts\": [{\"text\": \"SUA_PERGUNTA_AQUI\"}]"
echo "    }"
echo "  }'" 