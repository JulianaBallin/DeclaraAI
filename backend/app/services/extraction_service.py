"""
Serviço de extração de texto e metadados de documentos fiscais.

Usa heurísticas baseadas em expressões regulares para identificar
informações relevantes como datas, valores monetários e emitentes.
"""

import re
from pathlib import Path
from typing import Optional
from app.utils.file_parsers import extrair_texto
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Padrões de expressões regulares para extração de metadados
# ---------------------------------------------------------------------------

PADROES_DATA = [
    r"\b(\d{2}/\d{2}/\d{4})\b",                              # 31/12/2024
    r"\b(\d{2}-\d{2}-\d{4})\b",                              # 31-12-2024
    r"\b(\d{4}-\d{2}-\d{2})\b",                              # 2024-12-31
    r"\b(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})\b",               # 1 de janeiro de 2024
]

PADROES_VALOR = [
    r"(?i)valor\s+total\s*R?\$?\s*[\n\r\s]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)",
    r"(?i)valor\s+dos\s+servi[çc]os\s*R?\$?\s*[\n\r\s]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)",
    r"(?i)valor\s+recebido\s*R?\$?\s*[\n\r\s]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)",
    # Genérico por último; linhas R$ 0,00 são descartadas em _extrair_valor
    r"R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)",
    r"(?i)(?:total|subtotal)[:\s]+R?\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)",
    r"(?i)(?:mensalidade|honorários)[:\s]+R?\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)",
]

PADROES_EMITENTE = [
    r"([A-ZÀ-Ú][A-Za-zÀ-ú\s]{3,}(?:Ltda|LTDA|S\.A\.|SA|ME|EPP|EIRELI|LTDA\.))",
    r"(?i)(?:emitente|empresa|prestador|fornecedor|clínica|hospital|escola|"
    r"universidade|colégio|laboratório|farmácia|odontologia)[:\s]+([A-ZÀ-Ú][A-Za-zÀ-ú\s]+)",
    r"(?i)(?:CNPJ|CPF)[:\s]*[\d.\/\-]+\s*[-–]?\s*([A-ZÀ-Ú][A-Za-zÀ-ú\s]+)",
]

# Chave de acesso NF-e: 44 dígitos, possivelmente com espaços/pontos entre grupos
PADRAO_CHAVE_ACESSO = re.compile(r"(?:chave[:\s]*(?:de\s+acesso)?[:\s]*)?((?:\d[\s.]?){44})", re.IGNORECASE)

PADROES_CNPJ = [
    r"\b(\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2})\b",  # CNPJ xx.xxx.xxx/xxxx-xx
]

PADROES_CPF_EMITENTE = [
    r"(?i)(?:CPF\s*do\s*emitente|CPF\s*emitente|emitente\s*CPF)[:\s]*([\d]{3}[.\s]?[\d]{3}[.\s]?[\d]{3}[-\s]?[\d]{2})",
]

PADROES_BENEFICIARIO = [
    r"(?i)(?:paciente|aluno|cliente|tomador|destinatário|destinatario|beneficiário|beneficiario)"
    r"[:\s]+([A-ZÀ-Ú][A-Za-zÀ-ú\s]{4,})",
    r"(?i)(?:nome\s+do\s+(?:paciente|aluno|cliente|tomador|destinatário))[:\s]+"
    r"([A-ZÀ-Ú][A-Za-zÀ-ú\s]{4,})",
]


class ServicoExtracao:
    """
    Extrai texto e metadados estruturados de documentos enviados pelo usuário.

    As heurísticas são otimizadas para documentos fiscais brasileiros comuns:
    recibos médicos, notas fiscais, informes de rendimento e comprovantes educacionais.
    """

    def processar_arquivo(self, caminho: str) -> dict:
        """
        Lê e processa um arquivo, retornando texto e metadados detectados.

        Args:
            caminho: Caminho para o arquivo (PDF, TXT ou HTML).

        Returns:
            Dicionário com texto extraído, tipo do arquivo e metadados.

        Raises:
            RuntimeError: Se ocorrer erro durante extração ou tipo não suportado.
        """
        path = Path(caminho)

        try:
            texto, tipo_arquivo = extrair_texto(caminho)
        except Exception as erro:
            logger.error(f"Falha ao extrair texto de '{path.name}': {erro}")
            raise RuntimeError(str(erro)) from erro

        if not texto.strip():
            logger.warning(f"Arquivo '{path.name}' extraído com texto vazio.")

        return {
            "nome_arquivo": path.name,
            "tipo_arquivo": tipo_arquivo,
            "texto_extraido": texto,
            "data_detectada": self._extrair_data(texto),
            "valor_detectado": self._extrair_valor(texto),
            "emitente_detectado": self._extrair_emitente(texto),
            "chave_acesso": self._extrair_chave_acesso(texto),
            "cnpj_emitente": self._extrair_cnpj_emitente(texto),
            "nome_beneficiario": self._extrair_nome_beneficiario(texto),
            "caminho_arquivo": caminho,
        }

    # -----------------------------------------------------------------------
    # Métodos privados de extração por heurísticas
    # -----------------------------------------------------------------------

    def _extrair_data(self, texto: str) -> Optional[str]:
        """Retorna a primeira data encontrada no texto."""
        for padrao in PADROES_DATA:
            correspondencia = re.search(padrao, texto, re.IGNORECASE)
            if correspondencia:
                return correspondencia.group(1)
        return None

    def _extrair_valor(self, texto: str) -> Optional[str]:
        """Prioriza totais rotulados; ignora valores 0,00 (subtotais vazios em NFC-e)."""
        for padrao in PADROES_VALOR:
            for correspondencia in re.finditer(padrao, texto, re.IGNORECASE | re.MULTILINE):
                valor_bruto = correspondencia.group(1).strip()
                if valor_bruto in ("0,00", "0.00", "0"):
                    continue
                return f"R$ {valor_bruto}"
        return None

    def _extrair_emitente(self, texto: str) -> Optional[str]:
        """Retorna o nome do emitente identificado no texto."""
        for padrao in PADROES_EMITENTE:
            correspondencia = re.search(padrao, texto)
            if correspondencia:
                nome = correspondencia.group(1).strip()
                if len(nome) >= 4 and not nome.isspace():
                    return nome[:120]
        return None

    def _extrair_chave_acesso(self, texto: str) -> Optional[str]:
        """Extrai a chave de acesso de 44 dígitos de NF-e/NFC-e/NFSe."""
        # Remove espaços/pontos e procura sequência de 44 dígitos
        apenas_digitos = re.sub(r"[\s.]", "", texto)
        correspondencia = re.search(r"\d{44}", apenas_digitos)
        if correspondencia:
            return correspondencia.group(0)
        # Tenta com o padrão contextual (próximo a "chave")
        correspondencia = PADRAO_CHAVE_ACESSO.search(texto)
        if correspondencia:
            chave = re.sub(r"\D", "", correspondencia.group(1))
            if len(chave) == 44:
                return chave
        return None

    def _extrair_cnpj_emitente(self, texto: str) -> Optional[str]:
        """Extrai CNPJ ou CPF do emitente."""
        for padrao in PADROES_CNPJ:
            correspondencia = re.search(padrao, texto)
            if correspondencia:
                return re.sub(r"[\s]", "", correspondencia.group(1))
        for padrao in PADROES_CPF_EMITENTE:
            correspondencia = re.search(padrao, texto, re.IGNORECASE)
            if correspondencia:
                return re.sub(r"[\s]", "", correspondencia.group(1))
        return None

    def _extrair_nome_beneficiario(self, texto: str) -> Optional[str]:
        """Extrai o nome do beneficiário/destinatário do documento."""
        for padrao in PADROES_BENEFICIARIO:
            correspondencia = re.search(padrao, texto)
            if correspondencia:
                nome = correspondencia.group(1).strip().rstrip(".,;:")
                if len(nome) >= 4:
                    return nome[:120]
        return None
