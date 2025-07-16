import os
import logging
from fastapi import FastAPI, Request
from agno.agent import Agent
from agno.models.google import Gemini
from agno.storage.agent.sqlite import SqliteAgentStorage

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================
# API com FastAPI + Agno - Sara (Direito Médico)
# =====================
app = FastAPI()

# Configurar a API key do Gemini
os.environ["GOOGLE_API_KEY"] = "AIzaSyD9tPWukHuZFFbSNjTNfuIbH_PQwa3uEZQ"

# Configurar storage SQLite para sessões
storage = SqliteAgentStorage(table_name="sessions", db_file="sessions.db")

# Criar agente Sara - Especialista em Direito Médico
sara = Agent(
    name="Sara", 
    role="Especialista em Direito Médico e da Saúde",
    model=Gemini(id="gemini-1.5-flash"),
    storage=storage,
    add_history_to_messages=True,
    instructions=[
        "Você é Sara, uma especialista em direito médico e da saúde.",
        "Responda APENAS perguntas relacionadas a:",
        "- Direito médico",
        "- Direito da saúde",
        "- Responsabilidade civil médica",
        "- Erro médico",
        "- Consentimento informado",
        "- Prontuário médico",
        "- Sigilo médico",
        "- Ética médico",
        "- Legislação em saúde",
        "- Regulamentação de profissões da saúde",
        "- Direito do paciente",
        "- Planos de saúde",
        "- Vigilância sanitária",
        "- Bioética e biodireito",
        "",
        "Para perguntas fora desses temas, responda:",
        "'Desculpe, sou especializada apenas em direito médico e da saúde. "
        "Por favor, faça perguntas relacionadas a esses temas.'",
        "",
        "Sempre cite a legislação brasileira quando aplicável "
        "(Código Civil, Código de Ética Médica, Lei 8.080/90, etc.)",
        "Seja precisa, técnica e didática nas explicações.",
        "Use exemplos práticos quando apropriado."
    ],
    markdown=True,
    show_tool_calls=False,
)

# Agente Sara Pro para análises mais complexas
sara_pro = Agent(
    name="Sara Pro", 
    role="Especialista Sênior em Direito Médico e da Saúde",
    model=Gemini(id="gemini-1.5-pro"),
    storage=storage,
    add_history_to_messages=True,
    instructions=[
        "Você é Sara Pro, uma especialista sênior em direito médico "
        "e da saúde.",
        "Forneça análises jurídicas detalhadas APENAS sobre:",
        "- Direito médico e da saúde",
        "- Casos complexos de responsabilidade médica",
        "- Análise de jurisprudência em saúde",
        "- Pareceres técnicos em direito médico",
        "- Compliance em saúde",
        "- Contratos médicos e hospitalares",
        "- Direito sanitário",
        "",
        "Para temas fora do direito médico/saúde, responda:",
        "'Minha especialidade é exclusivamente direito médico e da saúde. "
        "Posso ajudar apenas com questões dessa área.'",
        "",
        "Inclua sempre:",
        "- Base legal específica",
        "- Jurisprudência relevante quando possível",
        "- Aspectos práticos e preventivos",
        "- Estruture a resposta de forma organizada",
        "- Use linguagem técnica mas acessível"
    ],
    markdown=True,
    show_tool_calls=False,
)


def extract_evolution_data(data):
    """Extrai dados específicos do webhook da Evolution API"""
    try:
        # Extrair dados específicos da Evolution API
        conversation_path = data.get('data', {}).get('message', {})
        key_path = data.get('data', {}).get('key', {})
        
        evolution_data = {
            'message': conversation_path.get('conversation', ''),
            'remote_jid': key_path.get('remoteJid', ''),
            'push_name': data.get('data', {}).get('pushName', 'Usuário'),
            'timestamp': data.get('data', {}).get('messageTimestamp', 0),
            'instance': data.get('instance', ''),
            'event': data.get('event', ''),
            'message_type': data.get('data', {}).get('messageType', ''),
        }
        
        logger.info("📱 Dados Evolution extraídos:")
        logger.info(f"   - Mensagem: {evolution_data['message']}")
        logger.info(f"   - RemoteJid: {evolution_data['remote_jid']}")
        logger.info(f"   - Nome: {evolution_data['push_name']}")
        logger.info(f"   - Timestamp: {evolution_data['timestamp']}")
        logger.info(f"   - Instância: {evolution_data['instance']}")
        
        return evolution_data
    except Exception as e:
        logger.error(f"❌ Erro ao extrair dados da Evolution: {e}")
        return None


@app.get("/")
async def root():
    return {
        "message": "Sara - Especialista em Direito Médico e da Saúde", 
        "description": (
            "Assistente especializada em direito médico, "
            "responsabilidade civil médica, ética médica, "
            "direito do paciente e legislação em saúde."
        ),
        "endpoints": {
            "/ask": "Consultas básicas em direito médico",
            "/ask-pro": "Análises jurídicas complexas em direito médico", 
            "/especialidades": "Áreas de especialização"
        },
        "example_curl": (
            "curl -X POST http://127.0.0.1:8080/ask "
            "-H 'Content-Type: application/json' "
            "-d '{\"question\": \"Quais são os requisitos "
            "do consentimento informado?\"}'"
        ),
        "evolution_api": "Compatível com webhooks da Evolution API",
        "sessions": "Implementa histórico com SQLite storage do agno"
    }


@app.get("/especialidades")
async def especialidades():
    return {
        "areas_especializacao": [
            "Direito médico",
            "Direito da saúde", 
            "Responsabilidade civil médica",
            "Erro médico",
            "Consentimento informado",
            "Prontuário médico",
            "Sigilo médico",
            "Ética médica",
            "Legislação em saúde",
            "Regulamentação de profissões da saúde",
            "Direito do paciente",
            "Planos de saúde",
            "Vigilância sanitária",
            "Bioética e biodireito"
        ]
    }


@app.post("/ask")
async def ask_sara(request: Request):
    """Consulta com Sara - Especialista em Direito Médico"""
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
                    "data.message.conversation"
                )
            }
        
        question = evolution_data['message']
        remote_jid = evolution_data['remote_jid']
        push_name = evolution_data['push_name']
        
        logger.info(f"   - Pergunta final: {question}")
        logger.info(f"   - RemoteJid: {remote_jid}")
        logger.info(f"   - Nome do usuário: {push_name}")
        
        # Usar session_id baseado no remote_jid
        session_id = f"evolution-{remote_jid}"
        
        # Enviar para Sara com session_id (histórico automático)
        logger.info("⚖️ Sara analisando a questão jurídica...")
        response = sara.run(question, session_id=session_id)
        
        # Extrair apenas o conteúdo da mensagem
        message = (response.content if hasattr(response, 'content') 
                   else str(response))
        
        logger.info(f"✅ Sara respondeu com sucesso "
                    f"(tamanho: {len(message)} caracteres)")
        
        return {
            "message": message, 
            "specialist": "Sara - Direito Médico",
            "user": push_name,
            "remote_jid": remote_jid,
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"❌ Erro na consulta com Sara: {str(e)}")
        return {"error": f"Erro ao processar consulta: {str(e)}"}


@app.post("/ask-pro")
async def ask_sara_pro(request: Request):
    """Análise jurídica complexa com Sara Pro"""
    try:
        # Log completo do que estamos recebendo
        body = await request.body()
        logger.info("📥 DADOS RAW RECEBIDOS (PRO - Evolution API):")
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
                    "data.message.conversation"
                )
            }
        
        question = evolution_data['message']
        remote_jid = evolution_data['remote_jid']
        push_name = evolution_data['push_name']
        
        logger.info(f"   - Pergunta final: {question}")
        logger.info(f"   - RemoteJid: {remote_jid}")
        logger.info(f"   - Nome do usuário: {push_name}")
        
        # Usar session_id baseado no remote_jid
        session_id = f"evolution-pro-{remote_jid}"
        
        # Enviar para Sara Pro com session_id (histórico automático)
        logger.info("⚖️ Sara Pro fazendo análise jurídica detalhada...")
        response = sara_pro.run(question, session_id=session_id)
        
        # Extrair apenas o conteúdo da mensagem
        message = (response.content if hasattr(response, 'content') 
                   else str(response))
        
        logger.info(f"✅ Sara Pro finalizou análise "
                    f"(tamanho: {len(message)} caracteres)")
        
        return {
            "message": message, 
            "specialist": "Sara Pro - Direito Médico Sênior",
            "user": push_name,
            "remote_jid": remote_jid,
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"❌ Erro na análise da Sara Pro: {str(e)}")
        return {"error": f"Erro ao processar análise: {str(e)}"}


