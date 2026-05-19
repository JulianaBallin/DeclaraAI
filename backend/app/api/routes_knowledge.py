"""
Rotas da API para gerenciamento da base de conhecimento do pipeline RAG.

Permite listar os arquivos já indexados e adicionar novos documentos
diretamente pela interface, sem necessidade de acesso manual ao servidor.
"""

import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse

from app.core.config import configuracoes
from app.services.rag_service import get_servico_rag
import logging

logger = logging.getLogger(__name__)

roteador = APIRouter()

EXTENSOES_PERMITIDAS = {".pdf", ".txt", ".html", ".htm"}


@roteador.get(
    "/files",
    summary="Listar arquivos da base de conhecimento",
    description="Retorna a lista de arquivos presentes no diretório da base de conhecimento.",
)
async def listar_arquivos_base():
    """
    Lista todos os arquivos disponíveis na base de conhecimento.

    Retorna nome, tamanho (em KB) e tipo de cada arquivo encontrado.
    """
    diretorio = Path(configuracoes.CAMINHO_BASE_CONHECIMENTO)
    diretorio.mkdir(parents=True, exist_ok=True)

    arquivos = []
    for arquivo in sorted(diretorio.rglob("*")):
        if arquivo.is_file() and arquivo.suffix.lower() in EXTENSOES_PERMITIDAS:
            arquivos.append({
                "nome": arquivo.name,
                "tipo": arquivo.suffix.lower().lstrip("."),
                "tamanho_kb": round(arquivo.stat().st_size / 1024, 1),
            })

    try:
        servico = get_servico_rag()
        chunks_total = servico.banco_vetorial.total_chunks()
    except Exception:
        chunks_total = 0

    return {
        "total_arquivos": len(arquivos),
        "chunks_indexados": chunks_total,
        "arquivos": arquivos,
    }


@roteador.post(
    "/upload",
    summary="Adicionar arquivo à base de conhecimento",
    description=(
        "Recebe um arquivo (PDF, TXT ou HTML), salva na pasta da base de conhecimento "
        "e dispara a re-indexação completa no ChromaDB para que o conteúdo fique "
        "disponível nas consultas do chat."
    ),
)
async def adicionar_a_base(arquivo: UploadFile = File(...)):
    """
    Salva o arquivo na base de conhecimento e re-indexa o ChromaDB.

    Fluxo:
    1. Valida a extensão do arquivo
    2. Salva em data/knowledge_base/ (sobrescreve se já existir)
    3. Re-indexa toda a base de conhecimento no ChromaDB
    4. Retorna número de chunks gerados
    """
    extensao = Path(arquivo.filename or "arquivo.txt").suffix.lower()
    if extensao not in EXTENSOES_PERMITIDAS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Formato '{extensao}' não suportado. "
                f"Aceitos: {', '.join(sorted(EXTENSOES_PERMITIDAS))}"
            ),
        )

    diretorio = Path(configuracoes.CAMINHO_BASE_CONHECIMENTO)
    diretorio.mkdir(parents=True, exist_ok=True)

    # Usa o nome original — permite substituir versões antigas do mesmo arquivo
    nome_destino = arquivo.filename or f"documento{extensao}"
    caminho_destino = diretorio / nome_destino

    try:
        with open(caminho_destino, "wb") as destino:
            shutil.copyfileobj(arquivo.file, destino)
        logger.info(f"Arquivo salvo na base de conhecimento: {caminho_destino}")
    except Exception as erro:
        logger.error(f"Erro ao salvar arquivo: {erro}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Erro ao salvar o arquivo no servidor.",
        )

    # Re-indexa toda a base para incluir o novo documento
    # IMPORTANTE: limpar antes de re-indexar evita duplicação de chunks no ChromaDB
    try:
        servico = get_servico_rag()
        servico.banco_vetorial.limpar()
        total_chunks = servico.ingerir_base_conhecimento()
        logger.info(f"Re-indexação concluída após upload de '{nome_destino}': {total_chunks} chunks.")
    except Exception as erro:
        logger.error(f"Erro na re-indexação: {erro}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Arquivo salvo, mas re-indexação falhou: {str(erro)}",
        )

    return {
        "mensagem": f"Arquivo '{nome_destino}' adicionado e base re-indexada com sucesso.",
        "arquivo": nome_destino,
        "chunks_indexados": total_chunks,
    }


@roteador.get(
    "/files/{nome_arquivo}/download",
    summary="Baixar arquivo da base de conhecimento",
    description="Retorna o arquivo original da base de conhecimento para download.",
)
async def baixar_arquivo_base(nome_arquivo: str):
    """Serve o arquivo da base de conhecimento para download direto."""
    diretorio = Path(configuracoes.CAMINHO_BASE_CONHECIMENTO)
    caminho = diretorio / nome_arquivo

    if not caminho.exists() or not caminho.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Arquivo '{nome_arquivo}' não encontrado na base de conhecimento.",
        )

    try:
        caminho.resolve().relative_to(diretorio.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Caminho inválido.")

    return FileResponse(
        path=str(caminho),
        filename=nome_arquivo,
        media_type="application/octet-stream",
    )


@roteador.delete(
    "/files/{nome_arquivo}",
    summary="Remover arquivo da base de conhecimento",
    description="Remove um arquivo da base de conhecimento e re-indexa o ChromaDB.",
)
async def remover_arquivo_base(nome_arquivo: str):
    """
    Remove o arquivo informado da base de conhecimento e re-indexa.

    Args:
        nome_arquivo: Nome do arquivo a ser removido (ex: guia_imposto_renda.txt).
    """
    diretorio = Path(configuracoes.CAMINHO_BASE_CONHECIMENTO)
    caminho = diretorio / nome_arquivo

    if not caminho.exists() or not caminho.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Arquivo '{nome_arquivo}' não encontrado na base de conhecimento.",
        )

    # Impede path traversal
    try:
        caminho.resolve().relative_to(diretorio.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Caminho inválido.")

    caminho.unlink()
    logger.info(f"Arquivo removido da base de conhecimento: {nome_arquivo}")

    try:
        servico = get_servico_rag()
        # Limpa o ChromaDB e re-indexa apenas os arquivos restantes
        servico.banco_vetorial.limpar()
        total_chunks = servico.ingerir_base_conhecimento()
        logger.info(f"Re-indexação após remoção: {total_chunks} chunks.")
    except Exception as erro:
        logger.error(f"Erro na re-indexação após remoção: {erro}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Arquivo removido, mas re-indexação falhou: {str(erro)}",
        )

    return {
        "mensagem": f"Arquivo '{nome_arquivo}' removido e base re-indexada.",
        "chunks_indexados": total_chunks,
    }
