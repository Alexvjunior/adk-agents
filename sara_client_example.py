#!/usr/bin/env python3
"""
Cliente exemplo para conversar com Sara via API ADK
Após fazer deploy no EasyPanel ou rodar localmente com: adk api_server
"""

import requests
import sys
from datetime import datetime


class SaraClient:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url.rstrip('/')
        self.session_id = None
        self.user_id = "user_" + str(int(datetime.now().timestamp()))
        
    def check_connection(self):
        """Verifica se a API está rodando"""
        try:
            response = requests.get(f"{self.base_url}/list-apps")
            response.raise_for_status()
            apps = response.json()
            print(f"✅ API conectada! Agentes disponíveis: {apps}")
            return "sara-medical-law-agent" in apps
        except Exception as e:
            print(f"❌ Erro ao conectar com API: {e}")
            return False
    
    def create_session(self):
        """Cria uma nova sessão com Sara"""
        try:
            url = (f"{self.base_url}/apps/sara-medical-law-agent/"
                   f"users/{self.user_id}/sessions")
            response = requests.post(url, json={"state": {}})
            response.raise_for_status()
            
            session_data = response.json()
            self.session_id = session_data["id"]  # Usar "id" não "sessionId"
            print(f"✅ Sessão criada: {self.session_id}")
            return True
        except Exception as e:
            print(f"❌ Erro ao criar sessão: {e}")
            return False
    
    def send_message(self, message):
        """Envia mensagem para Sara"""
        if not self.session_id:
            print("❌ Sessão não criada. Criando nova sessão...")
            if not self.create_session():
                return None
        
        try:
            payload = {
                "appName": "sara-medical-law-agent",
                "userId": self.user_id,
                "sessionId": self.session_id,
                "newMessage": {
                    "parts": [{"text": message}]
                }
            }
            
            print(f"📤 Enviando: {message}")
            response = requests.post(f"{self.base_url}/run", json=payload)
            response.raise_for_status()
            
            result = response.json()
            # A resposta é um array, pegar o primeiro elemento
            if result and len(result) > 0:
                sara_response = result[0]["content"]["parts"][0]["text"]
                print(f"💬 Sara: {sara_response}")
                return sara_response
            else:
                print("❌ Resposta vazia da Sara")
                return None
                
        except Exception as e:
            print(f"❌ Erro ao enviar mensagem: {e}")
            return None


def main():
    # Configurar URL base
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:5000"  # Local
        # base_url = "https://seu-dominio.easypanel.host"  # EasyPanel
    
    print(f"🔗 Conectando com: {base_url}")
    
    # Criar cliente
    client = SaraClient(base_url)
    
    # Verificar conexão
    if not client.check_connection():
        print("❌ Não foi possível conectar com a API")
        sys.exit(1)
    
    # Exemplos de perguntas
    perguntas = [
        "Olá Sara! Quais são os direitos básicos dos pacientes?",
        "O que diz a lei sobre o prontuário médico?",
        "Quais são as regras da telemedicina no Brasil?",
        "Como funciona o sigilo médico?",
        "Quais são as penalidades por erro médico?"
    ]
    
    print("\n" + "="*60)
    print("🏥 CONVERSANDO COM SARA - ESPECIALISTA EM DIREITO MÉDICO")
    print("="*60)
    
    # Modo interativo ou automático
    if "--interactive" in sys.argv:
        # Modo interativo
        while True:
            try:
                pergunta = input("\n💭 Sua pergunta (ou 'sair'): ").strip()
                if pergunta.lower() in ['sair', 'exit', 'quit']:
                    break
                if pergunta:
                    client.send_message(pergunta)
            except KeyboardInterrupt:
                print("\n👋 Tchau!")
                break
    else:
        # Modo demonstração automática
        for i, pergunta in enumerate(perguntas, 1):
            print(f"\n--- Pergunta {i} ---")
            client.send_message(pergunta)
            print("-" * 40)


if __name__ == "__main__":
    main() 