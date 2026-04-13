"""
Configurações centrais da aplicação DeclaraAI.
Carrega variáveis de ambiente com fallback para valores padrão.
"""

from pydantic_settings import BaseSettings
from pathlib import Path


class Configuracoes(BaseSettings):
    """Configurações globais carregadas via variáveis de ambiente ou arquivo .env."""

    # Informações da aplicação
    NOME_APP: str = "DeclaraAI"
    VERSAO_APP: str = "1.0.0"
    DEBUG: bool = False

    # Banco de dados relacional (SQLite)
    DATABASE_URL: str = "sqlite:///./data/declaraai.db"

    # Caminhos de dados
    CAMINHO_UPLOADS: str = "./data/uploads"
    CAMINHO_BASE_CONHECIMENTO: str = "./data/knowledge_base"
    CAMINHO_CHROMA: str = "./data/chroma_db"

    # Configurações de chunking
    # chunk_size=600: equilibra contexto e precisão semântica em documentos fiscais
    # overlap=80: preserva continuidade entre fragmentos adjacentes
    CHUNK_SIZE: int = 600
    CHUNK_OVERLAP: int = 80

    # Modelo de embeddings (multilíngue, leve, código aberto)
    # paraphrase-multilingual-MiniLM-L12-v2: suporte a PT-BR, 384 dims, rápido
    MODELO_EMBEDDINGS: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    # Integração com Ollama (LLM local)
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODELO: str = "mistral"

    # Recuperação semântica
    TOP_K_RESULTADOS: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Instância global de configurações
configuracoes = Configuracoes()
