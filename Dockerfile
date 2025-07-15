FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema se necessário
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo o código dos agentes
COPY . .

# Variáveis de ambiente
ENV PORT=5000
ENV PYTHONPATH=/app

# Expor porta
EXPOSE 5000

# Health check usando a API nativa do ADK
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/list-apps || exit 1

# Comando para iniciar a API nativa do ADK
CMD ["adk", "api_server", "--port=5000", "--host=0.0.0.0", "."] 