"""
Serviço orquestrador do pipeline RAG completo.

Coordena todas as etapas desde a ingestão de documentos até a geração
de respostas contextualizadas, expondo uma interface limpa para as rotas da API.

Pipeline:
    1. Ingestão  → CarregadorDocumentos lê arquivos da base de conhecimento
    2. Chunking  → ChunkerTexto divide textos em fragmentos semânticos
    3. Embeddings → GeradorEmbeddings vetoriza cada fragmento
    4. Indexação  → BancoVetorial persiste no ChromaDB
    5. Recuperação → Recuperador busca os chunks mais relevantes
    6. Geração   → GeradorResposta monta e envia o prompt ao LLM (Ollama)
"""

from app.rag.loader import CarregadorDocumentos
from app.rag.chunker import ChunkerTexto
from app.rag.vector_store import BancoVetorial
from app.rag.retriever import Recuperador
from app.rag.generator import GeradorResposta
from app.core.config import configuracoes
import logging

logger = logging.getLogger(__name__)


class ServicoRAG:
    """
    Orquestrador do pipeline RAG do DeclaraAI.

    Instancia e conecta todos os componentes necessários para ingestão
    de documentos e geração de respostas baseadas em recuperação semântica.

    Nota: o BancoVetorial é criado uma única vez e compartilhado com o
    Recuperador para evitar conexões duplicadas ao ChromaDB.
    """

    def __init__(self):
        self.carregador = CarregadorDocumentos()
        self.chunker = ChunkerTexto()
        # Instância compartilhada: evita abrir duas conexões ao ChromaDB
        self.banco_vetorial = BancoVetorial()
        self.recuperador = Recuperador(banco_vetorial=self.banco_vetorial)
        self.gerador = GeradorResposta()

    # -----------------------------------------------------------------------
    # Ingestão
    # -----------------------------------------------------------------------

    def ingerir_base_conhecimento(self) -> int:
        """
        Executa a ingestão completa da base de conhecimento.

        Carrega todos os arquivos do diretório configurado, fragmenta,
        vetoriza e indexa no ChromaDB.

        Returns:
            Número total de chunks indexados.
        """
        logger.info("Iniciando ingestão da base de conhecimento...")

        documentos = self.carregador.carregar_todos()
        if not documentos:
            logger.warning("Nenhum documento encontrado para ingerir.")
            return 0

        chunks = self.chunker.dividir_documentos(documentos)
        total = self.banco_vetorial.adicionar_chunks(chunks)

        logger.info(f"Ingestão concluída: {total} chunk(s) indexado(s).")
        return total

    def ingerir_documento(self, texto: str, fonte: str, tipo: str = "documento") -> int:
        """
        Ingere um único documento diretamente pelo seu texto.

        Usado após o upload de documentos pelo usuário, permitindo que eles
        sejam consultados no chat.

        Args:
            texto: Conteúdo textual do documento.
            fonte: Nome ou identificador da fonte (ex: nome do arquivo).
            tipo: Tipo do documento (pdf, txt, html, etc.).

        Returns:
            Número de chunks indexados.
        """
        chunks_texto = self.chunker.dividir_texto(texto)
        total_chunks = len(chunks_texto)

        chunks_formatados = [
            {
                "texto": chunk,
                "fonte": fonte,
                "tipo": tipo,
                "chunk_index": i,
                "total_chunks": total_chunks,
            }
            for i, chunk in enumerate(chunks_texto)
        ]

        return self.banco_vetorial.adicionar_chunks(chunks_formatados)

    # -----------------------------------------------------------------------
    # Consulta
    # -----------------------------------------------------------------------

    async def responder_pergunta(self, pergunta: str) -> dict:
        """
        Executa o pipeline completo RAG para responder uma pergunta.

        Etapas:
        1. Recupera chunks semânticamente relevantes do ChromaDB
        2. Formata o contexto para o prompt
        3. Envia ao LLM via Ollama e retorna a resposta

        Args:
            pergunta: Pergunta do usuário em linguagem natural.

        Returns:
            Dicionário com resposta, contexto, fontes, scores e contagem de chunks.
        """
        logger.info(f"Processando pergunta: '{pergunta[:80]}...'")

        # Passo 1: Recuperação semântica
        chunks_relevantes = self.recuperador.recuperar(pergunta)

        # Passo 2: Formatação do contexto
        contexto = self.recuperador.formatar_contexto(chunks_relevantes)

        # Passo 3: Geração de resposta
        resposta = await self.gerador.gerar(pergunta, contexto)

        # Deduplica fontes e coleta scores de similaridade para avaliação
        fontes = list({c.get("fonte", "") for c in chunks_relevantes if c.get("fonte")})
        scores = [round(c.get("score", 0.0), 4) for c in chunks_relevantes]

        return {
            "resposta": resposta,
            "contexto_utilizado": [c["texto"] for c in chunks_relevantes],
            "fontes": fontes,
            "chunks_recuperados": len(chunks_relevantes),
            "scores_contexto": scores,
        }

    # -----------------------------------------------------------------------
    # Status
    # -----------------------------------------------------------------------

    def obter_status(self) -> dict:
        """
        Retorna métricas e configurações atuais do sistema RAG.

        Returns:
            Dicionário com informações de diagnóstico.
        """
        return {
            "chunks_indexados": self.banco_vetorial.total_chunks(),
            "modelo_embeddings": configuracoes.MODELO_EMBEDDINGS,
            "modelo_llm": configuracoes.OLLAMA_MODELO,
            "ollama_url": configuracoes.OLLAMA_BASE_URL,
            "caminho_base_conhecimento": configuracoes.CAMINHO_BASE_CONHECIMENTO,
            "caminho_chroma": configuracoes.CAMINHO_CHROMA,
            "chunk_size": configuracoes.CHUNK_SIZE,
            "chunk_overlap": configuracoes.CHUNK_OVERLAP,
            "top_k": configuracoes.TOP_K_RESULTADOS,
        }
