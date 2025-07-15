# 🎯 Sara - Modo Super Simples

## 🚀 3 Formas Diferentes de Usar a Sara

### 1. 📝 **Script Simples** (Recomendado)

```bash
# Usar o script criado
./sara_simples.sh "Quais são os direitos dos pacientes?"
```

**Vantagens:**
- ✅ Não precisa gerenciar sessão
- ✅ Uma linha só
- ✅ Resposta limpa

### 2. 🔧 **Função Shell** (Mais Prático)

```bash
# Carregar a função (uma vez só)
source sara_function.sh

# Depois usar como comando
sara "Como funciona o sigilo médico?"
# ou
ask_sara "O que diz a lei sobre telemedicina?"
```

**Vantagens:**
- ✅ Comando super curto
- ✅ Disponível até fechar terminal
- ✅ Dois aliases disponíveis

### 3. 🌐 **cURL Manual** (Completo)

```bash
# Etapa 1: Criar sessão
SESSION_RESPONSE=$(curl -s -X POST http://localhost:5001/apps/sara-medical-law-agent/users/test/sessions -H "Content-Type: application/json" -d '{"state": {}}')

# Etapa 2: Extrair Session ID
SESSION_ID=$(echo "$SESSION_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

# Etapa 3: Enviar pergunta
curl -X POST http://localhost:5001/run \
  -H "Content-Type: application/json" \
  -d "{
    \"appName\": \"sara-medical-law-agent\",
    \"userId\": \"test\",
    \"sessionId\": \"$SESSION_ID\",
    \"newMessage\": {
      \"parts\": [{\"text\": \"Sua pergunta aqui\"}]
    }
  }"
```

## 🎯 **Exemplos Prontos para Testar**

### Script Simples:
```bash
./sara_simples.sh "Quais são os direitos básicos dos pacientes?"
./sara_simples.sh "Como funciona o consentimento informado?"
./sara_simples.sh "O que diz a lei sobre prontuário médico?"
./sara_simples.sh "Quais são as regras da telemedicina?"
```

### Função Shell:
```bash
source sara_function.sh  # Carregar função

sara "Quais são os direitos dos pacientes?"
sara "Como funciona o sigilo médico?" 
sara "O que fazer em caso de erro médico?"
ask_sara "Responsabilidades do CFM?"
```

## 🔄 **Script de Setup Completo**

```bash
#!/bin/bash
# setup_sara.sh - Configurar tudo de uma vez

echo "🏥 Configurando Sara - Modo Simples"

# Tornar scripts executáveis
chmod +x sara_simples.sh
chmod +x curl_exemplo_sara.sh

# Carregar função
source sara_function.sh

echo ""
echo "✅ Configuração completa!"
echo ""
echo "📋 Como usar:"
echo "1. Script: ./sara_simples.sh \"pergunta\""
echo "2. Função: sara \"pergunta\""
echo "3. Alias: ask_sara \"pergunta\""
echo ""
echo "🎯 Teste agora:"
echo "sara \"Quais são os direitos dos pacientes?\""
```

## ⚙️ **Configuração da Porta**

**Se estiver rodando em porta diferente:**

```bash
# Para porta 5000
sed -i 's/localhost:5001/localhost:5000/g' sara_simples.sh sara_function.sh

# Para EasyPanel
sed -i 's/http:\/\/localhost:5001/https:\/\/seu-dominio.easypanel.host/g' sara_simples.sh sara_function.sh
```

## 🚨 **Troubleshooting**

### Erro: "API não está rodando"
```bash
# Verificar se API está rodando
curl http://localhost:5001/list-apps

# Se não estiver, iniciar:
adk api_server --port=5001
```

### Erro: "Command not found: sara"
```bash
# Recarregar função
source sara_function.sh
```

### Erro: "Permission denied"
```bash
# Dar permissão aos scripts
chmod +x sara_simples.sh curl_exemplo_sara.sh
```

## 📱 **Integração Permanente**

**Para ter a função sempre disponível:**

```bash
# Adicionar ao ~/.bashrc ou ~/.zshrc
echo "source $(pwd)/sara_function.sh" >> ~/.bashrc
# ou
echo "source $(pwd)/sara_function.sh" >> ~/.zshrc
```

## 🎉 **Resultado Final**

Agora você pode conversar com Sara usando:

```bash
# Opção 1 (Script)
./sara_simples.sh "Pergunta sobre direito médico"

# Opção 2 (Função)
sara "Pergunta sobre direito médico"

# Opção 3 (Alias)
ask_sara "Pergunta sobre direito médico"
```

**Tudo automatizado! Sessões criadas automaticamente, resposta limpa! 🚀** 