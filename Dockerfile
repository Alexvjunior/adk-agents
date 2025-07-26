FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código da API e diretórios necessários
COPY api_dudu.py .
COPY api.py .
COPY knowledge/ ./knowledge/

# Variáveis de ambiente
ENV PORT=8080
ENV PYTHONPATH=/app
ENV GOOGLE_API_KEY=""
ENV GOOGLE_CLIENT_ID=""
ENV GOOGLE_CLIENT_SECRET=""
ENV GOOGLE_PROJECT_ID=""
ENV GOOGLE_REFRESH_TOKEN=""
ENV EVOLUTION_API_URL=""
ENV EVOLUTION_API_KEY=""
ENV EVOLUTION_INSTANCE=""

# Expor porta
EXPOSE 8080

# Health check para a API do Agno
HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8080/ || exit 1

# Comando para iniciar a API do Agno com uvicorn na porta 8080
CMD ["uvicorn", "api_dudu:app", "--host", "0.0.0.0", "--port", "8080"] 