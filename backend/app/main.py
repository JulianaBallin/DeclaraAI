"""
Ponto de entrada da API DeclaraAI.

Configura o aplicativo FastAPI, registra as rotas, inicializa o banco de dados
e executa a ingestão automática da base de conhecimento na primeira execução.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import configuracoes
from app.core.database import criar_tabelas
from app.api.routes_chat import roteador as roteador_chat
from app.api.routes_documents import roteador as roteador_documentos
from app.api.routes_history import roteador as roteador_historico

# ---------------------------------------------------------------------------
# Configuração de logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Ciclo de vida da aplicação
# ---------------------------------------------------------------------------

@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """
    Gerencia inicialização e encerramento da aplicação.

    Na inicialização:
    - Cria os diretórios de dados necessários
    - Inicializa o banco de dados SQLite
    - Auto-ingere a base de conhecimento se o ChromaDB estiver vazio

    No encerramento:
    - Registra o evento de encerramento
    """
    logger.info(f"Iniciando {configuracoes.NOME_APP} v{configuracoes.VERSAO_APP}")

    # Garante que os diretórios de dados existam
    for caminho in [
        configuracoes.CAMINHO_UPLOADS,
        configuracoes.CAMINHO_BASE_CONHECIMENTO,
        configuracoes.CAMINHO_CHROMA,
    ]:
        Path(caminho).mkdir(parents=True, exist_ok=True)

    # Inicializa banco de dados relacional
    criar_tabelas()

    # Auto-ingestão da base de conhecimento apenas se o ChromaDB estiver vazio
    try:
        from app.services.rag_service import ServicoRAG
        from app.rag.vector_store import BancoVetorial

        banco_vetorial = BancoVetorial()
        if banco_vetorial.total_chunks() == 0:
            logger.info("ChromaDB vazio — iniciando ingestão automática da base de conhecimento...")
            servico_rag = ServicoRAG()
            total = servico_rag.ingerir_base_conhecimento()
            if total > 0:
                logger.info(f"Ingestão automática concluída: {total} chunk(s) indexado(s).")
            else:
                logger.info(
                    "Base de conhecimento vazia. "
                    "Adicione arquivos em 'data/knowledge_base/' e chame POST /ingest."
                )
        else:
            logger.info(
                f"ChromaDB já inicializado: {banco_vetorial.total_chunks()} chunk(s) disponíveis."
            )
    except Exception as erro:
        logger.warning(
            f"Ingestão automática falhou (não crítico): {erro}. "
            "Use POST /ingest para indexar manualmente."
        )

    yield  # Aplicação em execução

    logger.info(f"{configuracoes.NOME_APP} encerrado.")


# ---------------------------------------------------------------------------
# Criação da aplicação FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title=configuracoes.NOME_APP,
    version=configuracoes.VERSAO_APP,
    description=(
        "API do DeclaraAI — assistente inteligente com RAG para organização de "
        "documentos e apoio à declaração do imposto de renda pessoa física."
    ),
    lifespan=ciclo_de_vida,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# Middlewares
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Em produção: restringir às origens permitidas
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Registro de rotas
# ---------------------------------------------------------------------------

app.include_router(roteador_chat, tags=["Chat RAG"])
app.include_router(
    roteador_documentos,
    prefix="/documents",
    tags=["Documentos"],
)
app.include_router(roteador_historico, tags=["Histórico"])


# ---------------------------------------------------------------------------
# Rota raiz (health check)
# ---------------------------------------------------------------------------

@app.get("/", summary="Health check", tags=["Sistema"])
async def raiz():
    """Verifica se a API está operacional."""
    return {
        "app": configuracoes.NOME_APP,
        "versao": configuracoes.VERSAO_APP,
        "status": "online",
        "docs": "/docs",
    }
