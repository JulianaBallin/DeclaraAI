"""
Recuperador semântico do pipeline RAG.

Realiza busca por similaridade no ChromaDB e formata o contexto
para envio ao modelo gerador (LLM).

Estrutura preparada para re-ranking com cross-encoder:
O método _reranquear() está documentado com instruções de implementação.
Para ativá-lo, instale um modelo cross-encoder e descomente o código.
"""

from typing import List
from app.rag.vector_store import BancoVetorial
from app.core.config import configuracoes
import logging

logger = logging.getLogger(__name__)


class Recuperador:
    """
    Recupera chunks relevantes do banco vetorial para uma dada consulta.

    Fluxo:
    1. Busca por similaridade semântica (bi-encoder via ChromaDB)
    2. Re-ranking opcional com cross-encoder (estrutura preparada)
    3. Formatação do contexto para o LLM
    """

    def __init__(self):
        self.banco_vetorial = BancoVetorial()

    def recuperar(
        self,
        consulta: str,
        top_k: int | None = None,
        usar_reranking: bool = False,
    ) -> List[dict]:
        """
        Recupera os chunks mais relevantes para a consulta.

        Args:
            consulta: Texto da pergunta do usuário.
            top_k: Número de resultados a retornar.
            usar_reranking: Se True, aplica re-ranking nos resultados.

        Returns:
            Lista de chunks ordenados por relevância.
        """
        top_k = top_k or configuracoes.TOP_K_RESULTADOS

        resultados = self.banco_vetorial.buscar_similares(consulta, top_k=top_k)

        if not resultados:
            logger.warning(f"Nenhum chunk recuperado para: '{consulta[:60]}...'")
            return []

        if usar_reranking:
            resultados = self._reranquear(consulta, resultados)

        logger.info(
            f"Recuperados {len(resultados)} chunk(s) | "
            f"Score máximo: {resultados[0]['score']:.3f}"
        )
        return resultados

    def _reranquear(self, consulta: str, resultados: List[dict]) -> List[dict]:
        """
        Re-ranqueia resultados usando modelo cross-encoder.

        ESTRUTURA PREPARADA — para implementar:
        1. Instale: pip install sentence-transformers
        2. Use o modelo: cross-encoder/ms-marco-MiniLM-L-6-v2
        3. Descomente o código abaixo

        Vantagem sobre bi-encoder:
        O cross-encoder avalia o par (consulta, texto) conjuntamente,
        capturando relações semânticas mais finas e melhorando a ordem
        dos resultados para perguntas complexas.
        """
        # ----------------------------------------------------------------
        # from sentence_transformers import CrossEncoder
        # cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        # pares = [[consulta, r["texto"]] for r in resultados]
        # scores = cross_encoder.predict(pares)
        # resultados_reranqueados = sorted(
        #     zip(scores, resultados), key=lambda x: x[0], reverse=True
        # )
        # return [r for _, r in resultados_reranqueados]
        # ----------------------------------------------------------------

        logger.debug("Re-ranking desabilitado — retornando ordem original.")
        return resultados

    def formatar_contexto(self, chunks: List[dict]) -> str:
        """
        Formata os chunks recuperados em um bloco de contexto para o LLM.

        Cada chunk é separado por delimitador para que o modelo possa
        identificar a fronteira entre diferentes trechos da base de conhecimento.

        Args:
            chunks: Lista de chunks com campos 'texto' e 'fonte'.

        Returns:
            String formatada com o contexto completo para o prompt.
        """
        if not chunks:
            return "Nenhum trecho relevante encontrado na base de conhecimento."

        partes: List[str] = []
        for i, chunk in enumerate(chunks, start=1):
            fonte = chunk.get("fonte", "Fonte desconhecida")
            partes.append(f"[Trecho {i} | Fonte: {fonte}]\n{chunk['texto']}")

        return "\n\n---\n\n".join(partes)
