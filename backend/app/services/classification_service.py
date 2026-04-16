"""
Serviço de classificação de documentos em categorias tributárias.

Utiliza análise de palavras-chave com pontuação ponderada para identificar
a categoria mais provável de um documento fiscal.
"""

import re
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapa de categorias tributárias e palavras-chave associadas
# ---------------------------------------------------------------------------
# Cada entrada possui:
#   - palavras: termos-chave que indicam a categoria
#   - peso: multiplicador de relevância (categorias mais específicas têm peso maior)
# ---------------------------------------------------------------------------

CATEGORIAS_TRIBUTARIAS: dict[str, dict] = {
    "Recibo Médico": {
        "palavras": [
            "médico", "médica", "consulta", "clínica", "hospital", "saúde",
            "dentista", "odontológico", "odontologia", "procedimento odontológico",
            "tratamento odontológico", "infinity odontologia",
            "psicólogo", "psiquiatra", "fisioterapia",
            "fisioterapeuta", "fonoaudiólogo", "terapia", "exame", "laboratório",
            "farmácia", "medicamento", "remédio", "plano de saúde", "cirurgia",
            "internação", "prontuário", "receita médica", "CRM", "CRO", "CRP",
            "CRF", "CREFITO", "nutricionista", "psicopedagogo",
        ],
        "peso": 2.0,
    },
    "Comprovante Educacional": {
        "palavras": [
            "escola", "colégio", "universidade", "faculdade", "mensalidade",
            "matrícula", "educação", "ensino", "curso", "aula", "professor",
            "aluno", "semestre", "graduação", "pós-graduação", "pós graduação",
            "MEC", "vestibular", "ENEM", "bolsa", "pedagógico", "creche",
            "pré-escola", "técnico", "tecnológico", "especialização",
        ],
        "peso": 1.5,
    },
    "Informe de Rendimentos": {
        "palavras": [
            "informe de rendimentos", "rendimentos", "salário", "remuneração",
            "empregador", "INSS", "IRRF", "imposto retido", "imposto de renda retido",
            "décimo terceiro", "13º salário", "férias", "rescisão", "CLT",
            "holerite", "contracheque", "rendimento tributável", "rendimento isento",
            "comprovante de rendimentos", "DIRF", "declaração anual",
        ],
        "peso": 2.0,
    },
    # Genérica: perde para categorias específicas quando há sinais claros (ex.: saúde/odontologia).
    "Nota Fiscal": {
        "palavras": [
            "nota fiscal", "NF-e", "NF-Se", "NFe", "DANFE", "chave de acesso",
            "ICMS", "IPI", "ISS", "produto", "mercadoria", "compra", "venda",
            "série", "número NF", "emissão fiscal", "SEFAZ",
        ],
        "peso": 1.0,
    },
    "Previdência Privada": {
        "palavras": [
            "previdência privada", "PGBL", "VGBL", "fundo de pensão",
            "contribuição previdenciária", "plano de previdência",
            "previdência complementar", "pecúlio",
        ],
        "peso": 2.0,
    },
    "Doações": {
        "palavras": [
            "doação", "donatário", "recibo de doação", "ONG", "entidade",
            "filantropia", "beneficente", "sem fins lucrativos", "associação",
            "fundação", "doador",
        ],
        "peso": 1.5,
    },
    "Pensão Alimentícia": {
        "palavras": [
            "pensão alimentícia", "alimentos", "pensionista", "decisão judicial",
            "acordo judicial", "alimentando", "pensão", "guarda",
        ],
        "peso": 2.0,
    },
    "Aluguel": {
        "palavras": [
            "aluguel", "locação", "locatário", "locador", "imóvel", "contrato",
            "recibo de aluguel", "arrendamento", "IPTU", "condomínio",
        ],
        "peso": 1.5,
    },
}

CATEGORIA_PADRAO = "Documento Não Classificado"


class ServicoClassificacao:
    """
    Classifica documentos fiscais em categorias tributárias usando pontuação ponderada.

    A pontuação de cada categoria é calculada contando as ocorrências de suas
    palavras-chave no texto do documento, multiplicadas pelo peso da categoria.
    A categoria com maior pontuação é retornada.
    """

    def classificar(self, texto: str, nome_arquivo: str = "") -> str:
        """
        Determina a categoria tributária mais provável para o documento.

        Args:
            texto: Texto extraído do documento.
            nome_arquivo: Nome do arquivo (contexto adicional).

        Returns:
            Nome da categoria tributária identificada ou 'Documento Não Classificado'.
        """
        if not texto and not nome_arquivo:
            return CATEGORIA_PADRAO

        # Combina texto e nome do arquivo para análise
        texto_analise = f"{texto} {nome_arquivo}".lower()
        pontuacoes: dict[str, float] = {}

        for categoria, config in CATEGORIAS_TRIBUTARIAS.items():
            pontuacao = sum(
                config["peso"]
                for palavra in config["palavras"]
                if re.search(rf"\b{re.escape(palavra.lower())}\b", texto_analise)
            )
            if pontuacao > 0:
                pontuacoes[categoria] = pontuacao

        if not pontuacoes:
            logger.info(f"Documento não classificado: nenhuma palavra-chave encontrada.")
            return CATEGORIA_PADRAO

        categoria_vencedora = max(pontuacoes, key=pontuacoes.get)
        score_max = pontuacoes[categoria_vencedora]
        logger.info(
            f"Classificado como '{categoria_vencedora}' "
            f"(score: {score_max:.1f} | candidatos: {len(pontuacoes)})"
        )
        return categoria_vencedora

    def listar_categorias(self) -> list[str]:
        """Retorna todas as categorias tributárias disponíveis incluindo a padrão."""
        return list(CATEGORIAS_TRIBUTARIAS.keys()) + [CATEGORIA_PADRAO]
