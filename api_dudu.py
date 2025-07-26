import os
import logging
import json
import tempfile
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

# Carregar variáveis de ambiente
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Usar variável de ambiente para Google API Key
google_api_key = os.getenv("GOOGLE_API_KEY", 
                           "AIzaSyD9tPWukHuZFFbSNjTNfuIbH_PQwa3uEZQ")
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
    instructions="Use sempre o FAQ para responder perguntas. Procure por "
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
                "redirect_uris": ["http://localhost", "https://agentes-agents.iaz7eb.easypanel.host/"]
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

# Definir ferramentas baseado na disponibilidade do calendário
tools = [shell_tools]
if calendar:
    tools.append(calendar)
    logger.info("Google Calendar configurado com sucesso")
else:
    warning_msg = ("Google Calendar não configurado - "
                   "verifique as variáveis de ambiente")
    logger.warning(warning_msg)


# Criar agente Vanessa - Vendedora da Elo Marketing
vanessa = Agent(
    name="Vanessa",
    role="Vendedora da Elo Marketing especializada em restaurantes",
    model=Gemini(id="gemini-2.0-flash"),
    storage=storage,
    tools=tools,  # Adicionado shell_tools
    knowledge=agent_knowledge,
    add_history_to_messages=True,
    instructions=[
        "Você é Vanessa, vendedora da Elo Marketing especializada em "
        "ajudar restaurantes.",
        "",
        "INFORMAÇÕES DA EMPRESA (das conversas reais):",
        "- Empresa: Elo Marketing Digital",
        "- Localização: Florianópolis, Santa Catarina",
        "- Tempo de mercado: 19 anos (completando 19 anos de mercado)",
        "- Site: https://elomarketing.com.br/",
        "- Especialidade: Restaurantes de frutos do mar e outros tipos",
        "",
        "Seu objetivo é captar leads qualificados e marcar reuniões com o "
        "especialista Eduardo.",
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
        "conversacionais.",
        "",
        "Nunca pressione o cliente. Seja consultiva e amigável.",
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
        "Quando alguém perguntar sobre cases de sucesso, sempre mencione "
        "o faturamento de R$ 862.000 em um mês com investimento de R$ 7 mil.",
        "",
        "Quando perguntarem sobre resultados, mencione o crescimento de "
        "300% que conseguimos para restaurantes parceiros.",
        "",
        "ABERTURA PADRÃO: Sempre comece conversas com 'Oi, é do Restaurante? "
        "Vocês têm cardápio ou menu online?' (baseado nas conversas reais)."
        "",
        "📩 IMPORTANTE - MENSAGEM AUTOMÁTICA:",
        "- A primeira mensagem 'Oi, é do Restaurante? Vocês têm cardápio ou "
        "menu online?' será SEMPRE enviada automaticamente",
        "- Quando o cliente responder qualquer coisa, prossiga naturalmente",
        "- NÃO repita a abertura padrão se o cliente já respondeu",
        "- Continue a conversa baseada na resposta do cliente:",
        "  * Se disser 'sim' → pergunte sobre resultados atuais",
        "  * Se disser 'não' → explique benefícios do marketing digital",
        "  * Se perguntar sobre preços → fale de resultados primeiro",
        "  * Se quiser reunião → inicie processo de agendamento",
        "- Sempre consulte sua base de conhecimento para respostas precisas"
    ],
    markdown=True,
    show_tool_calls=False,
)


def extract_evolution_data(data):
    """Extrai dados da Evolution API"""
    try:
        # Estrutura típica da Evolution API
        if isinstance(data, dict):
            # Tentar diferentes estruturas possíveis
            message = None
            remote_jid = None
            push_name = None
            instance = None

            # Opção 1: data.message.conversation
            if 'message' in data and isinstance(data['message'], dict):
                if 'conversation' in data['message']:
                    message = data['message']['conversation']
                elif 'text' in data['message']:
                    message = data['message']['text']

            # Opção 2: data.text ou data.message direto
            elif 'text' in data:
                message = data['text']
            elif 'message' in data and isinstance(data['message'], str):
                message = data['message']
            elif 'question' in data:  # Para testes diretos
                message = data['question']

            # Extrair informações do remetente
            if 'key' in data and isinstance(data['key'], dict):
                remote_jid = data['key'].get('remoteJid', 'unknown')
            elif 'from' in data:
                remote_jid = data['from']

            if 'pushName' in data:
                push_name = data['pushName']
            elif 'sender_name' in data:
                push_name = data['sender_name']

            if 'instance' in data:
                instance = data['instance']

            return {
                'message': message,
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

        if not evolution_data or not evolution_data['message']:
            logger.warning("Mensagem não encontrada nos dados da Evolution")
            return {
                "error": "Mensagem não encontrada",
                "received_data": data,
                "hint": (
                    "Certifique-se de que a mensagem está em "
                    "data.message.conversation ou data.question"
                )
            }

        question = evolution_data['message']
        remote_jid = evolution_data['remote_jid']
        push_name = evolution_data['push_name']

        logger.info(f"   - Mensagem final: {question}")
        logger.info(f"   - RemoteJid: {remote_jid}")
        logger.info(f"   - Nome do usuário: {push_name}")

        # Usar session_id baseado no remote_jid para manter histórico
        session_id = f"elo-{remote_jid}"

        # Enviar para Vanessa com session_id (histórico automático)
        logger.info("🎯 Vanessa consultando base de conhecimento e "
                    "respondendo...")
        response = vanessa.run(question, session_id=session_id)

        # Extrair apenas o conteúdo da mensagem com verificação de None
        if response is None:
            message = "Erro: Resposta vazia do agente"
        elif hasattr(response, 'content') and response.content:
            message = response.content
        else:
            message = str(response) if response else "Erro: Resposta inválida"
        
        # Garantir que message nunca seja None
        if message is None:
            message = "Erro: Não foi possível obter resposta"

        logger.info(f"✅ Vanessa respondeu com sucesso "
                    f"(tamanho: {len(message)} caracteres)")

        return {
            "message": message,
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
