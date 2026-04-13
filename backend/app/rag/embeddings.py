"""
Geração de embeddings vetoriais com sentence-transformers.

Modelo padrão: paraphrase-multilingual-MiniLM-L12-v2
- Suporte nativo a português e outros idiomas
- 384 dimensões — bom equilíbrio entre qualidade e eficiência
- Leve o suficiente para rodar em CPU durante protótipos acadêmicos
- Desempenho comprovado em tarefas de similaridade semântica

O padrão Singleton garante que o modelo seja carregado uma única vez
na memória durante toda a execução da aplicação.
"""

from sentence_transformers import SentenceTransformer
from typing import List
from app.core.config import configuracoes
import logging

logger = logging.getLogger(__name__)

# Instância global do modelo (Singleton via módulo)
_modelo_global: SentenceTransformer | None = None


def _obter_modelo() -> SentenceTransformer:
    """
    Retorna a instância global do modelo de embeddings,
    carregando-a na primeira chamada (lazy loading).
    """
    global _modelo_global
    if _modelo_global is None:
        logger.info(
            f"Carregando modelo de embeddings: {configuracoes.MODELO_EMBEDDINGS}"
        )
        _modelo_global = SentenceTransformer(configuracoes.MODELO_EMBEDDINGS)
        logger.info("Modelo de embeddings carregado com sucesso.")
    return _modelo_global


class GeradorEmbeddings:
    """
    Interface para geração de embeddings textuais.

    Utiliza um modelo sentence-transformers compartilhado via Singleton,
    evitando múltiplos carregamentos do modelo em memória.
    """

    def gerar(self, texto: str) -> List[float]:
        """
        Gera embedding para um único texto.

        Args:
            texto: Texto a ser vetorizado.

        Returns:
            Lista de floats representando o vetor semântico do texto.
        """
        if not texto or not texto.strip():
            return []
        modelo = _obter_modelo()
        vetor = modelo.encode(texto, show_progress_bar=False, convert_to_numpy=True)
        return vetor.tolist()

    def gerar_lote(self, textos: List[str]) -> List[List[float]]:
        """
        Gera embeddings para múltiplos textos de forma eficiente (batch).

        Args:
            textos: Lista de textos a serem vetorizados.

        Returns:
            Lista de vetores, um por texto de entrada.
        """
        if not textos:
            return []
        modelo = _obter_modelo()
        logger.info(f"Gerando embeddings para {len(textos)} texto(s)...")
        vetores = modelo.encode(
            textos,
            show_progress_bar=True,
            batch_size=32,
            convert_to_numpy=True,
        )
        return vetores.tolist()
