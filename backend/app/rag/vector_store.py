"""
Gerenciamento do banco vetorial ChromaDB.

Responsável por persistir embeddings de chunks e recuperá-los por
similaridade semântica (cosine similarity).
"""

import chromadb
import uuid
from typing import List
from app.core.config import configuracoes
from app.rag.embeddings import GeradorEmbeddings
import logging

logger = logging.getLogger(__name__)

NOME_COLECAO = "base_conhecimento"


class BancoVetorial:
    """
    Interface com o ChromaDB para armazenamento e busca vetorial.

    Usa distância cosseno para comparação de embeddings, o que é mais
    robusto para documentos de comprimentos variados.
    """

    def __init__(self):
        self.gerador = GeradorEmbeddings()
        self._inicializar_cliente()

    def _inicializar_cliente(self) -> None:
        """Cria o cliente persistente e garante que a coleção exista."""
        try:
            self.cliente = chromadb.PersistentClient(
                path=configuracoes.CAMINHO_CHROMA
            )
            self.colecao = self.cliente.get_or_create_collection(
                name=NOME_COLECAO,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                f"ChromaDB inicializado em '{configuracoes.CAMINHO_CHROMA}' "
                f"| Chunks armazenados: {self.colecao.count()}"
            )
        except Exception as erro:
            logger.error(f"Falha ao inicializar ChromaDB: {erro}")
            raise

    def adicionar_chunks(self, chunks: List[dict]) -> int:
        """
        Adiciona uma lista de chunks ao banco vetorial.

        Gera embeddings em lote e persiste com metadados de origem
        para rastreabilidade das fontes durante a recuperação.

        Args:
            chunks: Lista de dicionários com 'texto', 'fonte', 'tipo', etc.

        Returns:
            Número de chunks efetivamente adicionados.
        """
        if not chunks:
            return 0

        textos = [c["texto"] for c in chunks]
        embeddings = self.gerador.gerar_lote(textos)

        ids = [str(uuid.uuid4()) for _ in chunks]
        metadados = [
            {
                "fonte": c.get("fonte", ""),
                "tipo": c.get("tipo", ""),
                "chunk_index": str(c.get("chunk_index", 0)),
            }
            for c in chunks
        ]

        self.colecao.add(
            ids=ids,
            embeddings=embeddings,
            documents=textos,
            metadatas=metadados,
        )

        logger.info(f"{len(chunks)} chunk(s) adicionado(s) ao ChromaDB.")
        return len(chunks)

    def buscar_similares(self, consulta: str, top_k: int | None = None) -> List[dict]:
        """
        Recupera os chunks mais similares à consulta por similaridade semântica.

        Args:
            consulta: Texto da pergunta ou busca.
            top_k: Número máximo de resultados a retornar.

        Returns:
            Lista de dicionários com 'texto', 'fonte', 'tipo' e 'score'.
        """
        top_k = top_k or configuracoes.TOP_K_RESULTADOS
        total = self.colecao.count()

        if total == 0:
            logger.warning("ChromaDB está vazio. Nenhum resultado possível.")
            return []

        embedding_consulta = self.gerador.gerar(consulta)
        n_resultados = min(top_k, total)

        resultados = self.colecao.query(
            query_embeddings=[embedding_consulta],
            n_results=n_resultados,
            include=["documents", "metadatas", "distances"],
        )

        chunks_relevantes: List[dict] = []
        if resultados["documents"] and resultados["documents"][0]:
            for texto, meta, distancia in zip(
                resultados["documents"][0],
                resultados["metadatas"][0],
                resultados["distances"][0],
            ):
                chunks_relevantes.append({
                    "texto": texto,
                    "fonte": meta.get("fonte", ""),
                    "tipo": meta.get("tipo", ""),
                    "score": round(1 - distancia, 4),  # Converte distância → similaridade
                })

        return chunks_relevantes

    def total_chunks(self) -> int:
        """Retorna o total de chunks armazenados na coleção."""
        return self.colecao.count()

    def limpar(self) -> None:
        """Remove todos os documentos da coleção (útil para re-indexação completa)."""
        self.cliente.delete_collection(NOME_COLECAO)
        self.colecao = self.cliente.get_or_create_collection(
            name=NOME_COLECAO,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("Coleção do ChromaDB limpa com sucesso.")
