# Guia de Deploy no EasyPanel

## Problemas Resolvidos ✅

A configuração do Docker Compose foi otimizada para o EasyPanel, resolvendo os seguintes conflitos:

- ❌ **container_name removido** - O EasyPanel gerencia nomes automaticamente
- ❌ **ports substituído por expose** - O EasyPanel gerencia mapeamento de portas  
- ❌ **redes personalizadas removidas** - O EasyPanel usa rede padrão
- ❌ **volumes simplificados** - Evita conflitos desnecessários

## Passo a Passo Atualizado

### 1. Repositório Público ✅
Seu repositório já está público: `https://github.com/Alexvjunior/adk-agents.git`

### 2. Configuração no EasyPanel

1. **Criar Novo Serviço**
   - Clique em "Serviço" 
   - Selecione "Docker Compose"

2. **Configurar Repositório**
   - **URL**: `https://github.com/Alexvjunior/adk-agents.git`
   - **Branch**: `master`
   - **Caminho do Build**: `/` (raiz)
   - **Arquivo Docker Compose**: `docker-compose.yml`

3. **Variáveis de Ambiente** 
   ```
   GOOGLE_API_KEY=sua_chave_api_google_aqui
   EASYPANEL_DOMAIN=seu-dominio.com
   ```

### 3. Configuração de Rede no EasyPanel

Como removemos as configurações de porta personalizadas:

1. **O EasyPanel automaticamente:**
   - Gerencia o mapeamento de portas
   - Detecta a porta 5000 via `expose`
   - Configura o proxy reverso via Traefik

2. **Verificar após deploy:**
   - Vá em "Rede" no painel do serviço
   - Confirme que a porta 5000 está mapeada
   - Configure domínio customizado se necessário

### 4. Verificação de Saúde

O healthcheck está configurado para:
- **Endpoint**: `http://localhost:5000/list-apps`  
- **Intervalo**: 30 segundos
- **Timeout**: 10 segundos
- **Tentativas**: 3
- **Período inicial**: 40 segundos

### 5. Acesso à API

Após o deploy bem-sucedido:

**Endpoints disponíveis:**
- `GET /list-apps` - Lista agentes disponíveis
- `GET /docs` - Documentação OpenAPI
- `POST /apps/sara-medical-law-agent/users/{user_id}/sessions` - Criar sessão
- `POST /run` - Executar consulta

**Exemplo de teste:**
```bash
# Verificar se está funcionando
curl https://seu-dominio.com/list-apps

# Ver documentação
curl https://seu-dominio.com/docs
```

## Troubleshooting

### Se ainda houver conflitos:

1. **Verificar logs do container:**
   - No EasyPanel, vá em "Logs" do serviço
   - Procure por erros de inicialização

2. **Verificar variáveis de ambiente:**
   - Confirme que `GOOGLE_API_KEY` está definida
   - Verifique se não há caracteres especiais

3. **Verificar porta:**
   - O serviço deve expor porta 5000
   - O EasyPanel deve mapear automaticamente

4. **Recrear serviço se necessário:**
   - Delete o serviço atual
   - Recrie com a configuração corrigida

### Logs Importantes

Se houver problemas, verifique estes logs:
```
- Container startup logs
- Traefik proxy logs  
- Application logs (erros da API)
```

## Próximos Passos

1. **Deploy** - Use a configuração corrigida
2. **Teste** - Verifique endpoints básicos
3. **Configuração de domínio** - Configure seu domínio personalizado
4. **Monitoramento** - Configure alertas de saúde se necessário

A configuração agora está otimizada para o EasyPanel e deve deployar sem conflitos! 🚀 