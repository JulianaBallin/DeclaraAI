"""
Geração de justificativas enriquecidas via LLM com contexto da base de conhecimento.

Após a classificação tributária (por regras ou LLM), este serviço recupera trechos
relevantes da base de conhecimento (ChromaDB) e usa o Mistral para produzir uma
explicação personalizada e fundamentada sobre por que o documento recebeu aquela
classificação e o que o contribuinte precisa verificar na declaração do IRPF.
"""

import logging
import httpx
from app.core.config import configuracoes
from app.rag.retriever import Recuperador
from app.rag.vector_store import BancoVetorial

logger = logging.getLogger(__name__)

# Consultas otimizadas por categoria para recuperar os chunks mais relevantes da base
_CONSULTAS_POR_CATEGORIA: dict[str, str] = {
    "Recibo Médico": (
        "despesas médicas dedutíveis IRPF código 09 dentista psicólogo fisioterapeuta "
        "pagamentos efetuados sem limite valor"
    ),
    "Comprovante Educacional": (
        "dedução educação instrução IRPF limite 3561 código 01 MEC ensino regular "
        "educação infantil fundamental médio superior técnico"
    ),
    "Informe de Rendimentos": (
        "informe rendimentos IRPF fonte pagadora salário rendimento tributável INSS IRRF "
        "rendimentos isentos tributados exclusivamente na fonte"
    ),
    "Nota Fiscal": (
        "nota fiscal eletrônica NF-e NFS-e dedutibilidade IRPF chave acesso SEFAZ "
        "natureza serviço produto dedução"
    ),
    "Previdência Privada": (
        "PGBL previdência privada IRPF código 36 limite 12% renda bruta tributável "
        "VGBL plano benefício contribuição"
    ),
    "Doações": (
        "doações dedutíveis IRPF fundos incentivados ECA PRONAC fundo criança idoso "
        "entidade habilitada percentual imposto"
    ),
    "Pensão Alimentícia": (
        "pensão alimentícia dedutível IRPF código 30 sentença judicial escritura pública "
        "alimentando alimentante pagamentos efetuados"
    ),
    "Aluguel": (
        "aluguel IRPF pagamentos efetuados código 70 carnê-leão rendimento tributável "
        "locador locatário pessoa física"
    ),
    "Saúde": (
        "despesas médicas dedutíveis IRPF código 09 dentista psicólogo fisioterapeuta "
        "pagamentos efetuados sem limite valor recibo comprovante"
    ),
    "Educação": (
        "dedução educação instrução IRPF limite 3561 código 01 MEC ensino regular "
        "educação infantil fundamental médio superior"
    ),
    "Documento Não Classificado": (
        "documentos fiscais IRPF comprovante pagamento despesas dedutíveis"
    ),
    "Requer Revisão": "documentos fiscais IRPF revisão classificação tributária",
}

PROMPT_JUSTIFICATIVA = """\
Você é o DeclaraAI, especialista em imposto de renda para pessoas físicas no Brasil.

Analise as informações do documento abaixo e produza uma justificativa técnica de 2 a 4 \
linhas explicando a classificação e o que o contribuinte deve fazer na declaração do IRPF.

PROIBIÇÕES ABSOLUTAS — leia com atenção:
1. NUNCA escreva "Trecho 1", "Trecho 2", "Trecho 3" nem qualquer referência numerada a fontes.
2. NUNCA invente valores, limites ou percentuais que não estejam explicitamente no texto de referência.
3. NUNCA use introduções como "Com base em...", "De acordo com...", "Conforme as informações...".
4. Se as informações de referência não contêm um limite específico para a categoria, NÃO mencione limite.

DOCUMENTO:
- Categoria tributária: {categoria}
- Natureza do conteúdo: {categoria_conteudo}
- Tipo de documento: {tipo_documento}
- Emitente: {emitente}
- Beneficiário: {beneficiario}
- Valor: {valor}
- Situação no IRPF: {status_irpf}

INFORMAÇÕES DE REFERÊNCIA (base de conhecimento DeclaraAI):
{contexto}

JUSTIFICATIVA (2–4 linhas, português, técnico, direto):"""


class ServicoJustificativa:
    """
    Gera justificativas enriquecidas combinando recuperação semântica (RAG) e LLM.

    Para cada documento classificado, recupera os trechos mais relevantes da base de
    conhecimento tributário e usa o Mistral para produzir uma explicação personalizada,
    fundamentada e citando as regras fiscais aplicáveis.
    """

    def __init__(self, banco_vetorial: BancoVetorial | None = None):
        bv = banco_vetorial or BancoVetorial()
        self.recuperador = Recuperador(banco_vetorial=bv)
        self.url_ollama = f"{configuracoes.OLLAMA_BASE_URL.rstrip('/')}/api/generate"

    async def gerar(
        self,
        categoria: str,
        tipo_documento: str = "",
        emitente: str = "",
        beneficiario: str = "",
        valor: str = "",
        status_irpf: str = "",
        categoria_conteudo: str = "",
    ) -> str:
        """
        Gera justificativa enriquecida para a classificação de um documento.

        Retorna string vazia em caso de falha (sem exceção propagada) para não
        bloquear o fluxo principal de upload e processamento.

        Args:
            categoria: Categoria tributária atribuída ao documento.
            tipo_documento: Tipo do documento (NF-e, Recibo, etc.).
            emitente: Nome do emitente detectado.
            beneficiario: Nome do beneficiário detectado.
            valor: Valor monetário detectado.
            status_irpf: Situação calculada no IRPF.
            categoria_conteudo: Natureza do conteúdo (Saúde, Educação, Aluguel...).

        Returns:
            Justificativa textual gerada pela LLM, ou string vazia se falhar.
        """
        try:
            # Usa a natureza do conteúdo para melhorar a query quando a categoria
            # principal não é suficientemente específica (ex.: "Documento Não Classificado"
            # com conteúdo de saúde deve consultar chunks de despesas médicas)
            chave_consulta = categoria
            if chave_consulta in ("Documento Não Classificado", "Requer Revisão"):
                for conteudo_chave in ("Saúde", "Educação", "Aluguel", "Pensão"):
                    if categoria_conteudo and conteudo_chave.lower() in categoria_conteudo.lower():
                        chave_consulta = conteudo_chave
                        break

            consulta = _CONSULTAS_POR_CATEGORIA.get(
                chave_consulta, f"{categoria} IRPF dedução regras comprovante"
            )

            chunks = self.recuperador.recuperar(consulta, top_k=3)
            if not chunks:
                logger.warning("Justificativa: nenhum chunk recuperado para '%s'.", categoria)
                return ""

            contexto = self.recuperador.formatar_contexto(chunks)

            prompt = PROMPT_JUSTIFICATIVA.format(
                categoria=categoria,
                categoria_conteudo=categoria_conteudo or "Não identificada",
                tipo_documento=tipo_documento or "Não identificado",
                emitente=emitente or "Não identificado",
                beneficiario=beneficiario or "Não identificado",
                valor=valor or "Não informado",
                status_irpf=status_irpf or "A definir",
                contexto=contexto,
            )

            payload = {
                "model": configuracoes.OLLAMA_MODELO,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.15,
                    "top_p": 0.9,
                    "num_ctx": 4096,
                    "num_predict": 350,
                },
            }

            async with httpx.AsyncClient(timeout=150.0) as cliente:
                resposta = await cliente.post(self.url_ollama, json=payload)
                resposta.raise_for_status()
                texto = resposta.json().get("response", "").strip()
                if texto:
                    logger.info(
                        "Justificativa gerada para '%s': %d caracteres.", categoria, len(texto)
                    )
                return texto

        except httpx.ConnectError:
            logger.warning("Justificativa: Ollama indisponível — justificativa omitida.")
            return ""
        except httpx.TimeoutException:
            logger.warning("Justificativa: timeout ao aguardar Ollama — justificativa omitida.")
            return ""
        except Exception as erro:
            logger.error("Justificativa: erro inesperado: %s", erro, exc_info=True)
            return ""
