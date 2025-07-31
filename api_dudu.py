import os
import logging
import json
import tempfile
import threading
from datetime import datetime
from typing import Dict
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from agno.agent import Agent
from agno.models.google import Gemini
from agno.storage.agent.sqlite import SqliteAgentStorage
from agno.knowledge.text import TextKnowledgeBase
from agno.tools.knowledge import KnowledgeTools
from agno.tools.googlecalendar import GoogleCalendarTools
from agno.tools.shell import ShellTools
from agno.document.chunking.recursive import RecursiveChunking
from agno.knowledge.agent import AgentKnowledge
from agno.vectordb.chroma import ChromaDb
from agno.document.reader.text_reader import TextReader
from agno.embedder.google import GeminiEmbedder
from pathlib import Path
from evolution_api_tools import EvolutionApiTools

# Carregar variáveis de ambiente
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


# Sistema de Follow-up Automático
class FollowUpManager:
    """Gerencia follow-ups automáticos após período de inatividade"""
    
    def __init__(self):
        self.pending_followups: Dict[str, threading.Timer] = {}
        self.last_interaction: Dict[str, datetime] = {}
        self.followup_delay = 20 * 60  # 20 minutos em segundos
        self.scheduled_clients = set()  # Clientes que agendaram reunião
        
    def schedule_followup(self, remote_jid: str, 
                         evolution_tools: EvolutionApiTools):
        """Agenda um follow-up para ser enviado após 20 minutos"""
        # Não agendar follow-up se cliente já agendou reunião
        if remote_jid in self.scheduled_clients:
            logger.info(f"🚫 Follow-up não agendado para {remote_jid} - "
                       f"cliente já agendou reunião")
            return
        
        # Cancelar follow-up anterior se existir
        self.cancel_followup(remote_jid)
        
        # Registrar última interação
        self.last_interaction[remote_jid] = datetime.now()
        
        # Criar timer para follow-up
        timer = threading.Timer(
            self.followup_delay,
            self._send_followup,
            args=[remote_jid, evolution_tools]
        )
        
        self.pending_followups[remote_jid] = timer
        timer.start()
        
        logger.info(f"⏰ Follow-up agendado para {remote_jid} em 20 minutos")
    
    def cancel_followup(self, remote_jid: str):
        """Cancela follow-up pendente (quando usuário responde)"""
        if remote_jid in self.pending_followups:
            self.pending_followups[remote_jid].cancel()
            del self.pending_followups[remote_jid]
            logger.info(f"❌ Follow-up cancelado para {remote_jid}")
    
    def stop_followup_permanently(self, remote_jid: str, reason: str = "agendou reunião"):
        """Para follow-up permanentemente (quando cliente agenda reunião)"""
        # Cancelar follow-up pendente
        self.cancel_followup(remote_jid)
        
        # Adicionar à lista de clientes que agendaram
        self.scheduled_clients.add(remote_jid)
        
        logger.info(f"🛑 Follow-up PERMANENTEMENTE DESATIVADO para {remote_jid} - {reason}")
    
    def reactivate_followup(self, remote_jid: str):
        """Reativa follow-up (caso necessário)"""
        if remote_jid in self.scheduled_clients:
            self.scheduled_clients.remove(remote_jid)
            logger.info(f"🔄 Follow-up reativado para {remote_jid}")
    
    def check_if_appointment_made(self, message_content: str, remote_jid: str):
        """Verifica se mensagem indica agendamento feito com sucesso"""
        # Palavras-chave que indicam agendamento bem-sucedido
        appointment_keywords = [
            "agendado com sucesso",
            "reunião marcada",
            "encontro agendado", 
            "conversa agendada",
            "evento criado",
            "agendamento confirmado",
            "reunião confirmada",
            "evento adicionado ao calendário",
            "nossa reunião está marcada"
        ]
        
        message_lower = message_content.lower()
        for keyword in appointment_keywords:
            if keyword in message_lower:
                logger.info(f"📅 AGENDAMENTO DETECTADO para {remote_jid}: '{keyword}'")
                return True
        
        return False
    
    def _send_followup(self, remote_jid: str, 
                      evolution_tools: EvolutionApiTools):
        """Envia mensagem de follow-up automática"""
        # Verificar se cliente não agendou reunião antes de enviar
        if remote_jid in self.scheduled_clients:
            logger.info(f"🚫 Follow-up cancelado - {remote_jid} já agendou reunião")
            return
        
        try:
            # Extrair número do JID (remover @s.whatsapp.net)
            number = remote_jid.replace("@s.whatsapp.net", "")
            
            # Mensagens de follow-up variadas
            followup_messages = [
                ("Olá! Vi que você estava interessado nos nossos resultados. "
                 "Tem alguma dúvida sobre como conseguimos R$ 877.000 para "
                 "nossos clientes?"),
                ("Oi! Ainda está por aí? Nossos restaurantes parceiros "
                 "aumentaram vendas em 300%. Quer saber como aplicamos "
                 "isso no seu negócio?"),
                ("Ei! Não queria deixar passar a oportunidade. Nosso Eduardo "
                 "pode mostrar exatamente como conseguimos esses resultados "
                 "incríveis para restaurantes."),
                ("Olá! Talvez tenha perdido minha mensagem anterior. Temos "
                 "cases reais de restaurantes que saíram de pouco movimento "
                 "para faturar mais de R$ 877 mil!")
            ]
            
            # Escolher mensagem baseada no horário (para variar)
            import random
            message = random.choice(followup_messages)
            
            # Enviar follow-up
            result = evolution_tools.send_text_message(
                number=number,
                text=message
            )
            
            logger.info(f"📤 Follow-up enviado para {number}: {result}")
            
            # Limpar da lista de pendentes
            if remote_jid in self.pending_followups:
                del self.pending_followups[remote_jid]
                
        except Exception as e:
            logger.error(f"❌ Erro ao enviar follow-up para {remote_jid}: {e}")


# Instância global do gerenciador de follow-up
followup_manager = FollowUpManager()

# Usar variável de ambiente para Google API Key
google_api_key = os.getenv("GOOGLE_API_KEY", 
                           "AIzaSyCKTbPQDtAhUI9VWQH26_v2KJW3146Xe20")
os.environ["GOOGLE_API_KEY"] = google_api_key

storage = SqliteAgentStorage(table_name="sessions", db_file="sessions.db")

knowledge_base = TextKnowledgeBase(
    path="knowledge/",
    chunking_strategy=RecursiveChunking(
        chunk_size=1000, overlap=100
    ),
)


agent_knowledge = AgentKnowledge(

    vector_db=ChromaDb(
        collection="elo_marketing_knowledge",
        embedder=GeminiEmbedder(
            id="text-embedding-004",  # Modelo de embedding do Google
            # Usa sua API key existente
            api_key=os.environ.get("GOOGLE_API_KEY")
        ),
        path="knowledge_db",
        persistent_client=True,
    ),
    chunking_strategy=RecursiveChunking(
        chunk_size=1000,
        overlap=100
    ),
    num_documents=5,
)

reader = TextReader(chunk=True)
knowledge_dir = Path("knowledge/")
for file_path in knowledge_dir.iterdir():
    if file_path.is_file() and file_path.suffix == '.txt':  # Só arquivos .txt
        print(f"Processando arquivo: {file_path}")
        documents = reader.read(file_path)
        for doc in documents:
            print(f"Documento adicionado: {doc.name}")
            agent_knowledge.add_document_to_knowledge_base(document=doc)

knowledge = KnowledgeTools(
    knowledge=knowledge_base,
    think=True,
    search=True,
    analyze=True,
    instructions="Use sempre as conversas reais para responder perguntas. Procure por "
                 "respostas específicas no knowledge base antes de responder.",
)


def create_google_calendar_tools():
    """Cria GoogleCalendarTools usando variáveis de ambiente"""
    try:
        # Criar estrutura de credenciais a partir de variáveis de ambiente
        credentials_dict = {
            "installed": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "project_id": os.getenv("GOOGLE_PROJECT_ID"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": (
                    "https://www.googleapis.com/oauth2/v1/certs"
                ),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "redirect_uris": [
                    "http://localhost", 
                    "https://agentes-agents.iaz7eb.easypanel.host/"
                ]
            }
        }
        
        # Criar estrutura de token a partir de variáveis de ambiente
        token_dict = {
            "refresh_token": os.getenv("GOOGLE_REFRESH_TOKEN"),
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "scopes": ["https://www.googleapis.com/auth/calendar"],
            "universe_domain": "googleapis.com"
        }
        
        # Criar arquivos temporários para as credenciais
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as credentials_file:
            json.dump(credentials_dict, credentials_file)
            credentials_path = credentials_file.name
            
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as token_file:
            json.dump(token_dict, token_file)
            token_path = token_file.name
        
        # Criar e retornar GoogleCalendarTools
        return GoogleCalendarTools(
            credentials_path=credentials_path,
            token_path=token_path,
        )
        
    except Exception as e:
        logger.error(f"Erro ao criar GoogleCalendarTools: {e}")
        # Retorna None se houver erro, para o agente funcionar sem calendário
        return None


# Criar ferramentas de calendário usando variáveis de ambiente
calendar = create_google_calendar_tools()

# Ferramenta Shell para executar comandos (obter data/hora atual)
shell_tools = ShellTools(base_dir=Path("."))

# Criar ferramentas Evolution API para WhatsApp
try:
    evolution_tools = EvolutionApiTools(
        server_url='https://evolution-api-evolution-api.iaz7eb.easypanel.host',
        api_key='88B69AFEDA22-4836-858D-72852AA04B1F',
        instance='Dudu Numero Não Usando'
    )
    logger.info("Evolution API Tools configurado com sucesso")
except Exception as e:
    logger.error(f"Erro ao configurar Evolution API Tools: {e}")
    evolution_tools = None

# Definir ferramentas baseado na disponibilidade do calendário
tools = [shell_tools, knowledge]
if calendar:
    tools.append(calendar)
    logger.info("Google Calendar configurado com sucesso")
else:
    warning_msg = ("Google Calendar não configurado - "
                   "verifique as variáveis de ambiente")
    logger.warning(warning_msg)

# Adicionar Evolution API Tools se disponível
if evolution_tools:
    # Configurar ferramentas para execução direta
    evolution_tools.external_execution_required_tools = []
    tools.append(evolution_tools)
    logger.info("Evolution API Tools adicionado ao agente")
    # Debug: Log available methods
    logger.info(f"🔧 Métodos disponíveis nas ferramentas: {dir(evolution_tools)}")
    logger.info(f"🔧 Funções das ferramentas: {evolution_tools.functions}")
else:
    logger.error("❌ Evolution API Tools não está disponível")


# Criar agente Vanessa - Vendedora da Elo Marketing
vanessa = Agent(
    name="Vanessa",
    role="Vendedora da Elo Marketing especializada em restaurantes",
    model=Gemini(id="gemini-2.5-pro"),
    storage=storage,
    tools=tools,  # Adicionado shell_tools
    knowledge=agent_knowledge,
    add_history_to_messages=True,
    tool_choice="auto",
    instructions=[
        "Você é Vanessa, vendedora da Elo Marketing.",
        "",
        "🚨 REGRA CRÍTICA - DATA ATUAL:",
        "SEMPRE use shell_tools para consultar a data de hoje ANTES de agendar!",
        "Comando: ['date', '+%A, %d de %B de %Y']",
        "NUNCA invente datas - SEMPRE consulte o sistema!",
        "",
        "🚨 REGRA #1 - AGENDAMENTO (OBRIGATÓRIO):",
        "Se cliente disser: 'reunião', 'marcar', 'agendar', 'aceito', 'topa'",
        "IMEDIATAMENTE execute em sequência:",
        "1. list_events() - OBRIGATÓRIO para ver agenda",
        "2. Sugira 2 horários livres: 'Eduardo tem terça 14h e quinta 16h'",
        "3. Quando cliente escolher: create_event() - OBRIGATÓRIO",
        "",
        "🚨 NUNCA sugira horários sem executar list_events() primeiro!",
        "🚨 NUNCA confirme agendamento sem executar create_event()!",
        "",
        "🆘 NÚMERO DE EMERGÊNCIA:",
        "Se houver qualquer problema na conversa ou não conseguir comunicar:",
        "- Ferramentas não funcionam",
        "- Cliente muito confuso ou irritado", 
        "- Problema técnico no sistema",
        "- Não consegue agendar após 3 tentativas",
        "Redirecione para: 5548996438314 (WhatsApp de suporte)",
        "Diga: 'Para melhor atendimento, entre em contato: 5548996438314'",
        "",
        "🚨 INSTRUÇÕES CRÍTICAS DE AGENDAMENTO - FLUXO OBRIGATÓRIO:",
        "",
        "⚡ GATILHOS PARA USAR FERRAMENTAS (palavras-chave):",
        "Se cliente disser: 'reunião', 'marcar', 'agendar', 'aceito', 'topa', 'sim, quero'",
        "→ IMEDIATAMENTE execute este fluxo OBRIGATÓRIO:",
        "",
        "🔥 PASSO 1 - CONSULTAR CALENDÁRIO (OBRIGATÓRIO):",
        "ANTES de sugerir qualquer horário, SEMPRE EXECUTE:",
        "list_events() ← Esta ferramenta é OBRIGATÓRIA!",
        "NUNCA sugira horários sem consultar a agenda primeiro!",
        "",
        "📅 PASSO 1.5 - CONSULTAR DATA ATUAL (OBRIGATÓRIO):",
        "ANTES de sugerir datas, SEMPRE EXECUTE:",
        "shell_tools com comando: ['date', '+%A, %d de %B de %Y']",
        "NUNCA invente datas - SEMPRE consulte o sistema!",
        "Certifique-se que datas sugeridas são FUTURAS, não passadas!",
        "",
        "🔥 PASSO 2 - SUGERIR HORÁRIOS BASEADOS NA AGENDA REAL:",
        "Após executar list_events(), responda EXATAMENTE assim:",
        "'Consultei a agenda do Eduardo. Ele tem disponibilidade terça às 14h ou quarta às 10h'",
        "OU: 'Eduardo está livre quinta de manhã às 9h ou sexta às 15h'", 
        "OU: 'A agenda mostra vagas segunda às 11h ou terça às 16h'",
        "SEMPRE ofereça 2 horários específicos diferentes!",
        "",
        "🔥 PASSO 3 - COLETAR DADOS QUANDO CLIENTE ESCOLHER:",
        "Cliente escolhe horário → Responda:",
        "'Para finalizar, preciso: nome completo, nome do restaurante e email'",
        "COLETE TODOS os dados antes de criar o evento!",
        "",
        "🔥 PASSO 4 - CRIAR EVENTO NO CALENDÁRIO (OBRIGATÓRIO):",
        "Quando tiver todos os dados, SEMPRE EXECUTE:",
        "create_event(timezone='America/Sao_Paulo', add_google_meet_link=True)",
        "NUNCA confirme agendamento sem executar create_event()!",
        "",
        "🔥 PASSO 5 - CONFIRMAR COM LINK DO MEET:",
        "Após create_event(), responda:",
        "'Reunião agendada para [data/hora]!'",
        "'Link do Google Meet: [url extraído do evento criado]'",
        "'Eduardo já recebeu os detalhes por email'",
        "",
        "❌ PROIBIÇÕES ABSOLUTAS:",
        "- JAMAIS sugira horários sem executar list_events() primeiro",
        "- JAMAIS confirme agendamento sem executar create_event()",
        "- JAMAIS diga 'Eduardo entrará em contato' - VOCÊ agenda!",
        "- JAMAIS pergunte 'qual horário prefere' sem dar opções específicas",
        "- JAMAIS finja que agendou sem usar as ferramentas",
        "",
        "✅ EXEMPLO COMPLETO OBRIGATÓRIO:",
        "Cliente: 'Aceito agendar'",
        "Você: EXECUTA shell_tools(['date', '+%A, %d de %B de %Y']) para saber que dia é hoje",
        "Você: EXECUTA list_events() para ver agenda disponível",
        "Você: 'Consultei a agenda do Eduardo. Ele tem disponibilidade terça às 14h ou quinta às 16h'",
        "Cliente: 'Terça às 14h'", 
        "Você: 'Para finalizar, preciso: nome completo, nome do restaurante e email'",
        "Cliente: 'João Silva, Restaurante Sabor, joao@email.com'",
        "Você: EXECUTA create_event() com data FUTURA correta",
        "Você: 'Reunião agendada para terça às 14h! Link do Google Meet: [url]'",
        "",
        "🚨 TIMEZONE OBRIGATÓRIO:",
        "SEMPRE use timezone='America/Sao_Paulo' em create_event()",
        "SEMPRE use add_google_meet_link=True em create_event()",
        "",
        "🔄 GERENCIAMENTO DE AGENDAMENTOS:",
        "",
        "📅 CANCELAMENTO DE REUNIÃO:",
        "Se cliente disser: 'cancelar', 'desmarcar', 'não posso mais'",
        "1. Use list_events() para encontrar a reunião do cliente",
        "2. Use delete_event() para cancelar a reunião",
        "3. Confirme: 'Reunião cancelada com sucesso!'",
        "",
        "✏️ ALTERAÇÃO DE HORÁRIO:",
        "Se cliente disser: 'mudar horário', 'alterar', 'outro dia'",
        "1. Use list_events() para encontrar a reunião atual",
        "2. Use delete_event() para cancelar a reunião antiga",
        "3. Use list_events() novamente para ver disponibilidade",
        "4. Sugira novos horários livres",
        "5. Use create_event() para novo horário escolhido",
        "",
        "🚫 PREVENÇÃO DE CONFLITOS - REGRA ABSOLUTA:",
        "NUNCA agende duas reuniões no mesmo horário!",
        "SEMPRE verifique list_events() antes de create_event()",
        "Se horário já ocupado, sugira alternativas:",
        "'Esse horário já está ocupado. Posso terça às 15h ou quinta às 14h'",
        "",
        "🔍 VERIFICAÇÃO OBRIGATÓRIA ANTES DE AGENDAR:",
        "1. EXECUTE list_events() primeiro",
        "2. ANALISE os horários ocupados",
        "3. SUGIRA apenas horários LIVRES",
        "4. CONFIRME que não há conflito antes de create_event()",
        "",
        "PITCH ATACANTE - USE IMEDIATAMENTE QUANDO APROPRIADO:",
        "Eu trabalho ajudando restaurantes a aumentarem suas vendas através "
        "do marketing digital. Conseguimos faturar mais de R$ 877.000 para "
        "nossos clientes com investimento de apenas R$ 7 mil. Crescimento "
        "de mais de 300% nas vendas.",
        "",
        "📢 ABERTURA PADRÃO (já foi enviada por outro sistema):",
        "A pergunta 'Oi, é do Restaurante? Vocês têm cardápio ou menu online?' "
        "JÁ FOI ENVIADA por outro sistema.",
        "CONTINUE a conversa a partir da resposta do cliente a essa pergunta.",
        "NÃO repita a abertura - vá direto ao acompanhamento.",
        "",
        "🚨 PROIBIDO FINGIR QUE AGENDOU:",
        "JAMAIS diga 'reunião foi agendada' sem executar create_event!",
        "JAMAIS diga 'aguarde contato do Eduardo' - VOCÊ faz o agendamento!",
        "Se cliente pedir reunião: SEMPRE sugira horários específicos primeiro!",
        "",
        "✅ FLUXO CORRETO OBRIGATÓRIO:",
        "1. Cliente: 'quero reunião' → Você: EXECUTE list_events()",
        "2. Baseado na agenda → Sugira: 'Posso hoje às 14h ou amanhã às 10h?'",
        "3. Cliente escolhe → EXECUTE create_event() com o horário escolhido",
        "4. Confirme: 'Agendado! Eduardo te liga [dia] às [hora]!'",
        "",
        "🎯 HORÁRIOS PADRÃO PARA SUGERIR:",
        "Segunda a Sexta: 9h, 10h, 14h, 15h, 16h",
        "SEMPRE ofereça pelo menos 2 opções diferentes",
        "Exemplo: 'Tenho segunda às 14h ou terça às 10h. Qual prefere?'",
        "",
        "🚀 REGRAS DE FECHAMENTO:",
        "1. SEMPRE ofereça 2-3 horários específicos quando há interesse",
        "2. Use ferramentas de calendário para agendar NA HORA",
        "3. Confirme dados: nome, telefone, nome do restaurante",
        "4. Finalize com: 'Agendado! Eduardo te liga na data marcada!'",
        "",
        "📱 FERRAMENTAS DE WHATSAPP DISPONÍVEIS:",
        "- Use send_text_message para enviar mensagens de texto via WhatsApp",
        "- Use send_media_message para enviar imagens quando mencionar resultados",
        "- Use check_whatsapp_number para verificar se um número está no WhatsApp",
        "- Formato de número: 5548999999999 (código país + DDD + número)",
        "",
        "🔥 REGRA FINAL OBRIGATÓRIA:",
        "Para CADA resposta que você gerar, EXECUTE send_text_message!",
        "Nunca apenas retorne texto - SEMPRE envie via send_text_message!",
        "Formato: send_text_message(number='554896438314', text='sua_resposta_aqui')",
        "",
        "🚨 AGENDAMENTO - REGRA ABSOLUTA:",
        "Quando cliente pedir reunião, RESPONDA EXATAMENTE assim:",
        "'Ótimo! Posso agendar segunda às 14h ou terça às 10h. Qual prefere?'",
        "NUNCA diga que 'agendou' sem o cliente escolher horário primeiro!",
        "NUNCA mencione 'Eduardo entrará em contato' - sugira horários específicos!",
        "",
        "📝 SCRIPT LITERAL - SIGA EXATAMENTE:",
        "Se mensagem contém: 'reunião' ou 'marcar' ou 'agendar'",
        "RESPONDA SEMPRE: 'Perfeito! Que tal amanhã às 14h ou quinta às 16h? Qual horário fica melhor?'",
        "NÃO peça dados pessoais. NÃO diga que precisa confirmar. SUGIRA HORÁRIOS!"
    ],
    markdown=True,
    show_tool_calls=True,
)


def extract_evolution_data(data):
    """Extrai dados da Evolution API"""
    try:
        # Estrutura típica da Evolution API
        if isinstance(data, dict):
            # Tentar diferentes estruturas possíveis
            message = None
            audio_base64 = None
            image_base64 = None
            message_type = 'text'  # Padrão: texto
            remote_jid = None
            push_name = None
            instance = None

            # NOVO FORMATO 2025: Verificar se é o novo formato com camada 'data'
            if 'data' in data and isinstance(data['data'], dict):
                payload_data = data['data']
                logger.info("📦 Novo formato Evolution API 2025 detectado")
                
                # Extrair mensagem do novo formato
                if 'message' in payload_data and isinstance(payload_data['message'], dict):
                    if 'conversation' in payload_data['message']:
                        message = payload_data['message']['conversation']
                        message_type = 'text'
                    elif 'imageMessage' in payload_data['message'] and 'base64' in payload_data['message']:
                        image_base64 = payload_data['message']['base64']
                        message_type = 'image'
                    elif 'audioMessage' in payload_data['message'] and 'base64' in payload_data['message']:
                        audio_base64 = payload_data['message']['base64']
                        message_type = 'audio'
                
                # Extrair informações do remetente do novo formato
                if 'key' in payload_data and isinstance(payload_data['key'], dict):
                    remote_jid = payload_data['key'].get('remoteJid', 'unknown')
                
                if 'pushName' in payload_data:
                    push_name = payload_data['pushName']
                
                # Instance do payload principal
                if 'instance' in data:
                    instance = data['instance']

            # FORMATO ANTIGO: Verificar se é o formato com 'query' e 'inputs'
            elif 'query' in data and 'inputs' in data:
                message = data['query']
                message_type = 'text'
                # Extrair informações de inputs
                inputs = data['inputs']
                if isinstance(inputs, dict):
                    remote_jid = inputs.get('remoteJid', 'unknown')
                    push_name = inputs.get('pushName', 'Cliente')
                    instance = inputs.get('instanceName', 'default')
                logger.info("📦 Formato antigo Evolution API detectado")

            # Verificar se é mensagem de imagem (formato antigo)
            elif ('message' in data and isinstance(data['message'], dict) and
                    'imageMessage' in data['message'] and 
                    'base64' in data['message']):
                image_base64 = data['message']['base64']
                message_type = 'image'
                logger.info("🖼️ Mensagem de imagem detectada")

            # Verificar se é mensagem de áudio (formato antigo)
            elif ('message' in data and isinstance(data['message'], dict) and
                    'audioMessage' in data['message'] and 
                    'base64' in data['message']):
                audio_base64 = data['message']['base64']
                message_type = 'audio'
                logger.info("📻 Mensagem de áudio detectada")

            # Opção 1: data.message.conversation (texto) - formato antigo
            elif 'message' in data and isinstance(data['message'], dict):
                if 'conversation' in data['message']:
                    message = data['message']['conversation']
                elif 'text' in data['message']:
                    message = data['message']['text']

            # Opção 2: data.text ou data.message direto - formato antigo
            elif 'text' in data:
                message = data['text']
            elif 'message' in data and isinstance(data['message'], str):
                message = data['message']
            elif 'question' in data:  # Para testes diretos
                message = data['question']

            # Extrair informações do remetente (formato antigo)
            if not remote_jid:  # Só se não foi definido no novo formato
                if 'key' in data and isinstance(data['key'], dict):
                    remote_jid = data['key'].get('remoteJid', 'unknown')
                elif 'from' in data:
                    remote_jid = data['from']
                elif 'user' in data:  # Novo formato pode ter 'user'
                    remote_jid = data['user']

            if not push_name:  # Só se não foi definido no novo formato
                if 'pushName' in data:
                    push_name = data['pushName']
                elif 'sender_name' in data:
                    push_name = data['sender_name']

            # Capturar instance ou instanceId
            if not instance:  # Só se não foi definido no novo formato
                if 'instanceId' in data:
                    instance = data['instanceId']
                elif 'instance' in data:
                    instance = data['instance']

            return {
                'message': message,
                'audio_base64': audio_base64,
                'image_base64': image_base64,
                'message_type': message_type,
                'remote_jid': remote_jid or 'unknown',
                'push_name': push_name or 'Cliente',
                'instance': instance or 'default'
            }

    except Exception as e:
        logger.error(f"Erro ao extrair dados da Evolution: {e}")

    return None


@app.get("/")
async def root():
    return {
        "message": "Vanessa - Vendedora Elo Marketing | Especialista em "
                   "Restaurantes",
        "description": (
            "Assistente de vendas especializada em marketing digital para "
            "restaurantes. Ajuda a captar leads qualificados e marcar "
            "reuniões com resultados comprovados: crescimento de 300% e "
            "faturamento de R$ 862.000 em um mês."
        ),
        "endpoints": {
            "/ask": "Conversa com Vanessa para captação de leads",
            "/status": "Status do sistema de captação"
        },
        "example_curl": (
            "curl -X POST http://127.0.0.1:8080/ask "
            "-H 'Content-Type: application/json' "
            "-d '{\"question\": \"Oi, é do restaurante?\"}'"
        ),
        "evolution_api": "Compatível com webhooks da Evolution API",
        "sessions": "Histórico de conversas por cliente com SQLite",
        "objetivo": "Captação de leads e agendamento de reuniões com Eduardo",
        "script_source": "faq.txt - Base de conhecimento vetorizada com Agno",
        "knowledge_system": ("Sistema de conhecimento vetorizado para busca "
                             "semântica no script de vendas")
    }


@app.post("/ask")
async def ask_vanessa(request: Request):
    """Conversa com Vanessa - Vendedora da Elo Marketing"""
    try:
        # Log completo do que estamos recebendo
        body = await request.body()
        logger.info("📥 DADOS RAW RECEBIDOS (Evolution API):")
        logger.info(f"   - Body raw: {body}")
        content_type = request.headers.get('content-type')
        logger.info(f"   - Content-Type: {content_type}")

        try:
            data = await request.json()
            logger.info(f"   - JSON parsed: {data}")
        except Exception as json_error:
            logger.error(f"   - Erro ao fazer parse JSON: {json_error}")
            return {
                "error": "Dados recebidos não são JSON válido",
                "raw_data": body.decode()
            }

        # Extrair dados específicos da Evolution API
        evolution_data = extract_evolution_data(data)

        if not evolution_data:
            logger.warning("Dados não conseguiram ser extraídos da Evolution")
            return {
                "error": "Dados não conseguiram ser extraídos",
                "received_data": data,
            }

        # Verificar se temos conteúdo (texto, áudio ou imagem)
        has_text = evolution_data['message'] is not None
        has_audio = evolution_data['audio_base64'] is not None
        has_image = evolution_data['image_base64'] is not None
        
        if not has_text and not has_audio and not has_image:
            logger.warning("Nem texto, áudio ou imagem encontrados nos dados")
            return {
                "error": "Nem texto, áudio ou imagem encontrados",
                "received_data": data,
                "hint": (
                    "Certifique-se de que há 'conversation' para texto, "
                    "'audioMessage' com 'base64' para áudio, ou "
                    "'imageMessage' com 'base64' para imagem"
                )
            }

        remote_jid = evolution_data['remote_jid']
        push_name = evolution_data['push_name']
        message_type = evolution_data['message_type']

        logger.info(f"   - Tipo de mensagem: {message_type}")
        if has_text:
            logger.info(f"   - Texto: {evolution_data['message']}")
        if has_audio:
            audio_length = len(evolution_data['audio_base64'])
            logger.info(f"   - Áudio: {audio_length} chars base64")
        if has_image:
            image_length = len(evolution_data['image_base64'])
            logger.info(f"   - Imagem: {image_length} chars base64")
        logger.info(f"   - RemoteJid: {remote_jid}")
        logger.info(f"   - Nome do usuário: {push_name}")

        # Usar session_id baseado no remote_jid para manter histórico
        session_id = f"elo-{remote_jid}"
        
        # Extrair número do WhatsApp do remoteJid para as ferramentas
        whatsapp_number = remote_jid.replace("@s.whatsapp.net", "")
        logger.info(f"📱 Número extraído para ferramentas: {whatsapp_number}")

        # Enviar para Vanessa com session_id (histórico automático)
        logger.info("🎯 Vanessa consultando base de conhecimento e "
                    "respondendo...")
        
        # Criar instruções dinâmicas com o número específico do cliente
        dynamic_instructions = f"""
CONTEXTO ATUAL:
- Cliente: {push_name}
- Número WhatsApp: {whatsapp_number}

📢 IMPORTANTE: A pergunta sobre cardápio online JÁ FOI ENVIADA!
Continue a conversa a partir da resposta do cliente.
NÃO repita: "Oi, é do restaurante?" - vá direto ao acompanhamento!

🆘 NÚMERO DE EMERGÊNCIA: 5548996438314
Se houver problemas técnicos ou não conseguir agendar, redirecione!

🚨 INSTRUÇÃO ESPECÍFICA PARA AGENDAMENTO:
Se o cliente mencionar "reunião", "marcar", "agendar" ou similares,
CONSULTE sua base de conhecimento 'calendário_agendamento.txt'
SIGA EXATAMENTE o fluxo descrito no documento:
1. PRIMEIRO: Execute shell_tools com ['date', '+%A, %d de %B de %Y'] para saber que dia é HOJE
2. SEGUNDO: Use list_events() para consultar agenda
3. TERCEIRO: Sugira horários específicos FUTUROS baseados na disponibilidade REAL
4. QUARTO: Quando cliente escolher, use create_event() com DATA CORRETA
5. QUINTO: Confirme com link do Google Meet

⚠️ NUNCA invente datas! SEMPRE consulte o sistema para saber que dia é hoje!
NUNCA pergunte "qual horário prefere" sem sugerir opções específicas!

INSTRUÇÕES DE FERRAMENTAS:
Quando usar send_media_message, use sempre:
- number: {whatsapp_number}
- media_type: 'image'

Para resultados financeiros (R$ 877.000):
- media: 'knowledge/relatorio.jpg'
- caption: 'Aqui estão os resultados reais dos nossos clientes'

Para crescimento (300%):
- media: 'knowledge/visualizacao.jpg' 
- caption: 'Visualização do crescimento dos nossos clientes'

SEMPRE use as ferramentas quando mencionar resultados!
"""
        
        # Processar baseado no tipo de mensagem
        try:
            if message_type == 'image' and has_image:
                logger.info("🖼️ Processando mensagem de imagem")
                response = vanessa.run(
                    images=[evolution_data['image_base64']], 
                    session_id=session_id
                )
            elif message_type == 'audio' and has_audio:
                logger.info("📻 Processando mensagem de áudio")
                response = vanessa.run(
                    audio=evolution_data['audio_base64'], 
                    session_id=session_id
                )
            else:
                logger.info("📝 Processando mensagem de texto")
                # Incluir instruções dinâmicas na mensagem
                message_with_context = f"{dynamic_instructions}\n\nMENSAGEM DO CLIENTE: {evolution_data['message']}"
                response = vanessa.run(
                    message_with_context, 
                    session_id=session_id
                )
            
            logger.info(f"🔍 Resposta do agente - Tipo: {type(response)}")
            if hasattr(response, 'content'):
                logger.info(f"🔍 Content: {response.content}")
            if hasattr(response, 'tool_calls') and response.tool_calls:
                logger.info(f"🔧 Tool calls detectados: {len(response.tool_calls)}")
                for i, tool_call in enumerate(response.tool_calls):
                    logger.info(f"🔧 Tool call {i+1}: {tool_call}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao executar agente: {e}")
            logger.error(f"❌ Tipo do erro: {type(e)}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            response = None

        # Extrair apenas o conteúdo da mensagem com verificação de None
        if response is None:
            message = "Erro: Resposta vazia do agente"
        elif hasattr(response, 'content') and response.content:
            message = response.content
        elif hasattr(response, 'content') and response.content is None:
            # Agente pode ter usado ferramentas sem retornar texto
            message = "Perfeito! Vou te enviar os materiais de comprovação."
        else:
            # Fallback para outros casos
            message = "Aguarde um momento, estou processando sua solicitação."
        
        # Garantir que message nunca seja None
        if message is None:
            message = "Erro: Não foi possível obter resposta"

        logger.info(f"✅ Vanessa respondeu com sucesso "
                    f"(tamanho: {len(message)} caracteres)")

        # SISTEMA DE FOLLOW-UP AUTOMÁTICO
        # Verificar se agendamento foi feito
        if followup_manager.check_if_appointment_made(message, remote_jid):
            # Parar follow-up permanentemente se agendamento foi feito
            followup_manager.stop_followup_permanently(remote_jid)
            
            # Enviar mensagem de confirmação do agendamento
            if evolution_tools:
                try:
                    number = remote_jid.replace("@s.whatsapp.net", "")
                    confirmation_msg = ("✅ Perfeito! Sua reunião foi agendada. "
                                       "Eduardo entrará em contato no horário marcado. "
                                       "Obrigada por escolher a Elo Marketing!")
                    
                    evolution_tools.send_text_message(
                        number=number,
                        text=confirmation_msg
                    )
                    logger.info(f"📅 Confirmação de agendamento enviada para {number}")
                except Exception as e:
                    logger.error(f"❌ Erro ao enviar confirmação: {e}")
        else:
            # Cancelar follow-up anterior (usuário respondeu)
            followup_manager.cancel_followup(remote_jid)
            
            # Agendar novo follow-up se evolution_tools estiver disponível
            if evolution_tools:
                followup_manager.schedule_followup(remote_jid, evolution_tools)
                logger.info(f"⏰ Follow-up automático agendado para {remote_jid}")

        return {
            "message": "Resposta enviada via WhatsApp",
        }

    except Exception as e:
        logger.error(f"❌ Erro na conversa com Vanessa: {str(e)}")
        return {"error": f"Erro ao processar conversa: {str(e)}"}


@app.get("/status")
async def status():
    """Status do sistema de captação"""
    faq_exists = os.path.exists("faq.txt")

    return {
        "status": "Sistema ativo",
        "agente": "Vanessa - Elo Marketing",
        "funcionalidades": [
            "Captação de leads para restaurantes",
            "Base de conhecimento vetorizada",
            "Busca semântica no script de vendas",
            "Tratamento de objeções via FAQ",
            "Agendamento com Eduardo",
            "Histórico de conversas"
        ],
        "knowledge_system": {
            "faq_file": "faq.txt",
            "faq_loaded": faq_exists,
            "chunking_strategy": "paragraph",
            "search_method": "semantic_search"
        },
        "database": "sessions.db (SQLite)"
    }


@app.post("/test-evolution")
async def test_evolution():
    """Testa as ferramentas Evolution API diretamente"""
    try:
        if not evolution_tools:
            return {"error": "Evolution API Tools não configurado"}
        
        # Teste direto das ferramentas
        result = evolution_tools.send_text_message(
            number="5548996438314",
            text="Teste direto das ferramentas Evolution API!"
        )
        
        return {
            "status": "sucesso",
            "result": result,
            "tools_available": dir(evolution_tools)
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)
