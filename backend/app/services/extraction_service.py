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
