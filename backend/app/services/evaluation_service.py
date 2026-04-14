"""
Serviço de avaliação do pipeline RAG do DeclaraAI.

Implementa métricas quantitativas para avaliar a qualidade da recuperação
semântica e das respostas geradas, seguindo princípios inspirados no RAGAS.

Métricas implementadas:
    1. Relevância Semântica do Contexto: média dos scores de similaridade
       cosseno retornados pelo ChromaDB (0–1, quanto maior melhor).
    2. Cobertura de Palavras-Chave: percentual dos termos esperados
       encontrados na resposta gerada (0–100%).
    3. Taxa de Recuperação: proporção de perguntas para as quais ao menos
       um chunk relevante foi encontrado no banco vetorial.
    4. Análise de Casos de Falha: identifica perguntas onde a cobertura
       de palavras-chave ficou abaixo de 50%, indicando lacunas na base
       de conhecimento ou problemas no pipeline.

Referência metodológica:
    - Es et al. (2023): "RAGAS: Automated Evaluation of Retrieval Augmented Generation"
    - As métricas aqui implementadas são versões simplificadas que não
      requerem um LLM-juiz externo, tornando a avaliação autossuficiente.
"""

import re
from typing import List
from app.rag.retriever import Recuperador
from app.rag.vector_store import BancoVetorial
from app.services.rag_service import ServicoRAG
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Conjunto de casos de teste para o domínio IRPF
# ---------------------------------------------------------------------------
# Cada caso possui palavras-chave esperadas na resposta — usadas para calcular
# a métrica de cobertura. Foram escolhidas perguntas representativas das
# principais categorias do IRPF para validar a amplitude da base de conhecimento.
# ---------------------------------------------------------------------------

CASOS_TESTE: List[dict] = [
    {
        "id": 1,
        "pergunta": "Quem é obrigado a declarar o imposto de renda?",
        "palavras_chave": ["rendimentos tributáveis", "declarar", "obrigado", "bens", "800.000"],
        "categoria": "Obrigatoriedade",
    },
    {
        "id": 2,
        "pergunta": "Posso deduzir despesas com médico e dentista no IR?",
        "palavras_chave": ["médico", "dentista", "dedução", "integral", "saúde"],
        "categoria": "Deduções Médicas",
    },
    {
        "id": 3,
        "pergunta": "Qual é o limite de dedução para gastos com educação?",
        "palavras_chave": ["3.561", "educação", "escola", "limite", "universidade"],
        "categoria": "Deduções Educacionais",
    },
    {
        "id": 4,
        "pergunta": "Qual a diferença entre declaração simplificada e completa?",
        "palavras_chave": ["simplificada", "completa", "20%", "dedução padrão"],
        "categoria": "Modalidades",
    },
    {
        "id": 5,
        "pergunta": "Como funciona o PGBL para dedução no imposto de renda?",
        "palavras_chave": ["PGBL", "previdência", "12%", "renda bruta"],
        "categoria": "Previdência Privada",
    },
    {
        "id": 6,
        "pergunta": "Quais são as multas por não entregar a declaração no prazo?",
        "palavras_chave": ["multa", "prazo", "1%", "165", "penalidade"],
        "categoria": "Penalidades",
    },
    {
        "id": 7,
        "pergunta": "O que é o carnê-leão e quando devo pagar?",
        "palavras_chave": ["carnê-leão", "autônomo", "pessoa física", "mensal"],
        "categoria": "Autônomos",
    },
    {
        "id": 8,
        "pergunta": "Como incluir dependentes na declaração do imposto de renda?",
        "palavras_chave": ["dependente", "filho", "cônjuge", "dedução", "2.275"],
        "categoria": "Dependentes",
    },
]


class ServicoAvaliacao:
    """
    Avalia a qualidade do pipeline RAG do DeclaraAI.

    Fornece dois modos de avaliação:
    - Recuperação: avalia apenas o retriever (sem LLM, rápido)
    - Completa: avalia o pipeline inteiro incluindo geração de resposta
    """

    def __init__(self):
        # Instância única compartilhada entre recuperador e serviço RAG
        self.banco_vetorial = BancoVetorial()
        self.recuperador = Recuperador(banco_vetorial=self.banco_vetorial)
        self.servico_rag = ServicoRAG(banco_vetorial=self.banco_vetorial)

    # -----------------------------------------------------------------------
    # Avaliação de Recuperação (sem LLM)
    # -----------------------------------------------------------------------

    def avaliar_recuperacao(self) -> dict:
        """
        Avalia apenas a etapa de recuperação semântica, sem chamar o LLM.

        Métricas calculadas:
        - Score médio de contexto: relevância semântica dos chunks recuperados
        - Taxa de recuperação: % de perguntas com pelo menos 1 chunk encontrado
        - Casos sem contexto: perguntas onde a recuperação falhou

        Returns:
            Dicionário com métricas gerais e resultados por caso de teste.
        """
        logger.info("Iniciando avaliação de recuperação...")
        resultados: List[dict] = []

        for caso in CASOS_TESTE:
            chunks = self.recuperador.recuperar(caso["pergunta"])
            scores = [c.get("score", 0.0) for c in chunks]
            score_medio = round(sum(scores) / len(scores), 4) if scores else 0.0

            resultados.append({
                "id": caso["id"],
                "pergunta": caso["pergunta"],
                "categoria": caso["categoria"],
                "chunks_recuperados": len(chunks),
                "score_medio_contexto": score_medio,
                "score_maximo": round(max(scores), 4) if scores else 0.0,
                "fontes_encontradas": list({c.get("fonte", "") for c in chunks}),
                "contexto_encontrado": len(chunks) > 0,
            })

        # Métricas agregadas
        total = len(resultados)
        com_contexto = sum(1 for r in resultados if r["contexto_encontrado"])
        score_medio_geral = (
            sum(r["score_medio_contexto"] for r in resultados) / total
        )
        casos_falha = [r for r in resultados if not r["contexto_encontrado"]]

        metricas = {
            "tipo_avaliacao": "recuperacao_semantica",
            "total_casos_testados": total,
            "taxa_recuperacao_pct": round(com_contexto / total * 100, 1),
            "score_medio_contexto": round(score_medio_geral, 4),
            "chunks_indexados": self.banco_vetorial.total_chunks(),
            "casos_sem_contexto": len(casos_falha),
            "analise_falhas": [
                {"id": r["id"], "pergunta": r["pergunta"], "categoria": r["categoria"]}
                for r in casos_falha
            ],
            "resultados": resultados,
            "interpretacao": self._interpretar_recuperacao(
                com_contexto / total, score_medio_geral
            ),
        }

        logger.info(
            f"Avaliação de recuperação concluída: "
            f"taxa={metricas['taxa_recuperacao_pct']}% | "
            f"score_médio={metricas['score_medio_contexto']}"
        )
        return metricas

    # -----------------------------------------------------------------------
    # Avaliação Completa (com LLM)
    # -----------------------------------------------------------------------

    async def avaliar_completa(self) -> dict:
        """
        Avalia o pipeline completo: recuperação + geração de resposta via LLM.

        Métricas calculadas:
        - Score médio de contexto (relevância semântica)
        - Cobertura de palavras-chave (qualidade da resposta)
        - Taxa de recuperação
        - Análise de falhas (casos com baixa cobertura)

        Returns:
            Dicionário com métricas gerais e resultados detalhados por caso.
        """
        logger.info("Iniciando avaliação completa do pipeline RAG...")
        resultados: List[dict] = []

        for caso in CASOS_TESTE:
            logger.info(f"Avaliando caso {caso['id']}: {caso['pergunta'][:60]}...")

            resultado_rag = await self.servico_rag.responder_pergunta(caso["pergunta"])

            scores = resultado_rag.get("scores_contexto", [])
            score_medio = round(sum(scores) / len(scores), 4) if scores else 0.0
            cobertura_kw = self._calcular_cobertura_keywords(
                resultado_rag["resposta"], caso["palavras_chave"]
            )

            resultados.append({
                "id": caso["id"],
                "pergunta": caso["pergunta"],
                "categoria": caso["categoria"],
                "chunks_recuperados": resultado_rag["chunks_recuperados"],
                "score_medio_contexto": score_medio,
                "cobertura_keywords_pct": cobertura_kw,
                "palavras_esperadas": caso["palavras_chave"],
                "fontes": resultado_rag["fontes"],
                "resposta_preview": resultado_rag["resposta"][:300],
                "falha": cobertura_kw < 50.0,
            })

        # Métricas agregadas
        total = len(resultados)
        com_contexto = sum(1 for r in resultados if r["chunks_recuperados"] > 0)
        media_score = sum(r["score_medio_contexto"] for r in resultados) / total
        media_cobertura = sum(r["cobertura_keywords_pct"] for r in resultados) / total
        casos_falha = [r for r in resultados if r["falha"]]

        metricas = {
            "tipo_avaliacao": "pipeline_completo",
            "total_casos_testados": total,
            "taxa_recuperacao_pct": round(com_contexto / total * 100, 1),
            "score_medio_contexto": round(media_score, 4),
            "media_cobertura_keywords_pct": round(media_cobertura, 1),
            "casos_com_falha": len(casos_falha),
            "analise_falhas": [
                {
                    "id": r["id"],
                    "pergunta": r["pergunta"],
                    "categoria": r["categoria"],
                    "cobertura_pct": r["cobertura_keywords_pct"],
                }
                for r in casos_falha
            ],
            "resultados": resultados,
            "interpretacao": self._interpretar_pipeline(
                com_contexto / total, media_score, media_cobertura
            ),
        }

        logger.info(
            f"Avaliação completa concluída: "
            f"cobertura_média={metricas['media_cobertura_keywords_pct']}% | "
            f"score_médio={metricas['score_medio_contexto']}"
        )
        return metricas

    # -----------------------------------------------------------------------
    # Métodos auxiliares de cálculo
    # -----------------------------------------------------------------------

    def _calcular_cobertura_keywords(
        self, texto_resposta: str, palavras_chave: List[str]
    ) -> float:
        """
        Calcula a porcentagem de palavras-chave esperadas presentes na resposta.

        Args:
            texto_resposta: Texto da resposta gerada pelo LLM.
            palavras_chave: Lista de termos esperados na resposta.

        Returns:
            Percentual de cobertura (0.0 a 100.0).
        """
        if not palavras_chave:
            return 100.0

        texto_lower = texto_resposta.lower()
        encontradas = sum(
            1
            for palavra in palavras_chave
            if re.search(re.escape(palavra.lower()), texto_lower)
        )
        return round(encontradas / len(palavras_chave) * 100, 1)

    def _interpretar_recuperacao(self, taxa: float, score: float) -> str:
        """Gera interpretação textual das métricas de recuperação."""
        if taxa >= 0.9 and score >= 0.7:
            return "Excelente: alta taxa de recuperação com contexto muito relevante."
        elif taxa >= 0.7 and score >= 0.5:
            return "Bom: recuperação satisfatória. Considere ampliar a base de conhecimento."
        elif taxa >= 0.5:
            return "Regular: cobertura parcial. Adicione mais documentos à base de conhecimento."
        else:
            return "Insuficiente: muitas perguntas sem contexto. A base de conhecimento precisa ser expandida."

    def _interpretar_pipeline(
        self, taxa: float, score: float, cobertura: float
    ) -> str:
        """Gera interpretação textual das métricas do pipeline completo."""
        if taxa >= 0.9 and cobertura >= 70:
            return "Excelente: pipeline RAG funcionando com alta qualidade de recuperação e resposta."
        elif taxa >= 0.7 and cobertura >= 50:
            return "Bom: respostas coerentes na maioria dos casos. Amplie a base para melhorar cobertura."
        elif cobertura >= 30:
            return "Regular: algumas respostas são adequadas. Verifique o modelo LLM e a base de conhecimento."
        else:
            return "Insuficiente: respostas com baixa cobertura. Verifique o Ollama e expanda a base de conhecimento."

    def listar_casos_teste(self) -> List[dict]:
        """Retorna os casos de teste disponíveis para avaliação."""
        return [
            {
                "id": c["id"],
                "pergunta": c["pergunta"],
                "categoria": c["categoria"],
                "total_keywords": len(c["palavras_chave"]),
            }
            for c in CASOS_TESTE
        ]
