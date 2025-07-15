# Configuração de Variáveis de Ambiente

## Variáveis Obrigatórias no EasyPanel

Configure estas variáveis no painel do EasyPanel:

```env
GOOGLE_API_KEY=your-google-api-key-here
PORT=5000
PYTHONPATH=/app
```

## Como obter GOOGLE_API_KEY

1. Acesse [Google AI Studio](https://aistudio.google.com/)
2. Clique em "Get API Key"
3. Crie uma nova chave
4. Copie a chave para usar no EasyPanel

## Configuração no EasyPanel

1. No painel do EasyPanel, vá em "Environment Variables"
2. Adicione:
   - Nome: `GOOGLE_API_KEY`, Valor: `sua-chave-aqui`
   - Nome: `PORT`, Valor: `5000`
   - Nome: `PYTHONPATH`, Valor: `/app`

## Opcional: Service Account

Se preferir usar Service Account ao invés de API Key:

```env
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

Neste caso, você precisará incluir o arquivo JSON no build do container. 