"""
Ponto de entrada da API DeclaraAI.

Configura o aplicativo FastAPI, registra as rotas, inicializa o banco de dados
e executa a ingestão automática da base de conhecimento na primeira execução.
"""

import asyncio
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
from app.api.routes_evaluation import roteador as roteador_avaliacao
from app.api.routes_knowledge import roteador as roteador_base
from app.api.routes_perfil import roteador as roteador_perfil

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

    # Inicializa o singleton do ServicoRAG e auto-ingere se necessário
    try:
        from app.services.rag_service import get_servico_rag

        servico_rag = get_servico_rag()
        if servico_rag.banco_vetorial.total_chunks() == 0:
            logger.info("ChromaDB vazio — iniciando ingestão automática da base de conhecimento...")
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
                f"ChromaDB já inicializado: {servico_rag.banco_vetorial.total_chunks()} chunk(s) disponíveis."
            )
    except Exception as erro:
        logger.warning(
            f"Ingestão automática falhou (não crítico): {erro}. "
            "Use POST /ingest para indexar manualmente."
        )

    # Pré-aquece embeddings e modelo LLM em segundo plano para eliminar latência na primeira consulta.
    async def _aquecer_tudo():
        import asyncio
        from app.rag.embeddings import GeradorEmbeddings
        from app.rag.generator import GeradorResposta
        logger.info("Aquecendo modelo de embeddings...")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, GeradorEmbeddings().gerar, "aquecimento")
        logger.info("Modelo de embeddings pré-carregado.")
        await GeradorResposta().aquecer()

    asyncio.create_task(_aquecer_tudo())
    logger.info("Aquecimento de modelos iniciado em segundo plano.")

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
app.include_router(roteador_avaliacao, tags=["Avaliação"])
app.include_router(
    roteador_base,
    prefix="/knowledge",
    tags=["Base de Conhecimento"],
)
app.include_router(
    roteador_perfil,
    prefix="/declarante",
    tags=["Perfil do Declarante"],
)


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
