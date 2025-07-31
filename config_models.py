"""
Configuração de Modelos de IA - Elo Marketing
============================================

Este arquivo centraliza as configurações dos modelos de IA para facilitar
testes e otimizações.
"""

import os

# 🚀 CONFIGURAÇÕES DE MODELOS OPENAI
OPENAI_MODELS = {
    # Modelos mais avançados (recomendados)
    "gpt-4o": {
        "id": "gpt-4o",
        "description": "Modelo multimodal mais avançado",
        "input_cost": 5.00,    # por milhão de tokens
        "output_cost": 15.00,  # por milhão de tokens
        "context": "128K",
        "capabilities": ["texto", "imagem", "áudio"],
        "recommended_for": "Tarefas complexas, análise multimodal"
    },
    
    "gpt-4.1": {
        "id": "gpt-4.1",
        "description": "Modelo mais recente com contexto estendido",
        "input_cost": 2.00,
        "output_cost": 8.00,
        "context": "1M",
        "capabilities": ["texto", "reasoning", "coding"],
        "recommended_for": "Documentos longos, análise de código"
    },
    
    # Modelos para reasoning
    "o1": {
        "id": "o1",
        "description": "Modelo especializado em reasoning",
        "input_cost": 15.00,
        "output_cost": 60.00,
        "context": "200K",
        "capabilities": ["reasoning complexo", "matemática", "ciência"],
        "recommended_for": "Problemas complexos que requerem reasoning"
    },
    
    # Modelos custo-benefício
    "gpt-4-turbo": {
        "id": "gpt-4-turbo",
        "description": "GPT-4 com boa relação custo-benefício",
        "input_cost": 10.00,
        "output_cost": 30.00,
        "context": "128K",
        "capabilities": ["texto", "imagem", "reasoning"],
        "recommended_for": "Aplicações que precisam de GPT-4 por menor custo"
    },
    
    "gpt-3.5-turbo": {
        "id": "gpt-3.5-turbo",
        "description": "Modelo rápido e econômico",
        "input_cost": 0.50,
        "output_cost": 1.50,
        "context": "16K",
        "capabilities": ["texto"],
        "recommended_for": "Chatbots, tarefas simples, alta velocidade"
    }
}

# 🔧 CONFIGURAÇÕES DE EMBEDDINGS
EMBEDDING_MODELS = {
    "openai-large": {
        "provider": "openai",
        "id": "text-embedding-3-large",
        "dimensions": 3072,
        "cost_per_million": 0.13,
        "description": "Embedding mais avançado da OpenAI",
        "recommended": True
    },
    
    "openai-small": {
        "provider": "openai", 
        "id": "text-embedding-3-small",
        "dimensions": 1536,
        "cost_per_million": 0.02,
        "description": "Embedding econômico da OpenAI"
    },
    
    "gemini": {
        "provider": "google",
        "id": "text-embedding-004",
        "dimensions": 768,
        "cost_per_million": 0.0,  # Gratuito até certo limite
        "description": "Embedding do Google Gemini"
    }
}

# ⚙️ CONFIGURAÇÃO ATIVA (mude aqui para testar diferentes modelos)
ACTIVE_CONFIG = {
    "main_model": "gpt-4o",  # Modelo principal
    "embedding_model": "openai-large",  # Modelo de embedding
    "fallback_model": "gpt-4-turbo",  # Modelo de fallback
    
    # Configurações de chunking otimizadas
    "chunking": {
        "chunk_size": 800,
        "overlap": 200,
        "num_documents": 10
    },
    
    # Configurações de temperatura por tipo de tarefa
    "temperatures": {
        "vendas": 0.7,      # Criativo mas controlado
        "agendamento": 0.3,  # Mais determinístico
        "suporte": 0.5      # Balanceado
    }
}

# 🔑 VALIDAÇÃO DE API KEYS


def validate_api_keys():
    """Valida se as API keys necessárias estão configuradas"""
    required_keys = {
        "OPENAI_API_KEY": "OpenAI",
        "GOOGLE_API_KEY": "Google (para calendar e fallback)"
    }
    
    missing_keys = []
    for key, service in required_keys.items():
        if not os.getenv(key):
            missing_keys.append(f"{key} ({service})")
    
    if missing_keys:
        print("⚠️ API Keys não configuradas:")
        for key in missing_keys:
            print(f"   - {key}")
        return False
    
    print("✅ Todas as API keys estão configuradas")
    return True


# 📊 FUNÇÃO PARA CALCULAR CUSTOS


def estimate_cost(model_name, input_tokens, output_tokens):
    """Estima o custo de uso de um modelo"""
    if model_name not in OPENAI_MODELS:
        return "Modelo não encontrado"
    
    model = OPENAI_MODELS[model_name]
    input_cost = (input_tokens / 1_000_000) * model["input_cost"]
    output_cost = (output_tokens / 1_000_000) * model["output_cost"]
    total_cost = input_cost + output_cost
    
    return {
        "input_cost": f"${input_cost:.4f}",
        "output_cost": f"${output_cost:.4f}", 
        "total_cost": f"${total_cost:.4f}",
        "model_info": model["description"]
    }


# 🎯 FUNÇÃO PARA OBTER CONFIGURAÇÃO ATIVA


def get_active_model_config():
    """Retorna a configuração do modelo ativo"""
    active_model = ACTIVE_CONFIG["main_model"]
    active_embedding = ACTIVE_CONFIG["embedding_model"]
    
    return {
        "model": OPENAI_MODELS[active_model],
        "embedding": EMBEDDING_MODELS[active_embedding],
        "config": ACTIVE_CONFIG
    }


if __name__ == "__main__":
    # Teste rápido das configurações
    print("🧪 Testando configurações...")
    validate_api_keys()
    
    config = get_active_model_config()
    print(f"📋 Modelo ativo: {config['model']['description']}")
    print(f"🔧 Embedding ativo: {config['embedding']['description']}")
    
    # Exemplo de cálculo de custo
    cost = estimate_cost("gpt-4o", 1000, 500)
    print(f"💰 Custo exemplo (1000 input + 500 output tokens): "
          f"{cost['total_cost']}") 