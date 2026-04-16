"""
Serviço de gerenciamento do histórico de documentos.

Persiste, recupera e organiza os documentos fiscais salvos pelo usuário
no banco de dados SQLite via SQLAlchemy.
"""

import re
from sqlalchemy.orm import Session
from sqlalchemy import extract
from typing import Optional, List
from datetime import datetime
from app.models.document import Documento
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# M7 — Limites de dedução anuais por categoria (valores vigentes IRPF 2024)
# ---------------------------------------------------------------------------
LIMITES_DEDUCAO: dict[str, float | None] = {
    "Comprovante Educacional": 3561.50,   # por pessoa (titular + cada dependente)
    "Recibo Médico": None,                 # sem limite
    "Nota Fiscal": None,                   # depende do conteúdo
    "Previdência Privada": None,           # 12% da renda bruta — calculado dinamicamente
    "Doações": None,                       # % do imposto — variável
    "Pensão Alimentícia": None,            # sem limite (dedução integral)
    "Aluguel": None,
    "Informe de Rendimentos": None,
}

# Alíquota estimada para cálculo de economia (alíquota marginal mediana)
ALIQUOTA_ESTIMATIVA = 0.275  # 27,5%


def _parse_valor(valor_str: str | None) -> float:
    """Converte string 'R$ 1.234,56' para float. Retorna 0.0 se inválido."""
    if not valor_str:
        return 0.0
    apenas_num = re.sub(r"[R$\s]", "", valor_str)
    apenas_num = apenas_num.replace(".", "").replace(",", ".")
    try:
        return float(apenas_num)
    except ValueError:
        return 0.0


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
            tipo_documento=dados.get("tipo_documento"),
            referencia_irpf=dados.get("referencia_irpf"),
            validade_fiscal=dados.get("validade_fiscal"),
            confianca_classificacao=dados.get("confianca_classificacao"),
            texto_extraido=dados.get("texto_extraido", ""),
            data_detectada=dados.get("data_detectada"),
            valor_detectado=dados.get("valor_detectado"),
            emitente_detectado=dados.get("emitente_detectado"),
            chave_acesso=dados.get("chave_acesso"),
            cnpj_emitente=dados.get("cnpj_emitente"),
            nome_beneficiario=dados.get("nome_beneficiario"),
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

        # M7 — Calcula totais, verifica limites e estima economia
        total_deducoes = 0.0
        for categoria, dados_cat in resumo["categorias"].items():
            total_num = sum(_parse_valor(v) for v in dados_cat["valores"])
            limite = LIMITES_DEDUCAO.get(categoria)

            dados_cat["total_numerico"] = round(total_num, 2)
            dados_cat["limite_deducao"] = limite
            dados_cat["excedente"] = None
            dados_cat["alerta_limite"] = None

            if limite is not None and total_num > 0:
                if total_num > limite:
                    excedente = round(total_num - limite, 2)
                    dados_cat["excedente"] = excedente
                    dados_cat["alerta_limite"] = (
                        f"Limite anual de R$ {limite:,.2f} atingido. "
                        f"Excedente de R$ {excedente:,.2f} não será deduzido."
                    )
                elif total_num > limite * 0.85:
                    restante = round(limite - total_num, 2)
                    dados_cat["alerta_limite"] = (
                        f"Atenção: você usou {total_num / limite * 100:.0f}% do limite anual "
                        f"(R$ {limite:,.2f}). Restam R$ {restante:,.2f}."
                    )

            # Soma categorias dedutíveis para estimativa
            if categoria in ("Recibo Médico", "Comprovante Educacional", "Pensão Alimentícia",
                             "Previdência Privada", "Doações"):
                dedutivel = min(total_num, limite) if limite else total_num
                total_deducoes += dedutivel

        resumo["total_deducoes_estimado"] = round(total_deducoes, 2)
        resumo["economia_estimada"] = round(total_deducoes * ALIQUOTA_ESTIMATIVA, 2)
        resumo["aviso_estimativa"] = (
            "Estimativa calculada com alíquota de 27,5%. "
            "O valor real depende da base de cálculo completa da sua declaração."
        )

        logger.info(
            f"Resumo gerado para {ano_referencia}: "
            f"{len(documentos)} documento(s) em {len(resumo['categorias'])} categoria(s)."
        )
        return resumo

    def buscar_por_id(self, db: Session, documento_id: int) -> Optional[Documento]:
        """
        Busca um documento específico pelo ID.

        Args:
            db: Sessão do banco de dados.
            documento_id: ID do documento.

        Returns:
            Instância do Documento ou None se não encontrado.
        """
        return db.query(Documento).filter(Documento.id == documento_id).first()

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
