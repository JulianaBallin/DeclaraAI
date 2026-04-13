"""
Módulo de chunking textual para o pipeline RAG.

Estratégia adotada:
- chunk_size = 600 caracteres: tamanho suficiente para capturar contexto
  semântico completo em documentos fiscais (recibos, informes, NFs),
  sem diluir a relevância com trechos excessivamente longos.
- overlap = 80 caracteres: sobreposição entre chunks consecutivos para
  preservar frases cortadas na fronteira, evitando perda de contexto
  crítico como valores e nomes de emitentes.
- Quebra preferencial em parágrafos e frases, nunca no meio de palavras,
  o que melhora a coerência dos trechos recuperados pelo retriever.
"""

from typing import List
from app.core.config import configuracoes
import logging

logger = logging.getLogger(__name__)


class ChunkerTexto:
    """
    Divide textos longos em fragmentos (chunks) menores para indexação vetorial.

    A estratégia respeita quebras naturais de parágrafo e sentença,
    garantindo que cada chunk seja semanticamente coerente.
    """

    def __init__(self, tamanho_chunk: int | None = None, overlap: int | None = None):
        """
        Args:
            tamanho_chunk: Número máximo de caracteres por chunk.
            overlap: Número de caracteres de sobreposição entre chunks.
        """
        self.tamanho_chunk = tamanho_chunk or configuracoes.CHUNK_SIZE
        self.overlap = overlap or configuracoes.CHUNK_OVERLAP

    def dividir_texto(self, texto: str) -> List[str]:
        """
        Divide um texto em chunks com sobreposição.

        Tenta quebrar em pontos naturais (parágrafo, sentença, espaço)
        para preservar a coerência semântica de cada fragmento.

        Args:
            texto: Texto a ser dividido.

        Returns:
            Lista de strings, cada uma com no máximo tamanho_chunk caracteres.
        """
        if not texto or not texto.strip():
            return []

        texto = texto.strip()
        chunks: List[str] = []
        inicio = 0

        while inicio < len(texto):
            fim = inicio + self.tamanho_chunk

            if fim >= len(texto):
                # Último fragmento — inclui o restante
                fragmento = texto[inicio:].strip()
                if fragmento:
                    chunks.append(fragmento)
                break

            # Tenta quebrar em ponto natural para preservar coerência
            ponto_quebra = fim
            for separador in ["\n\n", "\n", ". ", "! ", "? ", " "]:
                posicao = texto.rfind(separador, inicio + self.tamanho_chunk // 2, fim)
                if posicao > inicio:
                    ponto_quebra = posicao + len(separador)
                    break

            fragmento = texto[inicio:ponto_quebra].strip()
            if fragmento:
                chunks.append(fragmento)

            # Avança com overlap para manter contexto entre fragmentos adjacentes
            proximo_inicio = ponto_quebra - self.overlap
            inicio = max(proximo_inicio, inicio + 1)  # Evita loop infinito

        logger.debug(f"Texto dividido em {len(chunks)} chunks.")
        return chunks

    def dividir_documentos(self, documentos: List[dict]) -> List[dict]:
        """
        Divide múltiplos documentos em chunks, preservando os metadados originais.

        Args:
            documentos: Lista de dicionários com campos 'texto', 'fonte', 'tipo', etc.

        Returns:
            Lista de chunks enriquecidos com metadados de origem.
        """
        todos_chunks: List[dict] = []

        for documento in documentos:
            chunks = self.dividir_texto(documento["texto"])
            total = len(chunks)

            for indice, chunk in enumerate(chunks):
                todos_chunks.append({
                    "texto": chunk,
                    "fonte": documento.get("fonte", "desconhecido"),
                    "caminho": documento.get("caminho", ""),
                    "tipo": documento.get("tipo", ""),
                    "chunk_index": indice,
                    "total_chunks": total,
                })

        logger.info(f"Total de chunks gerados: {len(todos_chunks)}")
        return todos_chunks
