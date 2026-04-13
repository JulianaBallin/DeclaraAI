"""
Gerador de respostas via LLM rodando no Ollama.

Monta o prompt com contexto recuperado e envia ao modelo configurado.
A temperatura baixa (0.3) favorece respostas factuais e conservadoras,
adequadas ao domínio fiscal onde precisão é crítica.
"""

import httpx
from app.core.config import configuracoes
import logging

logger = logging.getLogger(__name__)

PROMPT_SISTEMA = """\
Você é o DeclaraAI, um assistente especializado em imposto de renda para pessoas físicas no Brasil.
Seu objetivo é ajudar usuários leigos a entender o processo de declaração do IRPF de forma clara e acessível.

REGRAS:
- Responda SEMPRE em português brasileiro, de forma clara e direta.
- Baseie sua resposta EXCLUSIVAMENTE no contexto fornecido abaixo.
- Se a resposta não estiver no contexto, diga: "Não encontrei essa informação na minha base de conhecimento."
- Nunca invente valores, datas, alíquotas ou regras fiscais.
- Recomende sempre consultar um contador para casos específicos ou complexos.
- Use listas e tópicos quando a resposta tiver múltiplos itens.

CONTEXTO DA BASE DE CONHECIMENTO:
{contexto}

PERGUNTA DO USUÁRIO:
{pergunta}

RESPOSTA:"""


class GeradorResposta:
    """
    Gera respostas contextualizadas usando LLM via API do Ollama.

    Integra o contexto recuperado pelo retriever ao prompt antes de
    enviar ao modelo de linguagem configurado.
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

        Returns:
            Resposta gerada pelo LLM como string.
        """
        prompt = PROMPT_SISTEMA.format(contexto=contexto, pergunta=pergunta)

        payload = {
            "model": self.modelo,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,   # Conservador para domínio fiscal
                "top_p": 0.9,
                "num_ctx": 4096,      # Janela de contexto
                "num_predict": 1024,  # Limite de tokens na resposta
            },
        }

        try:
            async with httpx.AsyncClient(timeout=180.0) as cliente:
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
