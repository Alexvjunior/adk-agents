import os
import logging
import json
import tempfile
import sqlite3
import csv
import asyncio
from datetime import datetime
from collections import defaultdict
from typing import Dict, List
from dotenv import load_dotenv
from fastapi import FastAPI, Request, UploadFile, File
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.storage.agent.sqlite import SqliteAgentStorage
from agno.tools.knowledge import KnowledgeTools
from agno.tools.googlecalendar import GoogleCalendarTools
from agno.tools.shell import ShellTools
from agno.document.chunking.recursive import RecursiveChunking
from agno.knowledge.agent import AgentKnowledge
from agno.vectordb.chroma import ChromaDb
from agno.document.reader.text_reader import TextReader
from agno.embedder.openai import OpenAIEmbedder  # Mudança para OpenAI
from pathlib import Path
from evolution_api_tools import EvolutionApiTools

# Carregar variáveis de ambiente
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


# Inicializar banco de dados para restaurantes
def init_restaurant_db():
    """Inicializa o banco de dados de restaurantes"""
    conn = sqlite3.connect("restaurantes.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS restaurantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            numero TEXT NOT NULL UNIQUE,
            primeira_mensagem_enviada BOOLEAN DEFAULT FALSE,
            data_envio DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    logger.info("✅ Banco de dados de restaurantes inicializado")


# Inicializar DB na importação
init_restaurant_db()


# Usar variável de ambiente para Google API Key
google_api_key = os.getenv("GOOGLE_API_KEY", 
                           "AIzaSyCKTbPQDtAhUI9VWQH26_v2KJW3146Xe20")
os.environ["GOOGLE_API_KEY"] = google_api_key

# Configurar OpenAI API Key
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    logger.error("❌ OPENAI_API_KEY não configurada!")
else:
    os.environ["OPENAI_API_KEY"] = openai_api_key
    logger.info("✅ OpenAI API Key configurada")

storage = SqliteAgentStorage(table_name="sessions", db_file="sessions.db")

# 🚀 SISTEMA DE CONHECIMENTO OTIMIZADO - Usando embeddings da OpenAI
agent_knowledge = AgentKnowledge(
    vector_db=ChromaDb(
        collection="elo_marketing_knowledge",
        embedder=OpenAIEmbedder(
            id="text-embedding-3-large",  # Modelo mais avançado da OpenAI
            api_key=os.environ.get("OPENAI_API_KEY"),
            dimensions=3072,  # Dimensões máximas para melhor precisão
        ),
        path="knowledge_db",
        persistent_client=True,
    ),
    chunking_strategy=RecursiveChunking(
        chunk_size=800,  # Otimizado para o modelo
        overlap=200,     # Maior overlap para melhor contexto
    ),
    num_documents=10,  # Aumentado para mais contexto
)


def load_knowledge_base_safely():
    """
    Carrega documentos do knowledge base de forma segura,
    evitando rate limiting da API da OpenAI
    """
    import time

    reader = TextReader(chunk=True)
    knowledge_dir = Path("knowledge/")
    
    if not knowledge_dir.exists():
        logger.warning("⚠️ Diretório 'knowledge/' não encontrado")
        return
    
    # Listar todos os arquivos para processar
    files_to_process = []
    for file_path in knowledge_dir.iterdir():
        if file_path.is_file() and file_path.suffix in ['.txt', '.md']:
            files_to_process.append(file_path)
    
    if not files_to_process:
        logger.info("📂 Nenhum arquivo encontrado na pasta knowledge/")
        return
    
    logger.info(f"📚 Encontrados {len(files_to_process)} arquivos "
                f"para processar")
    
    # Processar arquivos com rate limiting
    processed_count = 0
    for i, file_path in enumerate(files_to_process):
        try:
            logger.info(f"📄 Processando arquivo {i+1}/"
                        f"{len(files_to_process)}: {file_path.name}")
            
            # Verificar se já existe no banco vetorial
            # (apenas após collection existir)
            try:
                existing_docs = agent_knowledge.search(
                    query=f"arquivo {file_path.stem}",
                    num_documents=1
                )
                if existing_docs and len(existing_docs) > 0:
                    logger.info(f"✅ Arquivo {file_path.name} já foi "
                                f"processado anteriormente")
                    continue
            except Exception:
                # Collection pode não existir ainda - isso é normal
                logger.debug("Collection ainda não existe - criando...")
                pass
            
            # Ler e processar o arquivo
            documents = reader.read(file_path)
            
            # Processar documentos em lotes pequenos
            batch_size = 2  # Processar 2 documentos por vez
            for batch_start in range(0, len(documents), batch_size):
                batch_end = min(batch_start + batch_size, len(documents))
                batch_docs = documents[batch_start:batch_end]
                
                for doc in batch_docs:
                    try:
                        # Verificar se documento tem atributo meta
                        if not hasattr(doc, 'meta') or doc.meta is None:
                            doc.meta = {}
                        
                        # Adicionar metadados
                        doc.meta["source_file"] = file_path.name
                        doc.meta["processed_at"] = time.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                        
                        agent_knowledge.add_document_to_knowledge_base(
                            document=doc
                        )
                        processed_count += 1
                        
                        # Rate limiting: pausa entre documentos
                        time.sleep(0.5)  # 500ms entre documentos
                        
                    except Exception as doc_error:
                        logger.error(f"❌ Erro ao processar documento: "
                                     f"{doc_error}")
                        continue
                
                # Pausa maior entre lotes
                if batch_end < len(documents):
                    logger.info(f"⏸️ Pausa... {batch_end}/{len(documents)} "
                                f"processados")
                    time.sleep(2.0)  # 2 segundos entre lotes
            
            logger.info(f"✅ Arquivo {file_path.name} processado")
            
            # Pausa entre arquivos
            if i < len(files_to_process) - 1:
                logger.info("⏸️ Pausa entre arquivos...")
                time.sleep(3.0)  # 3 segundos entre arquivos
                
        except Exception as file_error:
            logger.error(f"❌ Erro ao processar {file_path.name}: "
                         f"{file_error}")
            continue
    
    logger.info(f"🎉 Knowledge base carregado! "
                f"Documentos processados: {processed_count}")


# Carregar knowledge base de forma assíncrona (não bloquear a inicialização)
try:
    logger.info("🚀 Iniciando carregamento do knowledge base...")
    load_knowledge_base_safely()
except Exception as e:
    logger.error(f"⚠️ Erro no carregamento do knowledge base: {e}")
    logger.info("📝 Sistema continuará funcionando sem o knowledge base "
                "completo")


# 🔧 FERRAMENTAS DE CONHECIMENTO - Usando o mesmo sistema
knowledge_tools = KnowledgeTools(
    knowledge=agent_knowledge,  # Usando o mesmo sistema do agente
    think=True,
    search=True,
    analyze=True,
    instructions=(
        "Use sempre as conversas reais para responder perguntas. "
        "Procure por respostas específicas no knowledge base antes de "
        "responder. Priorize informações precisas e atualizadas."
    ),
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
tools = [shell_tools, knowledge_tools]
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
    logger.info(f"🔧 Métodos disponíveis nas ferramentas: "
                f"{dir(evolution_tools)}")
    logger.info(f"🔧 Funções das ferramentas: {evolution_tools.functions}")
else:
    logger.error("❌ Evolution API Tools não está disponível")


# 🚀 SISTEMA DE DEBOUNCE PARA MENSAGENS CONSECUTIVAS
# Evita processamento individual de mensagens enviadas rapidamente
user_message_queues: Dict[str, List] = defaultdict(list)
user_timers: Dict[str, asyncio.Task] = {}
DEBOUNCE_DELAY = 5.0  # 5 segundos para aguardar mensagens consecutivas


async def process_user_messages_batch(user_id: str, whatsapp_number: str):
    """
    Processa todas as mensagens acumuladas de um usuário em lote
    """
    try:
        # Aguardar o delay de debounce
        await asyncio.sleep(DEBOUNCE_DELAY)
        
        # Pegar todas as mensagens acumuladas
        if (user_id not in user_message_queues or 
                not user_message_queues[user_id]):
            return
            
        messages = user_message_queues[user_id].copy()
        user_message_queues[user_id].clear()
        
        logger.info(f"🔄 Processando {len(messages)} mensagens em lote "
                    f"para {user_id}")
        
        # Combinar todas as mensagens
        combined_texts = []
        push_name = "Cliente"
        
        for msg in messages:
            if msg.get('text'):
                combined_texts.append(msg['text'])
            if msg.get('push_name'):
                push_name = msg['push_name']
        
        if not combined_texts:
            logger.warning("⚠️ Nenhuma mensagem de texto para processar")
            return
            
        combined_text = " | ".join(combined_texts)
        last_message = messages[-1]
        
        # Criar instruções dinâmicas para processamento em lote
        dynamic_instructions = f"""
CONTEXTO ATUAL:
- Cliente: {push_name}
- Número WhatsApp: {whatsapp_number}
- Total de mensagens recebidas consecutivamente: {len(messages)}

📢 IMPORTANTE: O cliente enviou {len(messages)} mensagens seguidas:
{' | '.join([f'"{text}"' for text in combined_texts])}

ANALISE TODAS as informações juntas e responda UMA ÚNICA VEZ 
via send_text_message!

🔍 DETECÇÃO DE DADOS DE AGENDAMENTO:
Se as mensagens contêm nome + restaurante + email:
→ PROCESSE o agendamento imediatamente
→ Use create_event() com os dados fornecidos
→ Confirme via send_text_message

🔄 DETECÇÃO DE MUDANÇAS DE AGENDAMENTO:
Se mensagens pedem mudança de horário:
→ EXECUTE list_events() para verificar agenda
→ RESPONDA DEFINITIVAMENTE se conseguiu ou não
→ Use update_event() se disponível o novo horário
→ NUNCA diga "vou verificar" - VERIFIQUE e RESPONDA!

🚨 VERIFICAÇÃO OBRIGATÓRIA DE AGENDA:
Para QUALQUER agendamento (novo ou mudança):
→ SEMPRE execute list_events() PRIMEIRO
→ ANALISE os eventos retornados
→ IDENTIFIQUE horários livres sem conflitos
→ NUNCA sugira horários ocupados
→ SÓ ofereça horários DISPONÍVEIS

🚨 SEMPRE SEJA ATIVO E COMERCIAL:
- Mencione resultados (R$ 877.000, 30%)
- Busque marcar reunião com Eduardo
- Use frases diretas: "Posso agendar hoje?"
- NUNCA seja passivo

🛡️ TRATAMENTO DE OBJEÇÕES:
Se detectar objeção ("não é o momento", "vou pensar"):
→ NÃO desista! Faça 2 tentativas educadas
→ Mostre material adicional (outras imagens)
→ Entenda a objeção e contorne
→ Ofereça conversa sem compromisso

🖼️ ENVIO DE IMAGENS (quando relevante):
Para resultados financeiros: relatorio.jpg
Para crescimento: visualizacao.jpg

Use send_text_message(number='{whatsapp_number}', 
text='sua_resposta_completa')

🚨 REGRA CRÍTICA: SEMPRE use send_text_message para TODA resposta!

{last_message.get('original_instructions', '')}
"""
        
        # Processar com o agente
        message_with_context = (
            f"{dynamic_instructions}\n\n"
            f"MENSAGENS DO CLIENTE: {combined_text}"
        )
        
        session_id = f"elo-{last_message['remote_jid']}"
        
        logger.info(f"🤖 Enviando para agente: sessão {session_id}")
        response = vanessa.run(message_with_context, session_id=session_id)
        
        logger.info(f"✅ Processamento em lote concluído para {user_id}")
        
        if hasattr(response, 'content') and response.content:
            logger.info(f"📝 Resposta do agente: {response.content[:100]}...")
        
        if hasattr(response, 'tool_calls') and response.tool_calls:
            logger.info(f"🔧 Tool calls executados: {len(response.tool_calls)}")
        
    except asyncio.CancelledError:
        logger.info(f"⏹️ Processamento cancelado para {user_id} "
                    f"(nova mensagem recebida)")
    except Exception as e:
        logger.error(f"❌ Erro no processamento em lote para {user_id}: {e}")
    finally:
        # Limpar timer da lista
        if user_id in user_timers:
            del user_timers[user_id]


# Criar agente Vanessa - Vendedora da Elo Marketing
vanessa = Agent(
    name="Vanessa",
    role="Vendedora da Elo Marketing especializada em restaurantes",
    model=OpenAIChat(
        id="gpt-4o",  # Atualizado para GPT-4o (mais avançado)
        temperature=0.7,
        max_tokens=1000,
        top_p=0.9,
        frequency_penalty=0.0,
        presence_penalty=0.0,
    ),
    storage=storage,
    tools=tools,  # Adicionado shell_tools
    knowledge=agent_knowledge,
    add_history_to_messages=True,
    tool_choice="auto",  # Voltando para "required" para garantir uso do send_text_message
    instructions=[
        "🚨 REGRA CRÍTICA #1 - ENVIO OBRIGATÓRIO:",
        "TODA resposta que você gerar DEVE ser enviada via send_text_message do EvolutionApiTools!",
        "",
        "🚨 REGRA CRÍTICA #2 - DIFERENÇA IMPORTANTE:",
        "AGENDAMENTO REAL: Use send_text_message + ferramentas de calendário",
        "",
        "🚨 REGRA CRÍTICA #3 - FERRAMENTAS",
        "VOCÊ É UM AGENTE CONECTADO NO WHATSAPP RECEBENDO EVENTOS E PARA RESPONDER O USUÁRIO VOCÊ DEVE USAR O EvolutionApiTools PARA RESPONDER",
        "",
        "🚨 REGRA CRÍTICA #4 - SEMPRE ATIVO E COMERCIAL:",
        "EM TODA RESPOSTA, SEMPRE inclua um elemento ativo:",
        "- Mencione resultados (R$ 877.000, 30% crescimento)", 
        "- Ofereça mostrar cases ou exemplos",
        "- Busque marcar reunião com Eduardo",
        "- Use frases como: 'Posso agendar hoje?', 'Que tal conversarmos?'",
        "NUNCA seja passivo - SEMPRE empurre para agendamento!",
        "",
        "Você é Vanessa, vendedora da Elo Marketing especializada em "
        "restaurantes.",
        "",
        "📋 FLUXO BASEADO NAS CONVERSAS REAIS (knowledge):",
        "",
        "SE cliente responder 'Sim, temos cardápio' ou similar:",
        "→ Use APENAS send_text_message com:",
        "'Tudo bem? 😉 Aqui é a Vanessa. Trabalho ajudando restaurantes "
        "a atrair clientes. Nos últimos meses, ajudamos restaurantes a "
        "crescer mais de 30%, faturando R$ 877.000 em um mês, "
        "investindo R$ 7 mil. Posso mostrar resultados?'",
        "",
        "SE cliente pedir para ver resultados:",
        "→ Use send_text_message + send_media_message (relatorio.jpg)",
        "→ DEPOIS da imagem, SEMPRE envie outro send_text_message:",
        "'Esses são alguns dos resultados reais! Você topa agendar "
        "um breve bate-papo com um dos nossos especialistas? "
        "Ele pode mostrar como conseguimos esses números.'",
        "",
        "SE cliente demonstrar interesse depois dos resultados:",
        "→ Use APENAS send_text_message:",
        "'Você topa agendar um breve bate-papo com nosso especialista "
        "Eduardo? Ele pode mostrar como ajudamos restaurantes.'",
        "",
        "🚨 SEJA SEMPRE ATIVO E ASSERTIVO:",
        "- SEMPRE busque marcar reunião após mostrar resultados",
        "- Use frases diretas como: 'Você topa agendar?'",
        "- Não seja passivo dizendo 'se quiser é só avisar'",
        "- FORCE o agendamento de forma educada mas firme",
        "- Exemplo: 'Legal! Posso agendar um horário hoje ou amanhã?'",
        "",
        "🛡️ TRATAMENTO DE OBJEÇÕES - NÃO DESISTA FÁCIL:",
        "SE cliente der objeção como 'não é o momento', 'vou pensar':",
        "🔄 ESTRATÉGIA DE 2 TENTATIVAS EDUCADAS:",
        "",
        "TENTATIVA 1 - Mostrar material adicional:",
        "→ 'Entendo! Deixa eu mostrar só mais um caso específico'",
        "→ Envie send_media_message com visualizacao.jpg ou cases.jpg",
        "→ 'Esse restaurante pensou igual, mas depois de 30 dias...'",
        "→ 'Que tal só uma conversa de 15min sem compromisso?'",
        "",
        "TENTATIVA 2 - Entender e contornar:",
        "→ 'Posso perguntar o que te faz hesitar? É o investimento?'",
        "→ 'É o tempo? É receio se funciona pro seu tipo de restaurante?'", 
        "→ 'Nosso especialista pode esclarecer isso em 10min'",
        "→ 'Que tal uma conversa rápida só pra tirar dúvidas?'",
        "",
        "APENAS DEPOIS DAS 2 TENTATIVAS:",
        "→ 'Entendo perfeitamente. Quando quiser conversar, é só chamar!'",
        "NUNCA desista na primeira objeção - SEMPRE tente 2 vezes!",
        "",
        "SE cliente ACEITAR EXPLICITAMENTE agendar:",
        "→ APENAS ENTÃO use ferramentas de calendário:",
        "1. shell_tools para data atual",
        "2. list_events() para agenda",
        "3. send_text_message sugerindo 2 horários",
        "4. create_event() quando cliente escolher",
        
        "🔄 MUDANÇAS DE AGENDAMENTO - RESPOSTA DEFINITIVA:",
        "SE cliente pedir para mudar horário existente:",
        "1. EXECUTE list_events() para verificar agenda",
        "2. VERIFIQUE se novo horário está disponível",
        "3. RESPONDA DEFINITIVAMENTE:",
        "   ✅ 'Perfeito! Consegui alterar para terça às 7h' (se disponível)",
        "   ❌ 'Não consegui às 7h, mas tenho segunda às 8h' (se indisponível)", 
        "4. Se conseguir: EXECUTE update_event() ou create_event()",
        "5. CONFIRME via send_text_message com horário final",
        "NUNCA diga 'vou verificar' - VERIFIQUE e RESPONDA NA HORA!",
        "",
        "🚨 FLUXO OBRIGATÓRIO DE AGENDAMENTO:",
        "🔥 PASSO 1 - CONSULTAR DATA E CALENDÁRIO (OBRIGATÓRIO):",
        "ANTES de sugerir qualquer horário, SEMPRE EXECUTE:",
        "1. shell_tools com comando: ['date', '+%A, %d de %B de %Y']",
        "2. list_events() ← Esta ferramenta é OBRIGATÓRIA!",
        "🚨 CRÍTICO: ANALISE os eventos retornados por list_events()",
        "NUNCA sugira horários que já estão ocupados na agenda!",
        "VERIFIQUE conflitos antes de oferecer qualquer horário!",
        "",
        "🔥 PASSO 2 - SUGERIR APENAS HORÁRIOS LIVRES:",
        "Após executar list_events() e VERIFICAR disponibilidade:",
        "→ ANALISE quais horários estão livres",
        "→ CONFIRME que não há conflitos",
        "→ SÓ ENTÃO sugira 2 horários DISPONÍVEIS via send_text_message:",
        "'Consultei a agenda! Eduardo está livre terça às 14h ou quarta às 10h'",
        "OU: 'Verifiquei a agenda. Temos segunda às 9h ou sexta às 15h'", 
        "OU: 'Agenda consultada! Disponível quinta às 11h ou terça às 16h'",
        "SEMPRE mencione que consultou agenda + 2 horários LIVRES",
        "",
        "🔥 PASSO 3 - COLETAR DADOS VIA WHATSAPP:",
        "Cliente escolhe horário → Use send_text_message com:",
        "'Para finalizar, preciso: nome completo, nome do restaurante e email'",
        "COLETE TODOS os dados antes de criar o evento!",
        "",
        "🔥 PASSO 4 - CRIAR EVENTO NO CALENDÁRIO (OBRIGATÓRIO):",
        "Quando tiver todos os dados, SEMPRE EXECUTE:",
        "create_event(timezone='America/Sao_Paulo', add_google_meet_link=True)",
        "NUNCA confirme agendamento sem executar create_event()!",
        "",
        "🔥 PASSO 5 - CONFIRMAR VIA WHATSAPP:",
        "Após create_event(), use send_text_message com:",
        "'Reunião agendada para [data/hora]!'",
        "'Link do Google Meet: [url extraído do evento criado]'",
        "'Eduardo já recebeu os detalhes por email'",
        "",
        "❌ PROIBIÇÕES ABSOLUTAS:",
        "- JAMAIS retorne texto sem usar send_text_message",
        "- JAMAIS sugira horários sem executar list_events() primeiro",
        "- JAMAIS sugira horários ocupados - SEMPRE verifique conflitos!",
        "- JAMAIS confirme agendamento sem executar create_event()",
        "- JAMAIS diga 'Eduardo entrará em contato' - VOCÊ agenda!",
        "",
        "✅ FLUXO CORRETO OBRIGATÓRIO:",
        "1. Cliente: 'quero reunião' → Você: EXECUTE list_events()",
        "2. ANALISE agenda e identifique horários LIVRES",
        "3. EXECUTE send_text_message('Consultei! Livre segunda às 14h ou terça às 10h?')",
        "4. Cliente escolhe → EXECUTE create_event() com o horário escolhido",
        "5. EXECUTE send_text_message('Agendado! Eduardo te liga [dia] às [hora]!')"
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
                if ('message' in payload_data and 
                        isinstance(payload_data['message'], dict)):
                    if 'conversation' in payload_data['message']:
                        message = payload_data['message']['conversation']
                        message_type = 'text'
                    elif ('imageMessage' in payload_data['message'] and 
                          'base64' in payload_data['message']):
                        image_base64 = payload_data['message']['base64']
                        message_type = 'image'
                    elif ('audioMessage' in payload_data['message'] and 
                          'base64' in payload_data['message']):
                        audio_base64 = payload_data['message']['base64']
                        message_type = 'audio'
                
                # Extrair informações do remetente do novo formato
                if ('key' in payload_data and 
                        isinstance(payload_data['key'], dict)):
                    remote_jid = payload_data['key'].get('remoteJid', 
                                                         'unknown')
                
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
            "reuniões com resultados comprovados: crescimento de 30% e "
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
    """Conversa com Vanessa - Vendedora da Elo Marketing (com debounce)"""
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
        
        # Extrair número do WhatsApp do remoteJid para as ferramentas
        whatsapp_number = remote_jid.replace("@s.whatsapp.net", "")
        logger.info(f"📱 Número extraído para ferramentas: {whatsapp_number}")

        # 🚀 SISTEMA DE DEBOUNCE - Processar mensagens de texto em lote
        if message_type == 'text' and has_text:
            user_id = remote_jid
            
            # Criar instruções dinâmicas originais para armazenar
            original_instructions = f"""
CONTEXTO ATUAL:
- Cliente: {push_name}
- Número WhatsApp: {whatsapp_number}

📢 IMPORTANTE: A pergunta sobre cardápio online JÁ FOI ENVIADA!
Continue a conversa a partir da resposta do cliente.
NÃO repita: "Oi, é do restaurante?" - vá direto ao acompanhamento!

🆘 NÚMERO DE EMERGÊNCIA: 5548996438314
Se houver problemas técnicos ou não conseguir agendar, redirecione!

INSTRUÇÕES DE FERRAMENTAS:
Quando usar send_media_message, use sempre:
- number: {whatsapp_number}
- media_type: 'image'

Para resultados financeiros (R$ 877.000):
- media: 'knowledge/relatorio.jpg'
- caption: 'Aqui estão os resultados reais dos nossos clientes'

Para crescimento (30%):
- media: 'knowledge/visualizacao.jpg' 
- caption: 'Visualização do crescimento dos nossos clientes'

SEMPRE use as ferramentas quando mencionar resultados!
"""
            
            # Adicionar mensagem à queue do usuário
            message_data = {
                'text': evolution_data['message'],
                'remote_jid': remote_jid,
                'push_name': push_name,
                'whatsapp_number': whatsapp_number,
                'message_type': message_type,
                'original_instructions': original_instructions,
                'timestamp': datetime.now().isoformat()
            }
            
            user_message_queues[user_id].append(message_data)
            logger.info(f"➕ Mensagem de texto adicionada à queue. "
                       f"Total na fila: {len(user_message_queues[user_id])}")
            
            # Cancelar timer anterior se existir
            if user_id in user_timers and not user_timers[user_id].done():
                user_timers[user_id].cancel()
                logger.info("⏹️ Timer anterior cancelado - nova mensagem recebida")
            
            # Criar novo timer para processamento em lote
            user_timers[user_id] = asyncio.create_task(
                process_user_messages_batch(user_id, whatsapp_number)
            )
            
            logger.info(f"⏱️ Timer de debounce iniciado ({DEBOUNCE_DELAY}s)")
            
            return {
                "message": "Mensagem de texto adicionada à queue",
                "queue_size": len(user_message_queues[user_id]),
                "debounce_delay": DEBOUNCE_DELAY,
                "processing_mode": "batch"
            }
        
        # 🎯 PROCESSAMENTO IMEDIATO para imagens e áudio (não aplicar debounce)
        else:
            logger.info("🎯 Processamento imediato (imagem/áudio)")
            
            # Usar session_id baseado no remote_jid para manter histórico
            session_id = f"elo-{remote_jid}"
            
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

INSTRUÇÕES DE FERRAMENTAS:
🖼️ ENVIO DE IMAGENS AUTOMÁTICO:
Quando mencionar resultados, SEMPRE envie imagem correspondente:

Para resultados financiais (R$ 877.000):
send_media_message(number='{whatsapp_number}', media_type='image',
media='knowledge/relatorio.jpg', caption='Aqui estão os resultados 
reais dos nossos clientes!')

Para crescimento (30%):
send_media_message(number='{whatsapp_number}', media_type='image', 
media='knowledge/visualizacao.jpg', caption='Visualização do 
crescimento dos nossos clientes!')

Para cases de sucesso:
send_media_message(number='{whatsapp_number}', media_type='image',
media='knowledge/cases.jpg', caption='Veja alguns dos nossos cases 
de sucesso!')

🎯 REGRA: SEMPRE combine send_text_message + send_media_message para 
maior impacto!

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
                logger.info("📝 Processando mensagem de texto (fallback)")
                message_with_context = (
                    f"{dynamic_instructions}\n\n"
                    f"MENSAGEM DO CLIENTE: {evolution_data['message']}"
                )
                response = vanessa.run(
                    message_with_context, 
                    session_id=session_id
                )
            
            logger.info(f"🔍 Resposta do agente - Tipo: {type(response)}")
            if hasattr(response, 'content'):
                logger.info(f"🔍 Content: {response.content}")
            if hasattr(response, 'tool_calls') and response.tool_calls:
                logger.info(f"🔧 Tool calls detectados: "
                           f"{len(response.tool_calls)}")
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

        return {
                "message": "Resposta enviada via WhatsApp (processamento imediato)",
                "processing_mode": "immediate"
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


@app.post("/enviar-lista-restaurantes")
async def enviar_lista_restaurantes(file: UploadFile = File(...)):
    """
    Endpoint para processar lista de restaurantes e enviar primeira mensagem
    Formato esperado do CSV: nome,numero
    """
    try:
        # Verificar se o arquivo é CSV
        if not file.filename.endswith('.csv'):
            return {"error": "Arquivo deve ser CSV"}
        
        # Ler conteúdo do arquivo
        content = await file.read()
        content_str = content.decode('utf-8')
        
        # Processar CSV
        csv_reader = csv.reader(content_str.splitlines())
        restaurantes_processados = []
        restaurantes_erro = []
        
        # Mensagem primeira interação
        primeira_mensagem = (
            "Oi! Aqui é a Vanessa da Elo Marketing. "
            "É de um restaurante? Vocês têm cardápio ou menu online?"
        )
        
        for i, row in enumerate(csv_reader):
            # Pular header se existir
            if i == 0 and ('nome' in row[0].lower() or 'name' in row[0].lower()):
                continue
                
            if len(row) < 2:
                restaurantes_erro.append({
                    "linha": i + 1,
                    "erro": "Formato inválido - necessário nome,numero"
                })
                continue
            
            nome = row[0].strip()
            numero = row[1].strip()
            
            # Limpar número (remover caracteres especiais)
            numero_limpo = ''.join(filter(str.isdigit, numero))
            
            if len(numero_limpo) < 10:
                restaurantes_erro.append({
                    "linha": i + 1,
                    "nome": nome,
                    "numero": numero,
                    "erro": "Número muito curto"
                })
                continue
            
            try:
                # Salvar no banco de dados
                conn = sqlite3.connect("restaurantes.db")
                cursor = conn.cursor()
                
                # Verificar se já existe
                cursor.execute(
                    "SELECT id, primeira_mensagem_enviada FROM restaurantes WHERE numero = ?",
                    (numero_limpo,)
                )
                existing = cursor.fetchone()
                
                if existing:
                    if existing[1]:  # Já enviou mensagem
                        restaurantes_erro.append({
                            "linha": i + 1,
                            "nome": nome,
                            "numero": numero_limpo,
                            "erro": "Mensagem já enviada anteriormente"
                        })
                        conn.close()
                        continue
                else:
                    # Inserir novo restaurante
                    cursor.execute(
                        """INSERT INTO restaurantes (nome, numero) 
                           VALUES (?, ?)""",
                        (nome, numero_limpo)
                    )
                
                # Para teste, enviar apenas para o número especificado
                numero_envio = "5548996438314"  # Número de teste
                
                if evolution_tools:
                    try:
                        # Enviar mensagem
                        result = evolution_tools.send_text_message(
                            number=numero_envio,
                            text=f"TESTE - {nome}: {primeira_mensagem}"
                        )
                        
                        # Marcar como enviado no banco
                        cursor.execute(
                            """UPDATE restaurantes 
                               SET primeira_mensagem_enviada = TRUE, data_envio = ?
                               WHERE numero = ?""",
                            (datetime.now(), numero_limpo)
                        )
                        
                        restaurantes_processados.append({
                            "nome": nome,
                            "numero": numero_limpo,
                            "numero_teste": numero_envio,
                            "status": "enviado",
                            "result": str(result)
                        })
                        
                    except Exception as e:
                        restaurantes_erro.append({
                            "linha": i + 1,
                            "nome": nome,
                            "numero": numero_limpo,
                            "erro": f"Erro ao enviar: {str(e)}"
                        })
                else:
                    restaurantes_erro.append({
                        "linha": i + 1,
                        "nome": nome,
                        "numero": numero_limpo,
                        "erro": "Evolution API não configurada"
                    })
                
                conn.commit()
                conn.close()
                
            except sqlite3.IntegrityError:
                restaurantes_erro.append({
                    "linha": i + 1,
                    "nome": nome,
                    "numero": numero_limpo,
                    "erro": "Número já existe no banco"
                })
            except Exception as e:
                restaurantes_erro.append({
                    "linha": i + 1,
                    "nome": nome,
                    "numero": numero,
                    "erro": str(e)
                })
        
        return {
            "status": "processado",
            "total_linhas": i + 1,
            "processados": len(restaurantes_processados),
            "erros": len(restaurantes_erro),
            "restaurantes_processados": restaurantes_processados,
            "restaurantes_erro": restaurantes_erro,
            "observacao": "MODO TESTE: Todas as mensagens foram enviadas para 5548996438314"
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao processar lista de restaurantes: {e}")
        return {"error": f"Erro interno: {str(e)}"}


@app.get("/restaurantes")
async def listar_restaurantes():
    """Lista todos os restaurantes cadastrados"""
    try:
        conn = sqlite3.connect("restaurantes.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, nome, numero, primeira_mensagem_enviada, 
                   data_envio, created_at
            FROM restaurantes 
            ORDER BY created_at DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        restaurantes = []
        for row in rows:
            restaurantes.append({
                "id": row[0],
                "nome": row[1],
                "numero": row[2],
                "primeira_mensagem_enviada": bool(row[3]),
                "data_envio": row[4],
                "created_at": row[5]
            })
        
        return {
            "total": len(restaurantes),
            "restaurantes": restaurantes
        }
        
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)
