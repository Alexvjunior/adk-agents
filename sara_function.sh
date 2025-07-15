# 🏥 Função Shell para Sara - Use como: sara "sua pergunta"
# Para usar: source sara_function.sh  (depois use: sara "pergunta")

sara() {
    if [ -z "$1" ]; then
        echo "❌ Uso: sara \"Sua pergunta aqui\""
        echo ""
        echo "Exemplos:"
        echo "sara \"Quais são os direitos dos pacientes?\""
        echo "sara \"Como funciona o sigilo médico?\""
        return 1
    fi

    API_URL="http://localhost:5001"
    USER_ID="user_$(date +%s)_$$"
    
    # Criar sessão
    SESSION_RESPONSE=$(curl -s -X POST "$API_URL/apps/sara-medical-law-agent/users/$USER_ID/sessions" \
      -H "Content-Type: application/json" \
      -d '{"state": {}}' 2>/dev/null)
    
    SESSION_ID=$(echo "$SESSION_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null)
    
    # Enviar mensagem e exibir resposta
    curl -s -X POST "$API_URL/run" \
      -H "Content-Type: application/json" \
      -d "{
        \"appName\": \"sara-medical-law-agent\",
        \"userId\": \"$USER_ID\",
        \"sessionId\": \"$SESSION_ID\",
        \"newMessage\": {
          \"parts\": [{\"text\": \"$1\"}]
        }
      }" 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data and len(data) > 0:
        print(data[0]['content']['parts'][0]['text'])
    else:
        print('❌ Erro: Resposta vazia')
except:
    print('❌ Erro: API não está respondendo')
" 2>/dev/null
}

# Alias ainda mais simples
alias ask_sara='sara'

echo "✅ Função 'sara' carregada!"
echo "💡 Uso: sara \"sua pergunta aqui\""
echo "💡 Ou: ask_sara \"sua pergunta aqui\"" 