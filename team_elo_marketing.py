#!/usr/bin/env python3
"""
Team Elo Marketing - Agno Framework
Vanessa (Vendedora) + Eduardo (Especialista em Lembretes)
"""

import os
import logging
import json
import tempfile
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from agno.agent import Agent
from agno.team import Team
from agno.models.google import Gemini
from agno.storage.agent.sqlite import SqliteAgentStorage
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


# Sistema de Lembretes Automáticos
class ReminderManager:
    """Gerencia lembretes automáticos para agendamentos"""
    
    def __init__(self):
        self.scheduled_reminders: Dict[str, List[threading.Timer]] = {}
        self.appointments: Dict[str, dict] = {}  # Armazena dados dos agendamentos
        
    def schedule_appointment_reminders(
        self, 
        remote_jid: str, 
        appointment_datetime: datetime,
        evolution_tools: EvolutionApiTools,
        client_name: str = "Cliente"
    ):
        """Agenda lembretes para um agendamento"""
        
        # Cancelar lembretes anteriores se existirem
        self.cancel_reminders(remote_jid)
        
        # Armazenar dados do agendamento
        self.appointments[remote_jid] = {
            "datetime": appointment_datetime,
            "client_name": client_name,
            "created_at": datetime.now()
        }
        
        # Calcular horários dos lembretes
        reminders = []
        now = datetime.now()
        
        # Lembrete 1: 24h antes (se agendamento for mais de 24h no futuro)
        reminder_24h = appointment_datetime - timedelta(hours=24)
        if reminder_24h > now:
            delay_24h = (reminder_24h - now).total_seconds()
            if delay_24h > 0:
                timer_24h = threading.Timer(
                    delay_24h,
                    self._send_24h_reminder,
                    args=[remote_jid, evolution_tools, appointment_datetime, client_name]
                )
                reminders.append(timer_24h)
                timer_24h.start()
                logger.info(f"📅 Lembrete 24h agendado para {remote_jid} em {delay_24h/3600:.1f} horas")
        
        # Lembrete 2: 1h antes
        reminder_1h = appointment_datetime - timedelta(hours=1)
        if reminder_1h > now:
            delay_1h = (reminder_1h - now).total_seconds()
            if delay_1h > 0:
                timer_1h = threading.Timer(
                    delay_1h,
                    self._send_1h_reminder,
                    args=[remote_jid, evolution_tools, appointment_datetime, client_name]
                )
                reminders.append(timer_1h)
                timer_1h.start()
                logger.info(f"⏰ Lembrete 1h agendado para {remote_jid} em {delay_1h/3600:.1f} horas")
        
        # Lembrete 3: 10 minutos antes
        reminder_10m = appointment_datetime - timedelta(minutes=10)
        if reminder_10m > now:
            delay_10m = (reminder_10m - now).total_seconds()
            if delay_10m > 0:
                timer_10m = threading.Timer(
                    delay_10m,
                    self._send_10m_reminder,
                    args=[remote_jid, evolution_tools, appointment_datetime, client_name]
                )
                reminders.append(timer_10m)
                timer_10m.start()
                logger.info(f"⏱️ Lembrete 10min agendado para {remote_jid} em {delay_10m/60:.1f} minutos")
        
        # Armazenar todos os timers
        self.scheduled_reminders[remote_jid] = reminders
        
        logger.info(f"✅ {len(reminders)} lembretes agendados para {remote_jid}")
    
    def cancel_reminders(self, remote_jid: str):
        """Cancela todos os lembretes de um cliente"""
        if remote_jid in self.scheduled_reminders:
            for timer in self.scheduled_reminders[remote_jid]:
                timer.cancel()
            del self.scheduled_reminders[remote_jid]
            logger.info(f"❌ Lembretes cancelados para {remote_jid}")
    
    def _send_24h_reminder(self, remote_jid: str, evolution_tools, appointment_dt: datetime, client_name: str):
        """Envia lembrete 24h antes com confirmação"""
        try:
            number = remote_jid.replace("@s.whatsapp.net", "")
            formatted_time = appointment_dt.strftime("%d/%m às %H:%M")
            
            # Gerar link do Google Meet
            meet_link = self._generate_meet_link(appointment_dt, client_name)
            
            message = (f"Oi {client_name}! "
                      f"Lembra da nossa conversa sobre marketing digital? "
                      f"Sua reunião com Eduardo está marcada para amanhã ({formatted_time}). "
                      f"\n\nSó me confirma se está tudo certo? "
                      f"Se conseguir ir, só responder 'sim'. "
                      f"Se não rolar, me avisa que a gente remarca numa boa! "
                      f"\n\nAh, e se prepare que o Eduardo vai te mostrar uns cases bem legais!")
            
            evolution_tools.send_text_message(number=number, text=message)
            logger.info(f"📅 Lembrete 24h (confirmação) enviado para {number}")
            
            # Armazenar que estamos aguardando confirmação
            self.appointments[remote_jid]["awaiting_confirmation"] = True
            self.appointments[remote_jid]["meet_link"] = meet_link
            
        except Exception as e:
            logger.error(f"❌ Erro no lembrete 24h para {remote_jid}: {e}")
    
    def _send_1h_reminder(self, remote_jid: str, evolution_tools, appointment_dt: datetime, client_name: str):
        """Envia lembrete 1h antes com link do Meet"""
        try:
            number = remote_jid.replace("@s.whatsapp.net", "")
            formatted_time = appointment_dt.strftime("%H:%M")
            
            # Buscar link do Meet
            meet_link = self.appointments.get(remote_jid, {}).get("meet_link", "")
            
            message = (f"E aí {client_name}! "
                      f"Falta só 1 hora para nossa reunião ({formatted_time})! "
                      f"\n\nJá deixei o link pronto aqui:\n{meet_link}"
                      f"\n\nÉ só entrar no horário. "
                      f"Ah, e tenha em mãos as informações do seu restaurante que vai ser bem útil!")
            
            evolution_tools.send_text_message(number=number, text=message)
            logger.info(f"⏰ Lembrete 1h enviado para {number}")
            
        except Exception as e:
            logger.error(f"❌ Erro no lembrete 1h para {remote_jid}: {e}")
    
    def _send_10m_reminder(self, remote_jid: str, evolution_tools, appointment_dt: datetime, client_name: str):
        """Envia lembrete 10min antes"""
        try:
            number = remote_jid.replace("@s.whatsapp.net", "")
            
            # Buscar link do Meet
            meet_link = self.appointments.get(remote_jid, {}).get("meet_link", "")
            
            message = (f"Últimos 10 minutos, {client_name}! "
                      f"\n\nÉ agora! Pode entrar no link:\n{meet_link}"
                      f"\n\nEduardo já está te esperando. "
                      f"Vai ser demais te mostrar como nossos clientes conseguiram esses resultados!")
            
            evolution_tools.send_text_message(number=number, text=message)
            logger.info(f"⏱️ Lembrete 10min enviado para {number}")
            
        except Exception as e:
            logger.error(f"❌ Erro no lembrete 10min para {remote_jid}: {e}")
    
    def _generate_meet_link(self, appointment_dt: datetime, client_name: str) -> str:
        """Gera link do Google Meet para a reunião"""
        try:
            # Para esta demo, vamos usar um link fixo do Meet
            # Em produção, isso seria integrado com Google Calendar API
            base_meet_url = "https://meet.google.com/lookup/"
            
            # Gerar código único baseado na data e cliente
            import hashlib
            unique_data = f"{appointment_dt.isoformat()}-{client_name}-elo-marketing"
            meet_code = hashlib.md5(unique_data.encode()).hexdigest()[:10]
            
            # Link personalizado (em produção seria criado via Google Calendar)
            meet_link = f"{base_meet_url}{meet_code}"
            
            logger.info(f"📞 Link do Meet gerado para {client_name}: {meet_link}")
            return meet_link
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar link do Meet: {e}")
            return "https://meet.google.com/new"  # Link padrão como fallback
    
    def handle_confirmation_response(self, remote_jid: str, message: str, evolution_tools) -> bool:
        """Processa resposta de confirmação do cliente"""
        try:
            if remote_jid not in self.appointments:
                return False
                
            appointment = self.appointments[remote_jid]
            if not appointment.get("awaiting_confirmation", False):
                return False
            
            message_lower = message.lower().strip()
            number = remote_jid.replace("@s.whatsapp.net", "")
            client_name = appointment.get("client_name", "Cliente")
            meet_link = appointment.get("meet_link", "")
            
            if any(word in message_lower for word in ["sim", "confirmo", "vou", "participar", "ok"]):
                # Confirmação positiva
                appointment["confirmed"] = True
                appointment["awaiting_confirmation"] = False
                
                confirmation_msg = (f"Perfeito, {client_name}! "
                                   f"Anotado aqui que você vem amanhã. "
                                   f"\n\nJá deixo o link da reunião salvo para você:\n{meet_link}"
                                   f"\n\nVou te lembrar uma hora antes também. "
                                   f"Até amanhã às {appointment['datetime'].strftime('%H:%M')}!")
                
                evolution_tools.send_text_message(number=number, text=confirmation_msg)
                logger.info(f"✅ Agendamento confirmado para {client_name}")
                return True
                
            elif any(word in message_lower for word in ["não", "nao", "cancelar", "remarcar", "outro"]):
                # Cancelamento ou remarcação
                appointment["confirmed"] = False
                appointment["awaiting_confirmation"] = False
                
                # Cancelar lembretes restantes
                self.cancel_reminders(remote_jid)
                
                reschedule_msg = (f"Tranquilo, {client_name}! "
                                 f"Sem problemas. Quando você tiver um tempo melhor me avisa. "
                                 f"Que dia e horário seria bom para você?")
                
                evolution_tools.send_text_message(number=number, text=reschedule_msg)
                logger.info(f"📅 Agendamento cancelado para remarcação: {client_name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar confirmação: {e}")
            return False
    
    def parse_appointment_datetime(self, message: str) -> Optional[datetime]:
        """Extrai data/hora do agendamento da mensagem"""
        try:
            # Buscar padrões comuns de data/hora nas mensagens
            import re
            
            # Padrão: "amanhã às 14h" ou "amanhã às 14:00"
            tomorrow_pattern = r"amanhã às (\d{1,2})(?::(\d{2}))?h?"
            match = re.search(tomorrow_pattern, message.lower())
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2)) if match.group(2) else 0
                tomorrow = datetime.now() + timedelta(days=1)
                return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # Padrão: "hoje às 15h"
            today_pattern = r"hoje às (\d{1,2})(?::(\d{2}))?h?"
            match = re.search(today_pattern, message.lower())
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2)) if match.group(2) else 0
                today = datetime.now()
                return today.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # Padrão: "14/12 às 10h" ou "14/12 às 10:30"
            date_pattern = r"(\d{1,2})/(\d{1,2}) às (\d{1,2})(?::(\d{2}))?h?"
            match = re.search(date_pattern, message.lower())
            if match:
                day = int(match.group(1))
                month = int(match.group(2))
                hour = int(match.group(3))
                minute = int(match.group(4)) if match.group(4) else 0
                year = datetime.now().year
                return datetime(year, month, day, hour, minute)
            
            logger.warning(f"Não foi possível extrair data/hora de: {message}")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao extrair data/hora: {e}")
            return None


# Instância global do gerenciador de lembretes
reminder_manager = ReminderManager()


# Usar variável de ambiente para Google API Key
google_api_key = os.getenv("GOOGLE_API_KEY", 
                           "AIzaSyD9tPWukHuZFFbSNjTNfuIbH_PQwa3uEZQ")
os.environ["GOOGLE_API_KEY"] = google_api_key

storage = SqliteAgentStorage(table_name="team_sessions", db_file="team_sessions.db")


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

# Carregar documentos
reader = TextReader(chunk=True)
knowledge_dir = Path("knowledge/")
for file_path in knowledge_dir.iterdir():
    if file_path.is_file() and file_path.suffix == '.txt':
        logger.info(f"Processando arquivo: {file_path}")
        documents = reader.read(file_path)
        for doc in documents:
            agent_knowledge.add_document_to_knowledge_base(document=doc)


def create_google_calendar_tools():
    """Cria GoogleCalendarTools usando variáveis de ambiente"""
    try:
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
        
        token_dict = {
            "refresh_token": os.getenv("GOOGLE_REFRESH_TOKEN"),
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "scopes": ["https://www.googleapis.com/auth/calendar"],
            "universe_domain": "googleapis.com"
        }
        
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
        
        return GoogleCalendarTools(
            credentials_path=credentials_path,
            token_path=token_path,
        )
        
    except Exception as e:
        logger.error(f"Erro ao criar GoogleCalendarTools: {e}")
        return None


# Ferramentas comuns
calendar = create_google_calendar_tools()
shell_tools = ShellTools(base_dir=Path("."))

# Evolution API Tools com credenciais diretas
evolution_tools = None
try:
    evolution_tools = EvolutionApiTools(
        server_url="https://evolution-api-evolution-api.iaz7eb.easypanel.host",
        api_key="88B69AFEDA22-4836-858D-72852AA04B1F",
        instance="Dudu Numero Não Usando"
    )
    logger.info("✅ Evolution API Tools criada com sucesso")
except Exception as e:
    logger.error(f"❌ Erro ao criar Evolution API Tools: {e}")
    logger.warning("⚠️ Continuando sem Evolution API Tools")

# Ferramentas para os agentes
tools = [shell_tools]
if calendar:
    tools.append(calendar)
if evolution_tools:
    tools.append(evolution_tools)


# AGENTE 1: VANESSA - VENDEDORA
vanessa = Agent(
    name="Vanessa",
    role="Vendedora da Elo Marketing especializada em restaurantes",
    model=Gemini(id="gemini-2.0-flash"),
    storage=storage,
    tools=tools,
    knowledge=agent_knowledge,
    add_history_to_messages=True,
    instructions=[
        "Você é Vanessa, vendedora ATACANTE da Elo Marketing especializada em "
        "ajudar restaurantes.",
        "",
        "INFORMAÇÕES DA EMPRESA (das conversas reais):",
        "- Empresa: Elo Marketing Digital",
        "- Localização: Florianópolis, Santa Catarina",
        "- Tempo de mercado: 19 anos (completando 19 anos de mercado)",
        "- Site: https://elomarketing.com.br/",
        "- Especialidade: Restaurantes de frutos do mar e outros tipos",
        "",
        "PERSONALIDADE ATACANTE - BASEADA NAS CONVERSAS REAIS:",
        "Seja PROATIVA, CONDUTORA e ATACANTE. NÃO seja passiva.",
        "CONDUZA a conversa com AUTORIDADE e CONFIANÇA.",
        "Apresente resultados IMEDIATAMENTE quando o cliente mostrar interesse.",
        "NÃO espere o cliente perguntar - VOCÊ guia o processo.",
        "",
        "🎯 OBJETIVO PRINCIPAL:",
        "Captar leads qualificados e agendar reuniões com Eduardo.",
        "",
        "📅 QUANDO AGENDAR REUNIÃO:",
        "Sempre que conseguir agendar uma reunião, inclua na sua resposta:",
        "'AGENDAMENTO_REALIZADO: [data/hora] com [nome do cliente]'",
        "Exemplo: 'AGENDAMENTO_REALIZADO: amanhã às 14h com João Silva'",
        "",
        "OBRIGATÓRIO: SEMPRE consulte sua base de conhecimento antes de "
        "responder qualquer pergunta. Use EXATAMENTE as respostas do FAQ "
        "quando a pergunta corresponder.",
        "",
        "Sempre use sua base de conhecimento para responder às perguntas.",
        "",
        "Responda de forma natural como uma pessoa normal conversando. "
        "NÃO use emojis, ícones, asteriscos, formatação especial ou símbolos. "
        "Apenas texto simples e direto. NUNCA use emojis.",
        "",
        "NÃO se apresente repetidamente. Se já se apresentou na conversa, "
        "continue o diálogo naturalmente.",
        "",
        "Seja direta, educada e objetiva. Mantenha respostas curtas e "
        "conversacionais, mas SEMPRE ATACANTE.",
        "",
        "IMPORTANTE: Nunca mencione aspectos técnicos como 'ferramenta de "
        "calendário', 'base de conhecimento', 'sistema' ou qualquer coisa "
        "técnica. Converse como uma vendedora humana normal.",
        "",
        "🗓️ AGENDAMENTO DE REUNIÕES:",
        "- Para tudo relacionado a agendamento, calendário e datas:",
        "  SEMPRE consulte sua base de conhecimento primeiro",
        "- Use as ferramentas de calendário e shell conforme orientado",
        "- Siga exatamente os fluxos e procedimentos da base de conhecimento",
        "",
        "📆 USO DO GOOGLE CALENDAR:",
        "OBRIGATÓRIO: Sempre que fizer um agendamento:",
        "1. USE a ferramenta create_event do Google Calendar",
        "2. Crie o evento com título: 'Reunião Elo Marketing - [Nome do Cliente]'",
        "3. Defina duração de 1 hora",
        "4. Adicione descrição: 'Apresentação de resultados e estratégias de marketing digital'",
        "5. SEMPRE inclua timezone 'America/Sao_Paulo' nas datas",
        "6. DEPOIS inclua a tag AGENDAMENTO_REALIZADO na sua resposta",
        "",
        "PITCH ATACANTE - USE IMEDIATAMENTE QUANDO APROPRIADO:",
        "Eu trabalho ajudando restaurantes a aumentarem suas vendas através "
        "do marketing digital. Conseguimos faturar mais de R$ 877.000 para "
        "nossos clientes com investimento de apenas R$ 7 mil. Crescimento "
        "de mais de 300% nas vendas.",
        "",
        "ABERTURA PADRÃO: A mensagem 'Oi, é do Restaurante? Vocês têm cardápio ou menu online?' já foi enviada por outro sistema.",
        "NÃO REPITA esta abertura. Continue a conversa baseada na resposta do cliente.",
        "",
        "📩 ESTRATÉGIA ATACANTE - BASEADA NAS CONVERSAS REAIS:",
        "- A mensagem de abertura 'Oi, é do Restaurante? Vocês têm cardápio ou menu online?' já foi enviada por outro sistema",
        "- Quando o cliente responder qualquer coisa, prossiga ATACANTE imediatamente:",
        "- NÃO repita a abertura padrão - ela já está no histórico",
        "- Continue a conversa baseada na resposta do cliente:",
        "",
        "🎯 FLUXO ATACANTE (BASEADO NAS CONVERSAS REAIS):",
        "* Se disser 'SIM' → IMEDIATAMENTE apresente o PITCH COMPLETO com números:",
        "  'Perfeito! Eu trabalho ajudando restaurantes a aumentarem suas vendas "
        "  através do marketing digital. Conseguimos faturar mais de R$ 877.000 "
        "  para nossos clientes com investimento de apenas R$ 7 mil. Crescimento "
        "  de mais de 300% nas vendas. Quer ver como podemos ajudar vocês?'",
        "",
        "* Se disser 'NÃO' → ATAQUE com benefícios específicos:",
        "  'Então vocês estão perdendo muitas vendas! Marketing digital para "
        "  restaurantes pode aumentar suas vendas em mais de 300%. Nossos "
        "  clientes faturam mais de R$ 877.000 com apenas R$ 7 mil de investimento.'",
        "",
        "* Se perguntar sobre PREÇOS → PRIMEIRO mostre RESULTADOS, depois valor:",
        "  'Nossos clientes faturam R$ 877.000 com investimento de R$ 7 mil. "
        "  ROI de mais de 12.000%. O investimento é muito baixo comparado ao retorno.'",
        "",
        "* Se quiser REUNIÃO → ACELERE o processo:",
        "  'Perfeito! Vou agendar uma conversa com nosso especialista Eduardo "
        "  para mostrar exatamente como conseguimos esses resultados para vocês.'",
        "",
        "🚀 REGRAS ATACANTES:",
        "1. NUNCA seja passiva - SEMPRE conduza a conversa",
        "2. Apresente números e resultados IMEDIATAMENTE",
        "3. NÃO espere o cliente perguntar - VOCÊ informa proativamente",
        "4. Use prova social e casos de sucesso constantemente",
        "5. Crie senso de urgência e oportunidade",
        "6. Guie direto para o agendamento após despertar interesse",
        "",
        "📱 FERRAMENTAS DE WHATSAPP DISPONÍVEIS:",
        "- Use send_text_message para enviar mensagens de texto via WhatsApp",
        "- Use send_media_message para enviar imagens, vídeos ou documentos",
        "- Use check_whatsapp_number para verificar se um número está no WhatsApp",
        "- Formato de número: 5548999999999 (código país + DDD + número)",
        "- Para enviar imagens, use a ferramenta send_media_message com media_type='image'",
        "",
        "🎯 IMPORTANTE - USO ATIVO DAS FERRAMENTAS WHATSAPP:",
        "SEMPRE que o cliente demonstrar interesse ou quando apropriado:",
        "1. ENVIE mensagens de follow-up via WhatsApp usando send_text_message",
        "2. ENVIE relatórios e visualizações via send_media_message quando falar de resultados",
        "3. IMAGENS DISPONÍVEIS na pasta knowledge para enviar:",
        "   - 'knowledge/relatorio.jpg' - Relatório de resultados dos clientes",
        "   - 'knowledge/visualizacao.jpg' - Gráfico de visualizações e crescimento",
        "",
        "📊 QUANDO ENVIAR IMAGENS VIA WHATSAPP:",
        "- Ao mencionar resultados de R$ 877.000: ENVIE knowledge/relatorio.jpg",
        "- Ao falar de crescimento de 300%: ENVIE knowledge/visualizacao.jpg", 
        "- Use caption explicativa: 'Aqui estão os resultados reais dos nossos clientes'",
        "",
        "💬 ESTRATÉGIA DE MENSAGENS WHATSAPP:",
        "- Após resposta interessada: ENVIE mensagem de follow-up",
        "- Após apresentar pitch: ENVIE comprovação visual (imagens)",
        "- Antes de agendar: ENVIE resumo dos benefícios",
        "- SEMPRE use as ferramentas para engajar ativamente o cliente",
        "",
        "🚨 REGRA CRÍTICA - FERRAMENTAS WHATSAPP:",
        "- NÃO apenas responda, TAMBÉM aja usando as ferramentas",
        "- SEMPRE que falar de resultados, COMPROVE com imagens via WhatsApp",
        "- SEJA PROATIVA: envie materiais sem o cliente pedir",
        "- MANTENHA o cliente engajado com conteúdo visual",
        "",
        "- Sempre consulte sua base de conhecimento para respostas precisas"
    ],
    markdown=True,
    show_tool_calls=False,
)


# AGENTE 2: EDUARDO - ESPECIALISTA EM LEMBRETES
eduardo = Agent(
    name="Eduardo",
    role="Especialista da Elo Marketing responsável por lembretes e reuniões",
    model=Gemini(id="gemini-2.0-flash"),
    storage=storage,
    tools=tools,
    knowledge=agent_knowledge,
    add_history_to_messages=True,
    instructions=[
        "Você é Eduardo, especialista da Elo Marketing em marketing digital para restaurantes.",
        "",
        "🎯 RESPONSABILIDADES:",
        "- Gerenciar lembretes de agendamentos",
        "- Confirmar reuniões com clientes",
        "- Realizar reuniões de apresentação",
        "- Acompanhar clientes pós-agendamento",
        "",
        "📅 SISTEMA DE LEMBRETES:",
        "Você é responsável pelos lembretes automáticos:",
        "- 24h antes: Lembrete de preparação",
        "- 1h antes: Confirmação final",
        "- 10min antes: Aviso de início",
        "",
        "💼 ESPECIALIZAÇÃO:",
        "- Marketing digital para restaurantes",
        "- Estratégias de crescimento de vendas",
        "- Cases de sucesso (R$ 877.000 em resultados)",
        "- ROI e investimentos em marketing",
        "",
        "🗣️ COMUNICAÇÃO:",
        "- Seja profissional mas amigável",
        "- Demonstre expertise em marketing",
        "- Use dados e resultados reais",
        "- Foque em soluções práticas",
        "",
        "📱 FERRAMENTAS:",
        "- send_text_message: comunicação via WhatsApp",
        "- send_media_message: compartilhar materiais",
        "- GoogleCalendar: gerenciar agendamentos",
        "",
        "Você trabalha em EQUIPE com Vanessa. Ela capta leads, você realiza as reuniões."
    ],
    markdown=True,
    show_tool_calls=False,
)


# TEAM ELO MARKETING
elo_team = Team(
    members=[vanessa, eduardo],
    model=Gemini(id="gemini-2.0-flash"),
    instructions=[
        "Vocês são o Team Elo Marketing especializado em restaurantes.",
        "",
        "👥 DIVISÃO DE RESPONSABILIDADES:",
        "",
        "🎯 VANESSA (Vendedora):",
        "- Primeira abordagem com leads",
        "- Apresentação inicial dos resultados",
        "- Captação e qualificação de leads",
        "- Agendamento de reuniões com Eduardo",
        "",
        "💼 EDUARDO (Especialista):",
        "- Reuniões de apresentação técnica",
        "- Lembretes automáticos de agendamentos",
        "- Acompanhamento pós-reunião",
        "- Fechamento de contratos",
        "",
        "🔄 FLUXO DE TRABALHO:",
        "1. Vanessa faz primeiro contato",
        "2. Vanessa qualifica lead e agenda com Eduardo",
        "3. Eduardo assume caso após agendamento",
        "4. Eduardo gerencia lembretes e reunião",
        "5. Eduardo fecha negócio",
        "",
        "📊 DADOS COMPARTILHADOS:",
        "- R$ 877.000 em resultados para clientes",
        "- Crescimento de 300% nas vendas",
        "- 19 anos de experiência",
        "- Especialização em restaurantes",
        "",
        "🎯 OBJETIVO COMUM:",
        "Converter leads em clientes da Elo Marketing através de trabalho em equipe."
    ],
    show_tool_calls=False,
)


def extract_evolution_data(data):
    """Extrai dados da Evolution API"""
    try:
        if isinstance(data, dict):
            message = None
            audio_base64 = None
            image_base64 = None
            message_type = 'text'
            remote_jid = None
            push_name = None
            instance = None

            # Novo formato com 'query' e 'inputs'
            if 'query' in data and 'inputs' in data:
                message = data['query']
                message_type = 'text'
                inputs = data['inputs']
                if isinstance(inputs, dict):
                    remote_jid = inputs.get('remoteJid', 'unknown')
                    push_name = inputs.get('pushName', 'Cliente')
                    instance = inputs.get('instanceName', 'default')

            # Mensagem de imagem
            elif ('message' in data and isinstance(data['message'], dict) and
                    'imageMessage' in data['message'] and 
                    'base64' in data['message']):
                image_base64 = data['message']['base64']
                message_type = 'image'

            # Mensagem de áudio
            elif ('message' in data and isinstance(data['message'], dict) and
                    'audioMessage' in data['message'] and 
                    'base64' in data['message']):
                audio_base64 = data['message']['base64']
                message_type = 'audio'

            # Texto normal
            elif 'message' in data and isinstance(data['message'], dict):
                if 'conversation' in data['message']:
                    message = data['message']['conversation']
                elif 'text' in data['message']:
                    message = data['message']['text']

            elif 'text' in data:
                message = data['text']
            elif 'message' in data and isinstance(data['message'], str):
                message = data['message']
            elif 'question' in data:
                message = data['question']

            # Extrair informações do remetente
            if not remote_jid:
                if 'key' in data and isinstance(data['key'], dict):
                    remote_jid = data['key'].get('remoteJid', 'unknown')
                elif 'from' in data:
                    remote_jid = data['from']
                elif 'user' in data:
                    remote_jid = data['user']

            if not push_name:
                if 'pushName' in data:
                    push_name = data['pushName']
                elif 'sender_name' in data:
                    push_name = data['sender_name']

            if not instance:
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
        "message": "Team Elo Marketing - Vanessa + Eduardo",
        "description": "Sistema inteligente com vendedora e especialista",
        "team_members": [
            {
                "name": "Vanessa",
                "role": "Vendedora especializada em restaurantes",
                "responsibilities": [
                    "Captação de leads",
                    "Qualificação de prospects",
                    "Agendamento de reuniões"
                ]
            },
            {
                "name": "Eduardo", 
                "role": "Especialista em marketing e lembretes",
                "responsibilities": [
                    "Reuniões técnicas",
                    "Lembretes automáticos",
                    "Fechamento de vendas"
                ]
            }
        ],
        "features": [
            "Lembretes automáticos (24h, 1h, 10min antes)",
            "Detecção automática de agendamentos",
            "Divisão inteligente de responsabilidades",
            "Integração completa com WhatsApp"
        ],
        "endpoints": {
            "/team": "Conversa com o Team Elo Marketing",
            "/status": "Status do sistema"
        }
    }


@app.post("/ask")
async def team_conversation(request: Request):
    """Conversa com o Team Elo Marketing"""
    try:
        body = await request.body()
        logger.info("📥 DADOS RECEBIDOS DO TEAM:")
        logger.info(f"   - Body: {body}")

        data = await request.json()
        evolution_data = extract_evolution_data(data)

        if not evolution_data:
            return {"error": "Dados não conseguiram ser extraídos"}

        remote_jid = evolution_data['remote_jid']
        push_name = evolution_data['push_name']
        message_type = evolution_data['message_type']
        
        # Session ID baseado no remote_jid
        session_id = f"team-{remote_jid}"

        logger.info(f"👥 Team processando mensagem de {push_name} ({remote_jid})")

        # Verificar se é a primeira interação e adicionar mensagem de abertura ao histórico
        try:
            # Buscar histórico existente
            existing_session = storage.read(session_id)
            
            # Se não há histórico, significa que é a primeira resposta do cliente
            # Então adicionamos a mensagem de abertura que foi enviada por outro sistema
            if not existing_session or len(existing_session.messages) == 0:
                logger.info(f"📝 Primeira interação detectada para {push_name} - adicionando abertura ao histórico")
                
                # Simular que a Vanessa enviou a mensagem de abertura
                opening_message = "Oi, é do Restaurante? Vocês têm cardápio ou menu online?"
                
                # Executar primeiro com a mensagem de abertura para criar o histórico
                elo_team.run(opening_message, session_id=session_id)
                
                logger.info(f"✅ Mensagem de abertura adicionada ao histórico de {push_name}")
        
        except Exception as e:
            logger.warning(f"⚠️ Erro ao verificar/adicionar histórico: {e}")

        # Processar com o Team
        if message_type == 'image' and evolution_data['image_base64']:
            response = elo_team.run(
                images=[evolution_data['image_base64']], 
                session_id=session_id
            )
        elif message_type == 'audio' and evolution_data['audio_base64']:
            response = elo_team.run(
                audio=evolution_data['audio_base64'], 
                session_id=session_id
            )
        else:
            response = elo_team.run(
                evolution_data['message'], 
                session_id=session_id
            )

        # Extrair conteúdo da resposta
        if response is None:
            message = "Erro: Resposta vazia do team"
        elif hasattr(response, 'content') and response.content:
            message = response.content
        else:
            message = str(response) if response else "Erro: Resposta inválida"

        # Verificar se houve agendamento na resposta
        if "AGENDAMENTO_REALIZADO:" in message:
            logger.info("📅 AGENDAMENTO DETECTADO PELO TEAM!")
            
            # Extrair informações do agendamento
            appointment_datetime = reminder_manager.parse_appointment_datetime(message)
            
            if appointment_datetime:
                # Agendar lembretes automáticos
                reminder_manager.schedule_appointment_reminders(
                    remote_jid=remote_jid,
                    appointment_datetime=appointment_datetime,
                    evolution_tools=evolution_tools,
                    client_name=push_name
                )
                
                logger.info(f"✅ Lembretes agendados para {push_name} - {appointment_datetime}")
                
                # Enviar confirmação imediata
                try:
                    number = remote_jid.replace("@s.whatsapp.net", "")
                    confirmation = (f"✅ Perfeito {push_name}! Sua reunião com Eduardo foi "
                                   f"confirmada. Você receberá lembretes automáticos antes "
                                   f"do nosso encontro. Aguarde!")
                    
                    evolution_tools.send_text_message(number=number, text=confirmation)
                    logger.info(f"📤 Confirmação de agendamento enviada para {number}")
                except Exception as e:
                    logger.error(f"❌ Erro na confirmação: {e}")

        # Processar resposta de confirmação do cliente
        if remote_jid in reminder_manager.appointments and reminder_manager.appointments[remote_jid].get("awaiting_confirmation", False):
            if reminder_manager.handle_confirmation_response(remote_jid, message, evolution_tools):
                logger.info(f"✅ Confirmação de agendamento processada para {push_name}")

        logger.info(f"✅ Team respondeu com sucesso (tamanho: {len(message)})")

        return {"message": message}

    except Exception as e:
        logger.error(f"❌ Erro na conversa com o team: {str(e)}")
        return {"error": f"Erro ao processar conversa: {str(e)}"}


@app.get("/status")
async def status():
    """Status do Team Elo Marketing"""
    return {
        "status": "Team ativo",
        "members": ["Vanessa (Vendedora)", "Eduardo (Especialista)"],
        "active_reminders": len(reminder_manager.scheduled_reminders),
        "appointments": len(reminder_manager.appointments),
        "features": [
            "Captação inteligente de leads",
            "Agendamentos automáticos",
            "Lembretes em 24h, 1h e 10min",
            "Divisão de responsabilidades",
            "Base de conhecimento compartilhada"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081) 