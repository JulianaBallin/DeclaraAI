"""
Utilitários para extração de texto de diferentes formatos de arquivo.
Suporta PDF, TXT, HTML, XML (NF-e SEFAZ) e imagens JPG/PNG (via OCR).
"""

import pdfplumber
from bs4 import BeautifulSoup
from pathlib import Path
import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

# Namespace padrão do layout NF-e (modelo 55) emitido pela SEFAZ
_NFE_NS = "http://www.portalfiscal.inf.br/nfe"


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


def _tag(local: str) -> str:
    """Retorna tag qualificada com namespace NF-e."""
    return f"{{{_NFE_NS}}}{local}"


def extrair_texto_xml_nfe(caminho: str) -> str:
    """
    Extrai texto estruturado de um XML de NF-e emitido pela SEFAZ.

    Lê diretamente os campos do leiaute padrão (emitente, destinatário,
    valor total, data de emissão e chave de acesso), que é mais confiável
    do que OCR para esse formato.

    Args:
        caminho: Caminho para o arquivo XML de NF-e.

    Returns:
        Texto formatado com os principais campos da nota.
    """
    try:
        tree = ET.parse(caminho)
        root = tree.getroot()

        def find(element, *paths):
            """Busca recursiva com fallback entre namespaces."""
            for path in paths:
                # Tenta com namespace
                parts = path.split("/")
                node = element
                for part in parts:
                    node = node.find(_tag(part))
                    if node is None:
                        break
                if node is not None and node.text:
                    return node.text.strip()
                # Tenta sem namespace (XML antigo/variante)
                result = element.findtext(path)
                if result:
                    return result.strip()
            return ""

        # Localiza o elemento infNFe (pode estar dentro de nfeProc ou direto)
        inf_nfe = root.find(f".//{_tag('infNFe')}")
        if inf_nfe is None:
            # Fallback: tenta sem namespace
            inf_nfe = root.find(".//infNFe")
        if inf_nfe is None:
            inf_nfe = root

        emit = inf_nfe.find(f".//{_tag('emit')}") or inf_nfe.find(".//emit") or ET.Element("emit")
        dest = inf_nfe.find(f".//{_tag('dest')}") or inf_nfe.find(".//dest") or ET.Element("dest")
        ide = inf_nfe.find(f".//{_tag('ide')}") or inf_nfe.find(".//ide") or ET.Element("ide")
        total = inf_nfe.find(f".//{_tag('ICMSTot')}") or inf_nfe.find(".//ICMSTot") or ET.Element("ICMSTot")

        def txt(el, tag):
            n = el.find(_tag(tag))
            if n is None:
                n = el.find(tag)
            return (n.text or "").strip() if n is not None else ""

        chave = ""
        inf_nfe_el = root.find(f".//{_tag('infNFe')}")
        if inf_nfe_el is not None:
            chave = inf_nfe_el.get("Id", "").replace("NFe", "")

        linhas = [
            "=== NOTA FISCAL ELETRÔNICA (XML SEFAZ) ===",
            f"Nota Fiscal Eletrônica",
            f"Número: {txt(ide, 'nNF')}  Série: {txt(ide, 'serie')}",
            f"Data de Emissão: {txt(ide, 'dhEmi') or txt(ide, 'dEmi')}",
            f"Chave de Acesso: {chave}",
            "",
            "--- EMITENTE ---",
            f"Razão Social: {txt(emit, 'xNome')}",
            f"CNPJ: {txt(emit, 'CNPJ')}",
            f"Endereço: {txt(emit.find(_tag('enderEmit') or 'enderEmit') or ET.Element('e'), 'xLgr')}",
            "",
            "--- DESTINATÁRIO ---",
            f"Nome: {txt(dest, 'xNome')}",
            f"CPF: {txt(dest, 'CPF')}",
            f"CNPJ: {txt(dest, 'CNPJ')}",
            "",
            "--- VALORES ---",
            f"Valor Total NF: R$ {txt(total, 'vNF')}",
            f"Valor Produtos: R$ {txt(total, 'vProd')}",
            f"Valor Serviços: R$ {txt(total, 'vServ') if txt(total, 'vServ') else txt(total, 'vProd')}",
            "",
            "NF-e  DANFE  chave de acesso  SEFAZ  nota fiscal eletrônica",
        ]

        # Adiciona itens (produtos/serviços)
        for det in (inf_nfe.findall(f".//{_tag('det')}") or inf_nfe.findall(".//det") or [])[:10]:
            prod = det.find(_tag("prod")) or det.find("prod")
            if prod is not None:
                linhas.append(
                    f"Item: {txt(prod, 'xProd')} | Qtd: {txt(prod, 'qCom')} | Valor: R$ {txt(prod, 'vProd')}"
                )

        return "\n".join(l for l in linhas if l or l == "")

    except ET.ParseError as erro:
        logger.error(f"XML inválido '{caminho}': {erro}")
        raise RuntimeError(f"Arquivo XML inválido ou corrompido: {erro}") from erro
    except Exception as erro:
        logger.error(f"Falha ao processar XML NF-e '{caminho}': {erro}")
        raise RuntimeError(f"Erro ao processar XML: {erro}") from erro


def extrair_texto_imagem(caminho: str) -> str:
    """
    Tenta extrair texto de imagem JPG/PNG via OCR (pytesseract).

    Se o pytesseract não estiver instalado ou o tesseract não estiver disponível,
    informa ao usuário que o arquivo não pôde ser processado automaticamente
    e orienta a converter para PDF.

    Args:
        caminho: Caminho para o arquivo de imagem.

    Returns:
        Texto extraído via OCR.

    Raises:
        RuntimeError: Se OCR não estiver disponível ou falhar.
    """
    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        raise RuntimeError(
            "OCR não disponível. O arquivo de imagem não pôde ser processado automaticamente. "
            "Converta o documento para PDF e tente novamente."
        )

    try:
        imagem = Image.open(caminho)
        # Configura para português brasileiro e inglês
        texto = pytesseract.image_to_string(imagem, lang="por+eng")
        if not texto.strip():
            raise RuntimeError(
                "O OCR não conseguiu extrair texto desta imagem. "
                "A qualidade pode estar baixa — converta para PDF com texto ou tente uma foto com melhor iluminação."
            )
        return texto.strip()
    except RuntimeError:
        raise
    except Exception as erro:
        logger.error(f"Falha no OCR de '{caminho}': {erro}")
        raise RuntimeError(
            f"Erro ao processar imagem com OCR: {erro}. "
            "Converta o documento para PDF e tente novamente."
        ) from erro


def extrair_texto(caminho: str) -> tuple[str, str]:
    """
    Despacha a extração de texto para o parser correto com base na extensão.

    Args:
        caminho: Caminho para o arquivo a ser processado.

    Returns:
        Tupla (texto_extraido, tipo_arquivo).

    Raises:
        ValueError: Se o tipo de arquivo não for suportado.
    """
    extensao = Path(caminho).suffix.lower()

    parsers = {
        ".pdf": (extrair_texto_pdf, "pdf"),
        ".txt": (extrair_texto_txt, "txt"),
        ".html": (extrair_texto_html, "html"),
        ".htm": (extrair_texto_html, "html"),
        ".xml": (extrair_texto_xml_nfe, "xml"),
        ".jpg": (extrair_texto_imagem, "imagem"),
        ".jpeg": (extrair_texto_imagem, "imagem"),
        ".png": (extrair_texto_imagem, "imagem"),
    }

    if extensao not in parsers:
        raise ValueError(
            f"Formato '{extensao}' não suportado. Use: {', '.join(parsers.keys())}"
        )

    funcao_parser, tipo = parsers[extensao]
    texto = funcao_parser(caminho)
    return texto, tipo
