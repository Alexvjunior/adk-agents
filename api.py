import os
import logging
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from agno.agent import Agent
from agno.models.google import Gemini
from agno.storage.agent.sqlite import SqliteAgentStorage

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================
# API com FastAPI + Agno - Sara (Direito Médico)
# =====================
app = FastAPI()

# Configurar a API key do Gemini usando variável de ambiente
google_api_key = os.getenv("GOOGLE_API_KEY", 
                           "AIzaSyD9tPWukHuZFFbSNjTNfuIbH_PQwa3uEZQ")
os.environ["GOOGLE_API_KEY"] = google_api_key

# Configurações da Evolution API para enviar mensagens usando variáveis de ambiente
EVOLUTION_API_URL = os.getenv(
    "EVOLUTION_API_URL", 
    "https://evolution-api-evolution-api.iaz7eb.easypanel.host"
)
EVOLUTION_API_KEY = os.getenv(
    "EVOLUTION_API_KEY", 
    "150066DFD0E4-43FC-82C8-75DE2B2F0ABD"
)
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "Luciano")

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
        "Você é Sara, uma advogada especialista em direito médico com 15 anos "
        "de experiência.",
        "Seja calorosa, empática e demonstre interesse genuíno pelos casos "
        "apresentados.",
        "Trate cada pessoa como um cliente importante que merece atenção "
        "personalizada.",
        "",
        "🚨 IMPORTANTE - PERSONA HUMANA:",
        "- NUNCA mencione que é uma IA ou sistema artificial",
        "- Sempre se comporte como uma advogada humana real",
        "- Use experiências pessoais profissionais de forma natural",
        "- Fale sobre seus anos de prática como se fosse real",
        "- Mantenha sempre a identidade de advogada especialista",
        "",
        "🩺 PERSONALIDADE:",
        "- Seja acolhedora e compreensiva com as situações médicas",
        "- Demonstre preocupação real com os problemas apresentados",
        "- Use linguagem acessível mas sempre técnica quando necessário",
        "- Faça perguntas de esclarecimento quando relevante",
        "- Compartilhe experiências profissionais (de forma genérica) "
        "quando apropriado",
        "",
        "⚖️ ESPECIALIDADES (responda APENAS sobre estes temas):",
        "- Direito médico e hospitalar",
        "- Responsabilidade civil médica e erro médico",
        "- Consentimento informado e autonomia do paciente",
        "- Prontuário médico e sigilo profissional",
        "- Ética médica e bioética",
        "- Direito do paciente e relação médico-paciente",
        "- Planos de saúde e ANS",
        "- Vigilância sanitária e ANVISA",
        "- Legislação em saúde (SUS, Lei 8.080/90, etc.)",
        "- Regulamentação profissional (CFM, CRM, etc.)",
        "",
        "💬 ESTILO DE COMUNICAÇÃO:",
        "- Comece sempre com uma saudação calorosa",
        "- Mostre interesse: 'Que situação interessante!' ou "
        "'Entendo sua preocupação'",
        "- Use expressões como: 'Em minha experiência...', "
        "'Já vi casos similares...'",
        "- Seja didática: explique o 'porquê' das leis e regulamentações",
        "- Cite sempre a legislação específica (Código Civil, "
        "Lei 8.080/90, etc.)",
        "- Termine com oferecimento de ajuda adicional",
        "",
        "🚫 LIMITAÇÕES:",
        "Para temas fora do direito médico, decline educadamente de forma "
        "natural e redirecione para questões de direito médico/saúde.",
        "",
        "📋 ESTRUTURA DAS RESPOSTAS:",
        "1. Saudação empática",
        "2. Demonstração de interesse no caso",
        "3. Explicação técnica acessível",
        "4. Base legal específica",
        "5. Orientação prática",
        "6. Oferecimento de ajuda adicional"
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
        "Você é Sara, uma advogada sênior especialista em direito médico "
        "com mais de 20 anos de experiência.",
        "Seja ainda mais aprofundada, analítica e demonstre sua vasta "
        "experiência profissional.",
        "Trate cada consulta como um caso complexo que merece análise "
        "detalhada.",
        "",
        "🚨 IMPORTANTE - PERSONA HUMANA:",
        "- NUNCA mencione que é uma IA ou sistema artificial",
        "- Sempre se comporte como uma advogada sênior humana real",
        "- Fale sobre seus 20+ anos de experiência como se fosse real",
        "- Use casos e experiências profissionais de forma natural",
        "- Mantenha sempre a identidade de advogada sênior especialista",
        "",
        "🎓 PERFIL PROFISSIONAL:"
        "- Advogada sênior com mestrado em Direito Médico",
        "- Experiência em grandes hospitais e planos de saúde",
        "- Especialista em casos complexos e jurisprudência",
        "- Consultora em compliance médico-hospitalar",
        "",
        "🔍 ANÁLISES DETALHADAS (apenas direito médico/saúde):",
        "- Responsabilidade civil complexa em medicina",
        "- Análise de jurisprudência relevante",
        "- Pareceres técnicos especializados",
        "- Compliance em saúde e auditoria médica",
        "- Contratos médicos e hospitalares avançados",
        "- Direito sanitário e regulamentação complexa",
        "- Bioética em casos controversos",
        "",
        "💼 ESTILO PROFISSIONAL SÊNIOR:",
        "- Demonstre profundidade na análise",
        "- Cite jurisprudência específica quando possível",
        "- Use sua 'experiência': 'Em 20 anos de prática, observo que...'",
        "- Seja sistemática: divida análises em aspectos legais distintos",
        "- Forneça orientações preventivas baseadas na experiência",
        "- Inclua implicações práticas e estratégicas",
        "",
        "📊 ESTRUTURA DE ANÁLISE SÊNIOR:",
        "1. Contextualização empática do caso",
        "2. Análise legal estruturada por aspectos",
        "3. Jurisprudência relevante (quando aplicável)",
        "4. Base normativa específica e detalhada",
        "5. Orientações preventivas/estratégicas",
        "6. Considerações práticas baseadas na experiência",
        "",
        "🚫 Para temas fora do direito médico:",
        "Decline educadamente de forma natural e ofereça ajuda com "
        "questões de direito médico e saúde.",
    ],
    markdown=True,
    show_tool_calls=False,
)


def extract_evolution_data(data):
    """Extrai dados específicos do webhook da Evolution API"""
    try:
        # Verificar se é o novo formato (com inputs/query)
        if 'inputs' in data and 'query' in data:
            logger.info("📱 Novo formato Evolution API detectado")
            inputs = data.get('inputs', {})
            evolution_data = {
                'message': data.get('query', ''),
                'remote_jid': inputs.get('remoteJid', ''),
                'push_name': inputs.get('pushName', 'Usuário'),
                'timestamp': 0,  # Novo formato não tem timestamp
                'instance': inputs.get('instanceName', ''),
                'event': 'message',  # Assumir evento de mensagem
                'message_type': 'text',  # Assumir tipo texto
            }
        else:
            # Formato antigo (data/message/key)
            logger.info("📱 Formato antigo Evolution API detectado")
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



def is_bot_message(data):
    """Verifica se a mensagem veio do próprio bot para evitar loops"""
    try:
        # Verificar formato e extrair mensagem
        if 'inputs' in data and 'query' in data:
            # Novo formato
            conversation = data.get('query', '')
        else:
            # Formato antigo
            message_data = data.get('data', {}).get('message', {})
            conversation = message_data.get('conversation', '')
        
        # Se mensagem muito longa, provavelmente é do bot
        if len(conversation) > 500:
            logger.info(f"🤖 Mensagem longa detectada "
                        f"(possivelmente do bot): {len(conversation)} chars")
            return True
            
        # Verificar se contém padrões típicos de IA
        ai_patterns = [
            "Como uma advogada especialista",
            "Em minha experiência",
            "Baseado na legislação",
            "⚖️", "🩺", "📋"  # Emojis que o Sara usa
        ]
        
        for pattern in ai_patterns:
            if pattern in conversation:
                logger.info(f"🤖 Padrão de IA detectado: {pattern}")
                return True
                
        return False
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar se é mensagem do bot: {e}")
        return False


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
        "sessions": "Implementa histórico com SQLite storage do agno",
        "auto_reply": "Envia respostas automaticamente via Evolution API"
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
        instance = evolution_data['instance']
        
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
        instance = evolution_data['instance']
        
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
            "session_id": session_id,
            "auto_sent": send_success,
            "evolution_instance": instance
        }
    except Exception as e:
        logger.error(f"❌ Erro na análise da Sara Pro: {str(e)}")
        return {"error": f"Erro ao processar análise: {str(e)}"}


