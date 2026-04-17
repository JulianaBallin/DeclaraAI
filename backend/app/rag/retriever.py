"""
Recuperador semântico do pipeline RAG.

Realiza busca por similaridade no ChromaDB, aplica re-ranking com cross-encoder
multilíngue e formata o contexto para envio ao modelo gerador (LLM).

Re-ranking:
    Modelo: cross-encoder/mmarco-mMiniLMv2-L12-H384-v1
    Justificativa: treinado em MS MARCO multilíngue (inclui português), avalia
    o par (consulta, trecho) de forma conjunta — captura relações semânticas
    mais finas que o bi-encoder e melhora a precisão para perguntas complexas.
"""

from typing import List
from sentence_transformers import CrossEncoder
from app.rag.vector_store import BancoVetorial
from app.core.config import configuracoes
import logging

logger = logging.getLogger(__name__)


# Singleton do cross-encoder carregado na primeira chamada ao re-ranking
_cross_encoder_global: CrossEncoder | None = None

# Modelo multilíngue treinado no MS MARCO — suporta português nativamente
_MODELO_CROSS_ENCODER = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"


def _obter_cross_encoder() -> CrossEncoder:
    """Retorna instância global do cross-encoder, carregando na primeira chamada."""
    global _cross_encoder_global
    if _cross_encoder_global is None:
        logger.info(f"Carregando cross-encoder: {_MODELO_CROSS_ENCODER}")
        _cross_encoder_global = CrossEncoder(_MODELO_CROSS_ENCODER)
        logger.info("Cross-encoder carregado com sucesso.")
    return _cross_encoder_global


class Recuperador:
    """
    Recupera chunks relevantes do banco vetorial para uma dada consulta.

    Fluxo:
    1. Busca por similaridade semântica (bi-encoder via ChromaDB)
    2. Re-ranking com cross-encoder multilíngue (mmarco-mMiniLMv2)
    3. Formatação do contexto para o LLM
    """

    def __init__(self, banco_vetorial: BancoVetorial | None = None):
        """
        Args:
            banco_vetorial: Instância opcional de BancoVetorial.
                            Se não fornecida, cria uma nova.
                            Passar a instância evita conexões duplicadas ao ChromaDB.
        """
        self.banco_vetorial = banco_vetorial or BancoVetorial()

    def recuperar(
        self,
        consulta: str,
        top_k: int | None = None,
        usar_reranking: bool = True,
    ) -> List[dict]:
        """
        Recupera os chunks mais relevantes para a consulta.

        Busca um número maior de candidatos no bi-encoder (top_k * 3) e depois
        aplica o cross-encoder para re-rankear e retornar apenas os top_k melhores.

        Args:
            consulta: Texto da pergunta do usuário.
            top_k: Número de resultados a retornar após re-ranking.
            usar_reranking: Se True (padrão), aplica re-ranking com cross-encoder.

        Returns:
            Lista de chunks ordenados por relevância.
        """
        top_k = top_k or configuracoes.TOP_K_RESULTADOS

        # Recupera mais candidatos para o re-ranking ter melhor pool de seleção
        candidatos_k = top_k * 3 if usar_reranking else top_k
        resultados = self.banco_vetorial.buscar_similares(consulta, top_k=candidatos_k)

        if not resultados:
            trecho = consulta[:60] + ("..." if len(consulta) > 60 else "")
            logger.warning(f"Nenhum chunk recuperado para: '{trecho}'")
            return []

        if usar_reranking and len(resultados) > 1:
            resultados = self._reranquear(consulta, resultados)[:top_k]

        logger.info(
            f"Recuperados {len(resultados)} chunk(s) | "
            f"Score máximo: {resultados[0]['score']:.3f}"
        )
        return resultados

    def _reranquear(self, consulta: str, resultados: List[dict]) -> List[dict]:
        """
        Re-ranqueia resultados usando cross-encoder multilíngue.

        O cross-encoder avalia o par (consulta, trecho) de forma conjunta,
        capturando relações semânticas mais finas que o bi-encoder e melhorando
        a precisão para perguntas complexas em português.

        Args:
            consulta: Texto da pergunta do usuário.
            resultados: Lista de chunks retornados pelo bi-encoder.

        Returns:
            Lista re-ordenada por score do cross-encoder (maior primeiro).
        """
        try:
            cross_encoder = _obter_cross_encoder()
            pares = [[consulta, r["texto"]] for r in resultados]
            scores = cross_encoder.predict(pares)
            reordenados = sorted(
                zip(scores, resultados), key=lambda x: x[0], reverse=True
            )
            logger.debug(f"Re-ranking aplicado sobre {len(resultados)} candidato(s).")
            return [r for _, r in reordenados]
        except Exception as erro:
            logger.warning(f"Re-ranking falhou, usando ordem original: {erro}")
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
