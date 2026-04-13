"""
Rotas da API para consulta ao histórico de documentos e geração de resumo anual.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import obter_db
from app.schemas.document import DocumentoResumo
from app.services.history_service import ServicoHistorico
import logging

logger = logging.getLogger(__name__)

roteador = APIRouter()


@roteador.get(
    "/history/summary",
    summary="Resumo anual por categoria",
    description=(
        "Retorna um resumo dos documentos salvos agrupados por categoria tributária. "
        "Útil para preparar a declaração do IRPF."
    ),
)
async def resumo_anual(
    ano: Optional[int] = Query(
        None,
        description="Ano de referência para o resumo. Padrão: ano corrente.",
        ge=2000,
        le=2100,
    ),
    db: Session = Depends(obter_db),
):
    """
    Gera resumo organizando documentos por categoria tributária.

    IMPORTANTE: Esta rota deve ser definida ANTES de /history/{documento_id}
    para que o FastAPI não interprete 'summary' como um ID numérico.
    """
    try:
        servico = ServicoHistorico()
        resumo = servico.obter_resumo(db, ano)
        return resumo
    except Exception as erro:
        logger.error(f"Erro ao gerar resumo: {erro}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(erro))


@roteador.get(
    "/history",
    response_model=List[DocumentoResumo],
    summary="Listar histórico de documentos",
    description=(
        "Retorna a lista de documentos salvos com filtros opcionais por categoria, "
        "nome e período. Resultados ordenados do mais recente para o mais antigo."
    ),
)
async def listar_historico(
    categoria: Optional[str] = Query(None, description="Filtrar por categoria tributária"),
    nome: Optional[str] = Query(None, description="Filtrar por nome do arquivo (parcial)"),
    data_inicio: Optional[str] = Query(
        None, description="Data de início no formato YYYY-MM-DD"
    ),
    data_fim: Optional[str] = Query(
        None, description="Data de fim no formato YYYY-MM-DD"
    ),
    limite: int = Query(50, ge=1, le=200, description="Número máximo de resultados"),
    offset: int = Query(0, ge=0, description="Pular N resultados (paginação)"),
    db: Session = Depends(obter_db),
):
    """Lista documentos do histórico com suporte a filtros e paginação."""
    try:
        servico = ServicoHistorico()
        documentos = servico.listar_documentos(
            db=db,
            categoria=categoria,
            nome=nome,
            data_inicio=data_inicio,
            data_fim=data_fim,
            limite=limite,
            offset=offset,
        )
        return documentos
    except Exception as erro:
        logger.error(f"Erro ao listar histórico: {erro}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(erro))


@roteador.delete(
    "/history/{documento_id}",
    summary="Excluir documento do histórico",
    description="Remove permanentemente um documento do histórico pelo seu ID.",
)
async def excluir_documento(
    documento_id: int,
    db: Session = Depends(obter_db),
):
    """Remove um documento específico do histórico."""
    servico = ServicoHistorico()
    removido = servico.excluir_documento(db, documento_id)

    if not removido:
        raise HTTPException(
            status_code=404,
            detail=f"Documento ID {documento_id} não encontrado.",
        )

    return {"mensagem": f"Documento ID {documento_id} removido com sucesso."}
