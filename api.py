import os
import requests
import logging
from fastapi import FastAPI
from pydantic import BaseModel
from agno.agent import Agent
from agno.models.google import Gemini

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================
# API com FastAPI + Agno - Sara (Direito Médico)
# =====================
app = FastAPI()

# Configurar a API key do Gemini (pode também usar variável de ambiente)
os.environ["GOOGLE_API_KEY"] = "AIzaSyD9tPWukHuZFFbSNjTNfuIbH_PQwa3uEZQ"

# Criar agente Sara Sara - Especialista em Direito Médico
sara = Agent(
    name="Sara", 
    role="Especialista em Direito Médico e da Saúde",
    model=Gemini(id="gemini-1.5-flash"),
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
        "'Desculpe, sou especializada apenas em direito médico e da saúde. Por favor, faça perguntas relacionadas a esses temas.'",
        "",
        "Sempre cite a legislação brasileira quando aplicável (Código Civil, Código de Ética Médica, Lei 8.080/90, etc.)",
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
    instructions=[
        "Você é Sara Pro, uma especialista sênior em direito médico e da saúde.",
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
        "'Minha especialidade é exclusivamente direito médico e da saúde. Posso ajudar apenas com questões dessa área.'",
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

class InputData(BaseModel):
    question: str


@app.get("/")
async def root():
    return {
        "message": "Sara - Especialista em Direito Médico e da Saúde", 
        "description": "Assistente especializada em direito médico, responsabilidade civil médica, ética médica, direito do paciente e legislação em saúde.",
        "endpoints": {
            "/ask": "Consultas básicas em direito médico",
            "/ask-pro": "Análises jurídicas complexas em direito médico", 
            "/especialidades": "Áreas de especialização"
        },
        "example_curl": "curl -X POST http://127.0.0.1:80/ask -H 'Content-Type: application/json' -d '{\"question\": \"Quais são os requisitos do consentimento informado?\"}'"
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
async def ask_sara(data: InputData):
    """Consulta com Sara - Especialista em Direito Médico"""
    try:
        # Log do que estamos recebendo
        logger.info(f"📥 Sara recebeu consulta:")
        logger.info(f"   - Pergunta: {data.question}")
        logger.info(f"   - Tamanho: {len(data.question)} caracteres")
        
        # Enviar para Sara
        logger.info("⚖️ Sara analisando a questão jurídica...")
        response = sara.run(data.question)
        
        # Extrair apenas o conteúdo da mensagem
        message = response.content if hasattr(response, 'content') else str(response)
        
        logger.info(f"✅ Sara respondeu com sucesso (tamanho: {len(message)} caracteres)")
        
        return {"message": message, "specialist": "Sara - Direito Médico"}
    except Exception as e:
        logger.error(f"❌ Erro na consulta com Sara: {str(e)}")
        return {"error": f"Erro ao processar consulta: {str(e)}"}


@app.post("/ask-pro")
async def ask_sara_pro(data: InputData):
    """Análise jurídica complexa com Sara Pro"""
    try:
        # Log do que estamos recebendo
        logger.info(f"📥 Sara Pro recebeu consulta complexa:")
        logger.info(f"   - Pergunta: {data.question}")
        logger.info(f"   - Tamanho: {len(data.question)} caracteres")
        
        # Enviar para Sara Pro
        logger.info("⚖️ Sara Pro fazendo análise jurídica detalhada...")
        response = sara_pro.run(data.question)
        
        # Extrair apenas o conteúdo da mensagem
        message = response.content if hasattr(response, 'content') else str(response)
        
        logger.info(f"✅ Sara Pro finalizou análise (tamanho: {len(message)} caracteres)")
        
        return {"message": message, "specialist": "Sara Pro - Direito Médico Sênior"}
    except Exception as e:
        logger.error(f"❌ Erro na análise da Sara Pro: {str(e)}")
        return {"error": f"Erro ao processar análise: {str(e)}"}
