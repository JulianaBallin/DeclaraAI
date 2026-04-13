"""
Serviço de gerenciamento do histórico de documentos.

Persiste, recupera e organiza os documentos fiscais salvos pelo usuário
no banco de dados SQLite via SQLAlchemy.
"""

from sqlalchemy.orm import Session
from sqlalchemy import extract
from typing import Optional, List
from datetime import datetime
from app.models.document import Documento
import logging

logger = logging.getLogger(__name__)


class ServicoHistorico:
    """
    Gerencia o ciclo de vida dos documentos no histórico do usuário.

    Oferece operações de criação, listagem com filtros, resumo anual
    e exclusão de documentos persistidos no SQLite.
    """

    def salvar_documento(self, db: Session, dados: dict) -> Documento:
        """
        Persiste um documento processado no banco de dados.

        Args:
            db: Sessão ativa do SQLAlchemy.
            dados: Dicionário com todos os campos do documento.

        Returns:
            Instância do documento persistido com ID gerado.
        """
        documento = Documento(
            nome_arquivo=dados.get("nome_arquivo", "arquivo_sem_nome"),
            tipo_arquivo=dados.get("tipo_arquivo", "desconhecido"),
            categoria=dados.get("categoria", "Documento Não Classificado"),
            texto_extraido=dados.get("texto_extraido", ""),
            data_detectada=dados.get("data_detectada"),
            valor_detectado=dados.get("valor_detectado"),
            emitente_detectado=dados.get("emitente_detectado"),
            caminho_arquivo=dados.get("caminho_arquivo", ""),
        )

        db.add(documento)
        db.commit()
        db.refresh(documento)

        logger.info(
            f"Documento salvo: '{documento.nome_arquivo}' "
            f"(ID: {documento.id} | Categoria: {documento.categoria})"
        )
        return documento

    def listar_documentos(
        self,
        db: Session,
        categoria: Optional[str] = None,
        nome: Optional[str] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        limite: int = 100,
        offset: int = 0,
    ) -> List[Documento]:
        """
        Lista documentos do histórico com filtros opcionais.

        Args:
            db: Sessão do banco de dados.
            categoria: Filtrar por categoria tributária exata.
            nome: Filtrar por nome do arquivo (busca parcial, case-insensitive).
            data_inicio: Filtrar documentos criados a partir desta data (ISO 8601).
            data_fim: Filtrar documentos criados até esta data (ISO 8601).
            limite: Número máximo de resultados.
            offset: Quantidade de resultados a pular (paginação).

        Returns:
            Lista de documentos ordenados do mais recente ao mais antigo.
        """
        query = db.query(Documento)

        if categoria:
            query = query.filter(Documento.categoria == categoria)

        if nome:
            query = query.filter(Documento.nome_arquivo.ilike(f"%{nome}%"))

        if data_inicio:
            try:
                dt_inicio = datetime.fromisoformat(data_inicio)
                query = query.filter(Documento.criado_em >= dt_inicio)
            except ValueError:
                logger.warning(f"Formato de data_inicio inválido: '{data_inicio}'")

        if data_fim:
            try:
                dt_fim = datetime.fromisoformat(data_fim)
                query = query.filter(Documento.criado_em <= dt_fim)
            except ValueError:
                logger.warning(f"Formato de data_fim inválido: '{data_fim}'")

        return (
            query
            .order_by(Documento.criado_em.desc())
            .offset(offset)
            .limit(limite)
            .all()
        )

    def obter_resumo(self, db: Session, ano: Optional[int] = None) -> dict:
        """
        Gera resumo dos documentos agrupados por categoria para um ano específico.

        Útil para preparar a declaração do IR, organizando os comprovantes
        por tipo (saúde, educação, rendimentos, etc.).

        Args:
            db: Sessão do banco de dados.
            ano: Ano de referência (padrão: ano corrente).

        Returns:
            Dicionário com total de documentos e detalhamento por categoria.
        """
        ano_referencia = ano or datetime.now().year

        documentos = (
            db.query(Documento)
            .filter(extract("year", Documento.criado_em) == ano_referencia)
            .order_by(Documento.categoria, Documento.criado_em.desc())
            .all()
        )

        resumo: dict = {
            "ano": ano_referencia,
            "total_documentos": len(documentos),
            "categorias": {},
        }

        for doc in documentos:
            categoria = doc.categoria or "Documento Não Classificado"

            if categoria not in resumo["categorias"]:
                resumo["categorias"][categoria] = {
                    "quantidade": 0,
                    "documentos": [],
                    "valores": [],
                }

            resumo["categorias"][categoria]["quantidade"] += 1
            resumo["categorias"][categoria]["documentos"].append({
                "id": doc.id,
                "nome": doc.nome_arquivo,
                "data_detectada": doc.data_detectada,
                "valor_detectado": doc.valor_detectado,
                "emitente": doc.emitente_detectado,
                "criado_em": doc.criado_em.isoformat() if doc.criado_em else None,
            })

            if doc.valor_detectado:
                resumo["categorias"][categoria]["valores"].append(doc.valor_detectado)

        logger.info(
            f"Resumo gerado para {ano_referencia}: "
            f"{len(documentos)} documento(s) em {len(resumo['categorias'])} categoria(s)."
        )
        return resumo

    def excluir_documento(self, db: Session, documento_id: int) -> bool:
        """
        Remove um documento específico do histórico.

        Args:
            db: Sessão do banco de dados.
            documento_id: ID do documento a ser removido.

        Returns:
            True se removido com sucesso, False se não encontrado.
        """
        documento = db.query(Documento).filter(Documento.id == documento_id).first()
        if not documento:
            return False

        db.delete(documento)
        db.commit()
        logger.info(f"Documento ID {documento_id} removido do histórico.")
        return True
