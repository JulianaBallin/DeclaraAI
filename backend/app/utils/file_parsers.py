"""
Utilitários para extração de texto de diferentes formatos de arquivo.
Suporta PDF, TXT e HTML com tratamento de encoding e erros.
"""

import pdfplumber
from bs4 import BeautifulSoup
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def extrair_texto_pdf(caminho: str) -> str:
    """
    Extrai texto de arquivo PDF página por página usando pdfplumber.

    Args:
        caminho: Caminho absoluto ou relativo para o arquivo PDF.

    Returns:
        Texto extraído concatenado de todas as páginas.
    """
    texto_total = ""
    try:
        with pdfplumber.open(caminho) as pdf:
            for numero_pagina, pagina in enumerate(pdf.pages, start=1):
                texto_pagina = pagina.extract_text()
                if texto_pagina:
                    texto_total += texto_pagina + "\n"
                    logger.debug(f"Página {numero_pagina} extraída.")
    except Exception as erro:
        logger.error(f"Falha ao extrair PDF '{caminho}': {erro}")
        raise RuntimeError(f"Erro ao processar PDF: {erro}") from erro

    return texto_total.strip()


def extrair_texto_txt(caminho: str) -> str:
    """
    Lê e retorna o conteúdo de um arquivo de texto simples.

    Args:
        caminho: Caminho para o arquivo TXT.

    Returns:
        Conteúdo do arquivo como string.
    """
    try:
        with open(caminho, "r", encoding="utf-8", errors="ignore") as arquivo:
            return arquivo.read().strip()
    except Exception as erro:
        logger.error(f"Falha ao ler TXT '{caminho}': {erro}")
        raise RuntimeError(f"Erro ao ler TXT: {erro}") from erro


def extrair_texto_html(caminho: str) -> str:
    """
    Extrai texto legível de um arquivo HTML removendo tags, scripts e estilos.

    Args:
        caminho: Caminho para o arquivo HTML.

    Returns:
        Texto limpo extraído do HTML.
    """
    try:
        with open(caminho, "r", encoding="utf-8", errors="ignore") as arquivo:
            conteudo = arquivo.read()

        soup = BeautifulSoup(conteudo, "html.parser")

        # Remove elementos não textuais
        for elemento in soup(["script", "style", "meta", "link", "noscript"]):
            elemento.decompose()

        # Extrai texto com separadores de linha
        texto = soup.get_text(separator="\n")

        # Remove linhas em branco consecutivas
        linhas = [linha.strip() for linha in texto.splitlines()]
        linhas_validas = [linha for linha in linhas if linha]
        return "\n".join(linhas_validas)

    except Exception as erro:
        logger.error(f"Falha ao processar HTML '{caminho}': {erro}")
        raise RuntimeError(f"Erro ao processar HTML: {erro}") from erro


def extrair_texto(caminho: str) -> tuple[str, str]:
    """
    Despacha a extração de texto para o parser correto com base na extensão.

    Args:
        caminho: Caminho para o arquivo a ser processado.

    Returns:
        Tupla (texto_extraido, tipo_arquivo) onde tipo_arquivo é 'pdf', 'txt' ou 'html'.

    Raises:
        ValueError: Se o tipo de arquivo não for suportado.
    """
    extensao = Path(caminho).suffix.lower()

    parsers = {
        ".pdf": (extrair_texto_pdf, "pdf"),
        ".txt": (extrair_texto_txt, "txt"),
        ".html": (extrair_texto_html, "html"),
        ".htm": (extrair_texto_html, "html"),
    }

    if extensao not in parsers:
        raise ValueError(
            f"Formato '{extensao}' não suportado. Use: {', '.join(parsers.keys())}"
        )

    funcao_parser, tipo = parsers[extensao]
    texto = funcao_parser(caminho)
    return texto, tipo
