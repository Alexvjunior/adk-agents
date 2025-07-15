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

# Copiar o código da API
COPY api.py .

# Variáveis de ambiente
ENV PORT=8000
ENV PYTHONPATH=/app
ENV GOOGLE_API_KEY="AIzaSyD9tPWukHuZFFbSNjTNfuIbH_PQwa3uEZQ"

# Expor porta
EXPOSE 8000

# Health check para a API do Agno
HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/ || exit 1

# Comando para iniciar a API do Agno com uvicorn
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"] 