"""
Rotas da API para upload, processamento e salvamento de documentos fiscais.
"""

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import configuracoes
from app.core.database import obter_db
from app.schemas.document import DocumentoSalvar
from app.services.classification_service import ServicoClassificacao
from app.services.document_kind_service import (
    ajustar_categoria_irpf_por_tipo_documento,
    inferir_tipo_documento,
    inferir_tipo_documento_resumido,
    inferir_categoria_conteudo,
    legenda_validade_fiscal,
    referencia_irpf,
    resumir_status_irpf,
    texto_declara_ficticio_ou_teste_sem_validade_fiscal,
    validade_fiscal_do_tipo,
    avaliar_dedutibilidade_conteudo,
)
from app.services.extraction_service import ServicoExtracao
from app.services.history_service import ServicoHistorico
from app.services.justificativa_service import ServicoJustificativa
from app.services.rag_service import get_servico_rag
import logging

logger = logging.getLogger(__name__)

roteador = APIRouter()

# Extensões de arquivo permitidas para upload
EXTENSOES_PERMITIDAS = {".pdf", ".txt", ".html", ".htm", ".xml", ".jpg", ".jpeg", ".png"}


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

        # Classificação tributária com nível de confiança
        servico_classificacao = ServicoClassificacao()
        categoria, confianca = servico_classificacao.classificar_com_confianca(
            texto=dados["texto_extraido"],
            nome_arquivo=arquivo.filename or "",
        )

        tipo_detalhe = inferir_tipo_documento(
            dados["texto_extraido"],
            arquivo.filename or "",
        )
        tipo_exib = inferir_tipo_documento_resumido(
            dados["texto_extraido"],
            arquivo.filename or "",
        )
        categoria = ajustar_categoria_irpf_por_tipo_documento(
            tipo_exib, categoria, dados["texto_extraido"]
        )
        val_ok = validade_fiscal_do_tipo(tipo_exib)
        if texto_declara_ficticio_ou_teste_sem_validade_fiscal(
            dados["texto_extraido"]
        ):
            val_ok = False

        # Substitui o nome técnico pelo nome original do arquivo
        dados["nome_arquivo"] = arquivo.filename or nome_unico
        dados["categoria"] = categoria
        dados["confianca_classificacao"] = confianca
        dados["tipo_documento"] = tipo_exib
        dados["tipo_documento_detalhado"] = tipo_detalhe
        dados["validade_fiscal"] = val_ok
        dados["validade_fiscal_legenda"] = legenda_validade_fiscal(
            val_ok, tipo_exib, texto=dados["texto_extraido"]
        )
        dados["tipo_leiaute"] = tipo_exib
        natureza = inferir_categoria_conteudo(dados["texto_extraido"])
        dados["categoria_conteudo"] = natureza
        dados["natureza_conteudo"] = natureza
        dados["referencia_irpf"] = referencia_irpf(categoria, dados["texto_extraido"])

        # Avalia se o conteúdo é dedutível no IRPF (detecta gastos sabidamente inválidos)
        avaliacao = avaliar_dedutibilidade_conteudo(dados["texto_extraido"], categoria)
        dados["aviso_deducao"] = avaliacao.get("aviso")
        dados["nivel_aviso_deducao"] = avaliacao.get("nivel", "ok")
        st_irpf = resumir_status_irpf(
            avaliacao,
            texto=dados["texto_extraido"],
            validade_fiscal=val_ok,
            categoria_conteudo=natureza,
            nome_beneficiario=dados.get("nome_beneficiario"),
            categoria_interna=categoria,
        )
        dados["status_irpf"] = st_irpf["status_irpf"]
        dados["motivo_status_irpf"] = st_irpf.get("motivo_status_irpf", "")

        # Justificativa enriquecida: RAG + LLM fundamentada na base de conhecimento.
        # Executada após a classificação principal; falha silenciosa não bloqueia o upload.
        servico_justificativa = ServicoJustificativa()
        dados["justificativa_enriquecida"] = await servico_justificativa.gerar(
            categoria=categoria,
            tipo_documento=tipo_exib,
            emitente=dados.get("emitente_detectado") or "",
            beneficiario=dados.get("nome_beneficiario") or "",
            valor=dados.get("valor_detectado") or "",
            status_irpf=st_irpf["status_irpf"],
            categoria_conteudo=natureza,
        )

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
                servico_rag = get_servico_rag()
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
    "/referencia-irpf",
    summary="Texto de apoio IRPF por categoria",
    description=(
        "Retorna a descrição usual do quadro da declaração IRPF para a categoria escolhida. "
        "Opcionalmente usa um trecho do documento para refinar (ex.: Nota Fiscal de saúde)."
    ),
)
async def obter_referencia_irpf(
    categoria: str = Query(..., description="Categoria do DeclaraAI"),
    texto: str = Query("", max_length=12000, description="Trecho do texto extraído (opcional)"),
):
    return {"referencia_irpf": referencia_irpf(categoria, texto)}


@roteador.get(
    "/categorias",
    summary="Listar categorias tributárias",
    description="Retorna todas as categorias disponíveis para classificação de documentos.",
)
async def listar_categorias():
    """Lista todas as categorias tributárias disponíveis no sistema."""
    servico = ServicoClassificacao()
    return {"categorias": servico.listar_categorias()}
