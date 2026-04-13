"""
Rotas da API para upload, processamento e salvamento de documentos fiscais.
"""

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlalchemy.orm import Session

from app.core.config import configuracoes
from app.core.database import obter_db
from app.schemas.document import DocumentoSalvar
from app.services.classification_service import ServicoClassificacao
from app.services.extraction_service import ServicoExtracao
from app.services.history_service import ServicoHistorico
from app.services.rag_service import ServicoRAG
import logging

logger = logging.getLogger(__name__)

roteador = APIRouter()

# Mapeamento de MIME types para extensões permitidas
EXTENSOES_PERMITIDAS = {".pdf", ".txt", ".html", ".htm"}


@roteador.post(
    "/upload",
    summary="Upload e processamento de documento",
    description=(
        "Recebe um arquivo (PDF, TXT ou HTML), extrai o texto e os metadados "
        "(data, valor, emitente) e sugere uma categoria tributária. "
        "Não salva automaticamente — o usuário decide após ver os resultados."
    ),
)
async def upload_documento(arquivo: UploadFile = File(...)):
    """
    Processa um arquivo enviado pelo usuário sem salvar no histórico.

    Fluxo:
    1. Valida o tipo do arquivo
    2. Salva temporariamente em /data/uploads
    3. Extrai texto e metadados
    4. Classifica o documento por categoria tributária
    5. Retorna o resultado para o usuário decidir se salva
    """
    # Validação do tipo de arquivo
    extensao = Path(arquivo.filename or "arquivo.txt").suffix.lower()
    if extensao not in EXTENSOES_PERMITIDAS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Formato '{extensao}' não suportado. "
                f"Use: {', '.join(sorted(EXTENSOES_PERMITIDAS))}"
            ),
        )

    # Salva o arquivo com nome único para evitar colisões
    nome_unico = f"{uuid.uuid4().hex}_{arquivo.filename}"
    caminho_arquivo = Path(configuracoes.CAMINHO_UPLOADS) / nome_unico
    caminho_arquivo.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(caminho_arquivo, "wb") as destino:
            shutil.copyfileobj(arquivo.file, destino)
        logger.info(f"Arquivo salvo temporariamente: {caminho_arquivo}")

        # Extração de texto e metadados
        servico_extracao = ServicoExtracao()
        dados = servico_extracao.processar_arquivo(str(caminho_arquivo))

        # Classificação tributária
        servico_classificacao = ServicoClassificacao()
        categoria = servico_classificacao.classificar(
            texto=dados["texto_extraido"],
            nome_arquivo=arquivo.filename or "",
        )

        # Substitui o nome técnico pelo nome original do arquivo
        dados["nome_arquivo"] = arquivo.filename or nome_unico
        dados["categoria"] = categoria

        return {
            "mensagem": "Documento processado com sucesso.",
            "dados": dados,
        }

    except RuntimeError as erro:
        # Limpa o arquivo em caso de falha na extração
        if caminho_arquivo.exists():
            caminho_arquivo.unlink()
        raise HTTPException(status_code=422, detail=str(erro))
    except Exception as erro:
        if caminho_arquivo.exists():
            caminho_arquivo.unlink()
        logger.error(f"Erro inesperado no upload: {erro}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao processar o documento.",
        )


@roteador.post(
    "/save",
    summary="Salvar documento no histórico",
    description=(
        "Persiste um documento previamente processado no histórico do usuário. "
        "O usuário confirma explicitamente quais documentos deseja manter. "
        "O texto do documento também é indexado no ChromaDB para consultas futuras."
    ),
)
async def salvar_documento(
    dados: DocumentoSalvar,
    db: Session = Depends(obter_db),
):
    """
    Salva o documento no SQLite e o indexa no banco vetorial.
    """
    try:
        servico_historico = ServicoHistorico()
        documento = servico_historico.salvar_documento(db, dados.model_dump())

        # Indexa no RAG para permitir consultas futuras sobre os documentos salvos
        if dados.texto_extraido and dados.texto_extraido.strip():
            try:
                servico_rag = ServicoRAG()
                chunks_indexados = servico_rag.ingerir_documento(
                    texto=dados.texto_extraido,
                    fonte=dados.nome_arquivo,
                    tipo=dados.tipo_arquivo,
                )
                logger.info(
                    f"Documento '{dados.nome_arquivo}' indexado: {chunks_indexados} chunk(s)."
                )
            except Exception as erro_rag:
                # Falha no RAG não impede o salvamento no histórico
                logger.warning(f"Falha ao indexar no RAG: {erro_rag}")

        return {
            "mensagem": "Documento salvo com sucesso.",
            "id": documento.id,
            "categoria": documento.categoria,
        }

    except Exception as erro:
        logger.error(f"Erro ao salvar documento: {erro}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao salvar documento: {str(erro)}",
        )


@roteador.get(
    "/categorias",
    summary="Listar categorias tributárias",
    description="Retorna todas as categorias disponíveis para classificação de documentos.",
)
async def listar_categorias():
    """Lista todas as categorias tributárias disponíveis no sistema."""
    servico = ServicoClassificacao()
    return {"categorias": servico.listar_categorias()}
