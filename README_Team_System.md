# 🤖 Team Elo Marketing - Sistema Completo

## 📋 Visão Geral

Sistema inteligente com **dois agentes especializados** trabalhando em equipe:

- **👩‍💼 Vanessa** - Vendedora atacante especializada em captação de leads
- **👨‍💼 Eduardo** - Especialista em lembretes e reuniões técnicas

## 🏗️ Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    TEAM ELO MARKETING                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  👩‍💼 VANESSA (Vendedora)     │  👨‍💼 EDUARDO (Especialista)      │
│  ┌─────────────────────────  │  ─────────────────────────┐   │
│  │ • Captação de leads       │  │ • Lembretes automáticos │   │
│  │ • Qualificação prospects  │  │ • Reuniões técnicas     │   │
│  │ • Agendamento c/ Eduardo  │  │ • Fechamento vendas     │   │
│  └─────────────────────────  │  ─────────────────────────┘   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                  SISTEMA DE LEMBRETES                       │
│  📅 24h antes  │  ⏰ 1h antes  │  🔔 10min antes             │
│  "Prepare-se"  │  "É hoje!"   │  "Começando!"               │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 Fluxo de Trabalho

### 1️⃣ **Primeiro Contato (Vanessa)**
- Cliente chega via WhatsApp
- Vanessa faz abordagem atacante
- Apresenta resultados: R$ 877.000
- Qualifica interesse do lead

### 2️⃣ **Agendamento (Vanessa)**
- Vanessa agenda reunião com Eduardo
- Sistema detecta automaticamente
- Inclui `AGENDAMENTO_REALIZADO:` na resposta

### 3️⃣ **Lembretes Automáticos (Eduardo)**
- **24h antes**: Preparação e expectativa
- **1h antes**: Confirmação e instruções  
- **10min antes**: Aviso de início

### 4️⃣ **Reunião Técnica (Eduardo)**
- Eduardo conduz apresentação
- Demonstra cases de sucesso
- Fecha proposta comercial

## 📱 Sistema de Lembretes

### ⏰ **Horários Configurados**

| **Lembrete** | **Quando** | **Objetivo** | **Exemplo** |
|--------------|------------|--------------|-------------|
| 📅 **24h antes** | Dia anterior até 18h | Preparação | "Sua reunião é AMANHÃ às 14h. Prepare suas dúvidas!" |
| ⏰ **1h antes** | 1 hora antes | Confirmação | "Sua reunião é em 1 HORA! Eduardo entrará em contato." |
| 🔔 **10min antes** | 10 minutos antes | Início | "Em 10 MINUTOS Eduardo iniciará nossa reunião!" |

### 🎯 **Detecção Automática**

O sistema detecta agendamentos através de palavras-chave:
- "agendado com sucesso"
- "reunião marcada" 
- "evento criado"
- "nossa reunião está marcada"

### 📅 **Extração de Data/Hora**

Patterns suportados:
- `"amanhã às 14h"` → Amanhã 14:00
- `"hoje às 15h30"` → Hoje 15:30
- `"14/12 às 10h"` → 14/12 10:00

## 🚀 Como Usar

### **Arquivo Principal:** `team_elo_marketing.py`

```bash
# Executar o Team
python3 team_elo_marketing.py
```

### **Endpoints Disponíveis:**

- `POST /team` - Conversa com o Team
- `GET /status` - Status do sistema
- `GET /` - Informações do Team

### **Porta:** `8081`

## 📊 Funcionalidades

### ✅ **Implementado**

- [x] Team com dois agentes especializados
- [x] Detecção automática de agendamentos
- [x] Sistema de lembretes em 3 horários
- [x] Integração Evolution API
- [x] Base de conhecimento compartilhada
- [x] Storage separado para conversas
- [x] Divisão inteligente de responsabilidades

### 🎯 **Benefícios**

- **Cliente nunca esquece** da reunião
- **Eduardo sabe exatamente** quando agir
- **Vanessa foca** em captar novos leads
- **Sistema 100% automatizado**
- **Experiência profissional** garantida

## 🔧 Configuração

### **Variáveis de Ambiente Necessárias:**

```env
# Google API Key para Gemini
GOOGLE_API_KEY=sua_chave_aqui

# Google Calendar (opcional)
GOOGLE_CLIENT_ID=seu_client_id
GOOGLE_CLIENT_SECRET=seu_client_secret
GOOGLE_PROJECT_ID=seu_project_id
GOOGLE_REFRESH_TOKEN=seu_refresh_token
```

### **Evolution API:**
- Configurada diretamente no código
- Server: `https://evolution-api-evolution-api.iaz7eb.easypanel.host`
- Instance: `Dudu Numero Não Usando`

## 📈 Exemplo de Uso

```python
# Cliente conversa com Vanessa
POST /team
{
  "message": {
    "conversation": "Olá, vocês fazem marketing para restaurantes?"
  },
  "key": {
    "remoteJid": "5548999999999@s.whatsapp.net"
  },
  "pushName": "João Silva"
}

# Vanessa responde e agenda com Eduardo
# Sistema detecta: "AGENDAMENTO_REALIZADO: amanhã às 14h com João Silva"
# Lembretes são automaticamente agendados
```

## 🛠️ Estrutura de Arquivos

```
team_elo_marketing.py    # Sistema completo do Team
api_dudu.py             # Sistema original (Vanessa individual)
evolution_api_tools.py  # Ferramentas WhatsApp
knowledge/              # Base de conhecimento
├── faq.txt            # FAQ de vendas
├── calendário_agendamento.txt
└── outros arquivos...
```

## 📞 Suporte

### **Como Testar:**

1. Execute `python3 team_elo_marketing.py`
2. Acesse `http://localhost:8081`
3. Teste via POST para `/team`
4. Monitore logs para acompanhar funcionamento

### **Logs Importantes:**

- `📅 AGENDAMENTO DETECTADO` - Sistema identificou agendamento
- `⏰ Lembrete agendado` - Timers configurados
- `📤 Lembrete enviado` - Mensagens entregues

## 🎉 Resultado Final

**Sistema profissional que:**
- Capta leads com Vanessa
- Agenda automaticamente com Eduardo  
- Envia lembretes inteligentes
- Garante que nenhuma reunião seja perdida
- Maximiza conversão de leads em clientes

**🎯 Vanessa + Eduardo = Team imbatível para vendas B2B!** 