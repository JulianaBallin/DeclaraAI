"""
Rotas da API para o chat com RAG e gerenciamento da base de conhecimento.
"""

from fastapi import APIRouter, HTTPException
from app.schemas.document import RequisicaoChat, RespostaChat
from app.services.rag_service import ServicoRAG, get_servico_rag
import logging

logger = logging.getLogger(__name__)

roteador = APIRouter()


@roteador.post(
    "/chat",
    response_model=RespostaChat,
    summary="Enviar pergunta ao assistente RAG",
    description=(
        "Recebe uma pergunta em linguagem natural, recupera trechos relevantes "
        "da base de conhecimento e gera uma resposta contextualizada via LLM."
    ),
)
async def chat(requisicao: RequisicaoChat) -> RespostaChat:
    """
    Endpoint principal do chat.

    Pipeline executado:
    1. Busca semântica no ChromaDB
    2. Montagem do contexto para o LLM
    3. Geração de resposta via Ollama
    """
    if not requisicao.pergunta.strip():
        raise HTTPException(status_code=422, detail="A pergunta não pode ser vazia.")

    try:
        servico = get_servico_rag()
        resultado = await servico.responder_pergunta(requisicao.pergunta)
        return RespostaChat(**resultado)
    except Exception as erro:
        logger.error(f"Erro no endpoint /chat: {erro}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao processar a pergunta. Tente novamente.",
        )


@roteador.post(
    "/ingest",
    summary="Ingerir base de conhecimento",
    description=(
        "Dispara a ingestão completa dos documentos em 'data/knowledge_base/'. "
        "Use este endpoint para re-indexar após adicionar novos arquivos à base."
    ),
)
async def ingerir_base():
    """Reindexar todos os documentos da base de conhecimento no ChromaDB."""
    try:
        servico = get_servico_rag()
        total = servico.ingerir_base_conhecimento()
        return {
            "mensagem": "Ingestão concluída com sucesso.",
            "chunks_indexados": total,
        }
    except Exception as erro:
        logger.error(f"Erro na ingestão: {erro}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro na ingestão: {str(erro)}")


@roteador.get(
    "/status",
    summary="Status do sistema RAG",
    description="Retorna métricas e configurações atuais do pipeline RAG.",
)
async def status_rag():
    """Diagnóstico e métricas do sistema RAG."""
    try:
        servico = get_servico_rag()
        status = servico.obter_status()

        # Verifica disponibilidade do Ollama
        from app.rag.generator import GeradorResposta
        gerador = GeradorResposta()
        status["ollama_disponivel"] = await gerador.verificar_disponibilidade()

        return status
    except Exception as erro:
        logger.error(f"Erro ao obter status: {erro}")
        raise HTTPException(status_code=500, detail=str(erro))
