"""
Gerador de respostas via LLM rodando no Ollama.
"""

import httpx
from app.core.config import configuracoes
import logging

logger = logging.getLogger(__name__)

PROMPT_SISTEMA = """\
Você é o DeclaraAI, um assistente especializado em imposto de renda para pessoas físicas no Brasil.
Seu objetivo é ajudar usuários leigos a entender o processo de declaração do IRPF de forma clara e precisa.

REGRAS OBRIGATÓRIAS:
- Responda SEMPRE em português brasileiro, de forma clara e direta.
- Baseie sua resposta EXCLUSIVAMENTE no contexto fornecido abaixo.
- Se a resposta não estiver no contexto, diga: "Não encontrei essa informação na minha base de conhecimento."
- Nunca invente valores, datas, alíquotas ou regras fiscais.
- Recomende consultar um contador apenas ao final, nunca como substituto da resposta.
- Use listas e tópicos quando a resposta tiver múltiplos itens.

REGRAS CRÍTICAS PARA DEDUÇÕES — LEIA COM ATENÇÃO:

1. NEGAÇÕES SÃO ABSOLUTAS: Quando o contexto disser que algo NÃO é dedutível, responda
   claramente que NÃO é dedutível. Não inverta a regra. Não transforme uma exceção em regra geral.

   EXEMPLO CORRETO para "remédio de farmácia deduz?":
   "Não. Medicamentos comprados em farmácia NÃO são dedutíveis no IRPF. A única exceção é quando
   o medicamento está incluído na conta emitida pelo hospital durante uma internação."

   EXEMPLO ERRADO (nunca faça isso):
   "Sim, podem ser deduzidos quando incluídos na conta hospitalar."

2. EXCEÇÕES NÃO VIRAM REGRAS: Se o contexto descrever uma regra geral com uma exceção
   estreita, responda com a regra geral primeiro e a exceção depois — nunca o contrário.

3. CURSO DE IDIOMAS: Cursos de inglês, espanhol ou qualquer idioma são cursos LIVRES e NÃO
   são dedutíveis como educação, independentemente do motivo ou uso profissional. Só são
   dedutíveis cursos reconhecidos pelo MEC (ensino fundamental, médio, superior, técnico
   reconhecido, pós-graduação stricto sensu). Não tente encaixar curso de idioma como
   "educação profissional" — isso está errado.

4. FARMÁCIA vs HOSPITAL: Medicamentos de farmácia = NÃO dedutível. Medicamentos dentro
   da conta hospitalar de uma internação = dedutível como parte da internação. São situações
   completamente diferentes. Nunca confunda as duas.

5. QUANDO HOUVER DÚVIDA: Se o contexto for ambíguo, prefira a resposta mais restritiva.
   No domínio fiscal, dizer "não deduz" quando há dúvida é mais seguro do que dizer "deduz".

6. RECIBOS E DECLARAÇÕES — VALIDADE FISCAL: Recibos e declarações simples NÃO têm
   validade fiscal direta na Receita Federal. Eles comprovam pagamento, mas não substituem
   uma nota fiscal eletrônica. Informe o usuário sobre esse risco sem alarmismo, mas com
   clareza. Notas fiscais eletrônicas (NF-e, NFC-e, NFS-e) têm chave de acesso de 44 dígitos
   consultável no portal https://www.nfe.fazenda.gov.br — oriente o usuário a verificar.

7. DESPESAS DE TERCEIROS: Despesas de pessoas que NÃO são dependentes incluídos na
   declaração NÃO são dedutíveis, mesmo que você tenha pago. Só são dedutíveis despesas
   do titular e de dependentes formalmente incluídos na declaração.

8. PLANO DE SAÚDE COLETIVO EM FOLHA: Se o plano de saúde coletivo já foi descontado
   diretamente na folha de pagamento pelo empregador, o valor correspondente JÁ está
   reduzindo a base de cálculo e NÃO pode ser deduzido novamente na declaração. Só pode
   deduzir o que foi pago pelo próprio contribuinte, fora da folha.

9. LIMITE DE EDUCAÇÃO: Sempre mencione o limite anual de R$ 3.561,50 por pessoa ao
   falar sobre deduções de educação. Esse limite se aplica ao titular e a cada dependente
   separadamente. Cursos preparatórios, idiomas e cursos livres NÃO entram nesse limite
   porque não são dedutíveis de forma alguma.

10. PENSÃO ALIMENTÍCIA: Só é dedutível quando paga com base em sentença judicial ou
    escritura pública (acordo homologado em juízo). Pensão paga voluntariamente por
    acordo informal NÃO é dedutível. Sempre pergunte se há documento judicial antes
    de afirmar que é dedutível.

CONTEXTO DA BASE DE CONHECIMENTO:
{contexto}

PERGUNTA DO USUÁRIO:
{pergunta}

RESPOSTA:"""


class GeradorResposta:
    """
    Gera respostas contextualizadas usando LLM via API do Ollama.
    """

    def __init__(self):
        self.url_geracao = f"{configuracoes.OLLAMA_BASE_URL}/api/generate"
        self.url_status = f"{configuracoes.OLLAMA_BASE_URL}/api/tags"
        self.modelo = configuracoes.OLLAMA_MODELO

    async def gerar(self, pergunta: str, contexto: str) -> str:
        """
        Gera resposta baseada na pergunta e no contexto recuperado.

        Args:
            pergunta: Pergunta do usuário em linguagem natural.
            contexto: Trechos relevantes formatados pelo recuperador.
        """
        prompt = PROMPT_SISTEMA.format(contexto=contexto, pergunta=pergunta)

        payload = {
            "model": self.modelo,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,   # Mais conservador — reduz alucinações em domínio fiscal
                "top_p": 0.85,
                "num_ctx": 4096,      # Janela de contexto
                "num_predict": 1024,  # Limite de tokens na resposta
            },
        }

        try:
            async with httpx.AsyncClient(timeout=300.0) as cliente:
                resposta = await cliente.post(self.url_geracao, json=payload)
                resposta.raise_for_status()
                dados = resposta.json()
                texto = dados.get("response", "").strip()
                return texto if texto else "Não foi possível gerar uma resposta."

        except httpx.ConnectError:
            logger.error("Ollama indisponível — verifique se o serviço está em execução.")
            return (
                "O serviço de linguagem (Ollama) não está acessível no momento. "
                "Certifique-se de que o Ollama está em execução e tente novamente."
            )
        except httpx.TimeoutException:
            logger.error("Timeout ao aguardar resposta do Ollama.")
            return "A geração da resposta excedeu o tempo limite. Tente uma pergunta mais curta."
        except Exception as erro:
            logger.error(f"Erro inesperado ao chamar Ollama: {erro}")
            return f"Erro ao processar sua pergunta. Por favor, tente novamente."

    async def aquecer(self) -> None:
        """
        Pré-carrega o modelo Ollama na memória para reduzir a latência da primeira consulta.

        Envia um prompt vazio com keep_alive para que o Ollama carregue o modelo
        sem gerar texto. Deve ser chamado como task assíncrona no startup da aplicação.
        """
        try:
            logger.info(f"Aquecendo modelo '{self.modelo}' no Ollama...")
            async with httpx.AsyncClient(timeout=300.0) as cliente:
                await cliente.post(
                    self.url_geracao,
                    json={
                        "model": self.modelo,
                        "prompt": "",
                        "keep_alive": "10m",
                        "stream": False,
                    },
                )
            logger.info(f"Modelo '{self.modelo}' pré-carregado com sucesso.")
        except Exception as erro:
            logger.warning(f"Aquecimento do Ollama falhou (não crítico): {erro}")

    async def verificar_disponibilidade(self) -> bool:
        """
        Verifica se o Ollama está acessível e operacional.

        Returns:
            True se disponível, False caso contrário.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as cliente:
                resposta = await cliente.get(self.url_status)
                return resposta.status_code == 200
        except Exception:
            return False
