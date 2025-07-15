import os
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.duckduckgo import DuckDuckGoTools


# =====================
# API com FastAPI + Agno usando Gemini
# =====================
app = FastAPI()

# Configurar a API key do Gemini (pode também usar variável de ambiente)
os.environ["GOOGLE_API_KEY"] = "AIzaSyD9tPWukHuZFFbSNjTNfuIbH_PQwa3uEZQ"

# Criar agente usando Gemini através do Agno
agent = Agent(
    name="agente_gemini", 
    role="Assistente que responde perguntas de forma direta e precisa",
    model=Gemini(id="gemini-2.0-flash-exp"),  # Usando Gemini 2.0 Flash
    tools=[DuckDuckGoTools()],  # Ferramenta de busca web disponível no Agno
    instructions=[
        "Responda perguntas de forma direta e precisa",
        "Use busca web quando necessário para informações atualizadas",
        "Sempre inclua fontes quando usar informações da web",
        "Seja conciso mas informativo"
    ],
    markdown=True,
    show_tool_calls=True,
)

# Agente alternativo usando Gemini 1.5 Pro para tarefas mais complexas
agent_pro = Agent(
    name="agente_gemini_pro", 
    role="Assistente avançado para tarefas complexas",
    model=Gemini(id="gemini-1.5-pro"),
    tools=[DuckDuckGoTools()],
    instructions=[
        "Forneça análises detalhadas e respostas abrangentes",
        "Use busca web para verificar informações recentes",
        "Inclua todas as fontes relevantes",
        "Organize a resposta de forma clara e estruturada"
    ],
    markdown=True,
    show_tool_calls=True,
)

# Classe personalizada para implementação direta do Gemini (backup)
class GeminiLLM:
    def __init__(self, model="models/gemini-2.0-flash", temperature=0.7):
        self.api_key = "AIzaSyD9tPWukHuZFFbSNjTNfuIbH_PQwa3uEZQ"
        self.model = model
        self.temperature = temperature

    def generate(self, prompt: str) -> str:
        base_url = "https://generativelanguage.googleapis.com/v1beta/models/"
        url = f"{base_url}{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": self.temperature}
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()["candidates"][0]["content"]["parts"][0]
            return result["text"]
        else:
            return f"[Erro Gemini]: {response.text}"


class InputData(BaseModel):
    question: str


@app.get("/")
async def root():
    return {
        "message": "API do Agno com Gemini funcionando!", 
        "endpoints": {
            "/ask": "Perguntas básicas com Gemini 2.0 Flash",
            "/ask-pro": "Perguntas complexas com Gemini 1.5 Pro", 
            "/ask-direct": "Acesso direto ao Gemini (sem ferramentas)"
        }
    }


@app.post("/ask")
async def ask_question(data: InputData):
    """Endpoint principal usando Gemini 2.0 Flash através do Agno"""
    try:
        response = agent.run(data.question)
        # Extrair apenas o conteúdo da mensagem
        message = response.content if hasattr(response, 'content') else str(response)
        return {"message": message}
    except Exception as e:
        return {"error": f"Erro ao processar pergunta: {str(e)}"}


@app.post("/ask-pro")
async def ask_question_pro(data: InputData):
    """Endpoint para perguntas complexas usando Gemini 1.5 Pro"""
    try:
        response = agent_pro.run(data.question)
        # Extrair apenas o conteúdo da mensagem
        message = response.content if hasattr(response, 'content') else str(response)
        return {"message": message}
    except Exception as e:
        return {"error": f"Erro ao processar pergunta: {str(e)}"}


@app.post("/ask-direct")
async def ask_direct(data: InputData):
    """Endpoint usando implementação direta do Gemini (sem Agno)"""
    try:
        gemini_llm = GeminiLLM()
        answer = gemini_llm.generate(data.question)
        return {"message": answer, "model": "gemini-2.0-flash-direct"}
    except Exception as e:
        return {"error": f"Erro ao processar pergunta: {str(e)}"}
