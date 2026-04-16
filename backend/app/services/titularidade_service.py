"""
Verificação de titularidade do documento vs. declarante.

Compara o nome do beneficiário extraído do documento com o nome do declarante
informado pelo usuário. Foca nos sobrenomes, pois dependentes geralmente
compartilham o sobrenome familiar.
"""

import re
import unicodedata
import logging

logger = logging.getLogger(__name__)


def _normalizar(texto: str) -> str:
    """Remove acentos e converte para minúsculas para comparação."""
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sem_acento.lower().strip()


def _extrair_sobrenomes(nome_completo: str) -> list[str]:
    """
    Retorna lista de sobrenomes (todas as palavras exceto o primeiro nome).
    Ignora partículas comuns (de, da, dos, das, do, e).
    """
    particulas = {"de", "da", "dos", "das", "do", "e", "di", "du"}
    partes = _normalizar(nome_completo).split()
    # Descarta o primeiro nome e as partículas
    sobrenomes = [p for p in partes[1:] if p not in particulas and len(p) > 1]
    return sobrenomes


def _similaridade_sobrenomes(sobrenomes_a: list[str], sobrenomes_b: list[str]) -> float:
    """
    Calcula fração de sobrenomes de A que aparecem em B.
    Retorna 0.0 a 1.0.
    """
    if not sobrenomes_a or not sobrenomes_b:
        return 0.0
    set_b = set(sobrenomes_b)
    coincidencias = sum(1 for s in sobrenomes_a if s in set_b)
    return coincidencias / len(sobrenomes_a)


def verificar_titularidade(
    nome_declarante: str,
    nome_beneficiario: str | None,
) -> dict:
    """
    Compara o nome do beneficiário do documento com o nome do declarante.

    Returns:
        dict com:
            status: "titular" | "provavel_dependente" | "terceiro" | "nao_verificado"
            mensagem: texto explicativo para o usuário
            requer_confirmacao: bool
    """
    if not nome_beneficiario or not nome_declarante:
        return {
            "status": "nao_verificado",
            "mensagem": (
                "Não foi possível identificar o beneficiário do documento. "
                "Verifique se o documento está em nome do titular ou de um dependente."
            ),
            "requer_confirmacao": False,
        }

    norm_declarante = _normalizar(nome_declarante)
    norm_beneficiario = _normalizar(nome_beneficiario)

    # Correspondência exata (mesma pessoa)
    if norm_declarante == norm_beneficiario:
        return {
            "status": "titular",
            "mensagem": f"Documento em nome do declarante ({nome_declarante}).",
            "requer_confirmacao": False,
        }

    # Verifica se o primeiro nome é igual (mesma pessoa com variação de grafia)
    primeiro_declarante = norm_declarante.split()[0] if norm_declarante else ""
    primeiro_beneficiario = norm_beneficiario.split()[0] if norm_beneficiario else ""

    sobrenomes_declarante = _extrair_sobrenomes(nome_declarante)
    sobrenomes_beneficiario = _extrair_sobrenomes(nome_beneficiario)
    similaridade = _similaridade_sobrenomes(sobrenomes_beneficiario, sobrenomes_declarante)

    if primeiro_declarante == primeiro_beneficiario and similaridade >= 0.5:
        return {
            "status": "titular",
            "mensagem": f"Documento em nome do declarante ({nome_declarante}).",
            "requer_confirmacao": False,
        }

    # Sobrenomes em comum mas prenome diferente → provável dependente
    if similaridade >= 0.5:
        return {
            "status": "provavel_dependente",
            "mensagem": (
                f"O documento está em nome de **{nome_beneficiario}**, que compartilha "
                f"sobrenome com o declarante ({nome_declarante}). "
                "Esta pessoa é seu dependente (filho(a), cônjuge, pai/mãe)?"
            ),
            "requer_confirmacao": True,
        }

    # Sobrenomes totalmente diferentes → possível terceiro
    return {
        "status": "terceiro",
        "mensagem": (
            f"O documento está em nome de **{nome_beneficiario}**, que não parece ser "
            f"o declarante ({nome_declarante}) nem compartilha o sobrenome familiar. "
            "Despesas de terceiros só são dedutíveis se a pessoa for dependente incluída na declaração. "
            "Confirme se esta pessoa é seu dependente antes de salvar."
        ),
        "requer_confirmacao": True,
    }
