"""
Carregador de documentos da base de conhecimento.
Responsável por ler todos os arquivos suportados de um diretório
e prepará-los para ingestão no pipeline RAG.
"""

from pathlib import Path
from typing import List
from app.utils.file_parsers import extrair_texto
from app.core.config import configuracoes
import logging

logger = logging.getLogger(__name__)

EXTENSOES_SUPORTADAS = {".pdf", ".txt", ".html", ".htm"}


class CarregadorDocumentos:
    """
    Carrega documentos da base de conhecimento para o pipeline RAG.

    Varre recursivamente o diretório configurado e extrai o texto de todos
    os arquivos nos formatos suportados (PDF, TXT, HTML).
    """

    def __init__(self, diretorio: str | None = None):
        """
        Args:
            diretorio: Caminho opcional para substituir o diretório padrão.
        """
        self.diretorio = Path(diretorio or configuracoes.CAMINHO_BASE_CONHECIMENTO)

    def carregar_todos(self) -> List[dict]:
        """
        Carrega todos os documentos do diretório da base de conhecimento.

        Returns:
            Lista de dicionários com campos 'texto', 'fonte', 'caminho' e 'tipo'.
        """
        documentos: List[dict] = []

        if not self.diretorio.exists():
            logger.warning(
                f"Diretório '{self.diretorio}' não encontrado. Criando..."
            )
            self.diretorio.mkdir(parents=True, exist_ok=True)
            return documentos

        for arquivo in self.diretorio.rglob("*"):
            if arquivo.is_file() and arquivo.suffix.lower() in EXTENSOES_SUPORTADAS:
                try:
                    texto, tipo = extrair_texto(str(arquivo))
                    if texto.strip():
                        documentos.append({
                            "texto": texto,
                            "fonte": arquivo.name,
                            "caminho": str(arquivo),
                            "tipo": tipo,
                        })
                        logger.info(f"Carregado: {arquivo.name} ({tipo.upper()})")
                    else:
                        logger.warning(f"Arquivo vazio ignorado: {arquivo.name}")
                except Exception as erro:
                    logger.error(f"Erro ao carregar '{arquivo.name}': {erro}")

        logger.info(
            f"Base de conhecimento: {len(documentos)} documento(s) carregado(s)."
        )
        return documentos

    def carregar_arquivo(self, caminho: str) -> dict:
        """
        Carrega um arquivo específico e retorna seu conteúdo estruturado.

        Args:
            caminho: Caminho absoluto para o arquivo.

        Returns:
            Dicionário com 'texto', 'fonte', 'caminho' e 'tipo'.
        """
        path = Path(caminho)
        texto, tipo = extrair_texto(caminho)
        return {
            "texto": texto,
            "fonte": path.name,
            "caminho": caminho,
            "tipo": tipo,
        }
