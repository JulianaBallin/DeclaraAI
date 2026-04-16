# ============================================================
# DeclaraAI — Backend Dockerfile
# Python 3.11-slim para imagem menor
# ============================================================

FROM python:3.11-slim

# Metadados
LABEL maintainer="DeclaraAI Team"
LABEL description="Backend FastAPI com pipeline RAG para o DeclaraAI"

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependências do sistema: compilação, pdfplumber e tesseract (OCR para imagens)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        tesseract-ocr \
        tesseract-ocr-por \
        tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
# Separado do COPY do código para aproveitar cache de camadas Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código da aplicação
COPY app/ ./app/

# Cria diretórios de dados (serão sobrescritos pelo volume no docker-compose)
RUN mkdir -p data/uploads data/knowledge_base data/chroma_db

# Porta exposta pelo Uvicorn
EXPOSE 8000

# Healthcheck simples
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/').raise_for_status()" || exit 1

# Inicia o servidor ASGI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
