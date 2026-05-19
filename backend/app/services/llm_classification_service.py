"""
Classificação LLM-first de documentos fiscais.

Arquitetura:
    1. LLM (primário)  — chama Ollama com prompt estruturado, retorna JSON.
    2. Regras (fallback) — aciona ServicoClassificacao apenas se o LLM falhar
       ou retornar JSON inválido/categoria desconhecida.
    3. "Requer Revisão" — último recurso quando ambos são inconclusivos.

O campo `origem` no resultado rastreia qual caminho foi usado:
    "llm"             → LLM classificou com sucesso
    "fallback_regras" → regras foram acionadas (LLM falhou)
    "nao_classificado" → nenhum método conseguiu classificar
"""

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import configuracoes
from app.services.classification_service import (
    CATEGORIAS_VALIDAS,
    CATEGORIA_PADRAO,
    CATEGORIA_REVISAO,
    ServicoClassificacao,
)

logger = logging.getLogger(__name__)

PROMPT_CLASSIFICACAO_LLM = """\
Você é um classificador especialista em documentos fiscais brasileiros para o sistema DeclaraAI.

Analise o texto do documento abaixo e classifique em EXATAMENTE UMA das categorias:
- Recibo Médico
- Comprovante Educacional
- Informe de Rendimentos
- Nota Fiscal
- Previdência Privada
- Doações
- Pensão Alimentícia
- Aluguel
- Documento Não Classificado

REGRAS OBRIGATÓRIAS:
1. Responda APENAS com JSON válido. Nenhum texto antes ou depois do JSON.
2. O campo "confianca" deve ser exatamente: "alta", "media" ou "baixa".
3. O campo "motivo" deve ser uma frase curta (máx 15 palavras).
4. Se não conseguir classificar com segurança, use "Documento Não Classificado".
5. Não invente categorias fora da lista acima.
6. DANFE, NFC-e, NF-e ou chave de acesso (44 dígitos) indicam "Nota Fiscal".
7. "informe de rendimentos", "DIRF", "IRRF", "holerite" indicam "Informe de Rendimentos".
8. "PGBL", "previdência privada" indicam "Previdência Privada".
9. "pensão alimentícia", "alimentando", "decisão judicial" indicam "Pensão Alimentícia".
10. "aluguel", "locatário", "locador" indicam "Aluguel".

Formato obrigatório de resposta:
{{"categoria": "Nome Exato da Categoria", "confianca": "alta", "motivo": "Justificativa breve."}}

TEXTO DO DOCUMENTO:
{texto}

RESPOSTA JSON:"""


@dataclass
class ResultadoClassificacao:
    categoria: str
    confianca: str
    motivo: str
    origem: str
    latencia_ms: float = 0.0
    tentativas_llm: int = 0


class ServicoClassificacaoLLM:
    """
    Classificador LLM-first com fallback para regras.

    Uso:
        servico = ServicoClassificacaoLLM()
        resultado = servico.classificar("texto do documento", "nome_arquivo.pdf")
        print(resultado.categoria, resultado.origem, resultado.latencia_ms)
    """

    def __init__(self) -> None:
        self._fallback = ServicoClassificacao()

    def classificar(self, texto: str, nome_arquivo: str = "") -> ResultadoClassificacao:
        if not texto and not nome_arquivo:
            return ResultadoClassificacao(
                categoria=CATEGORIA_PADRAO,
                confianca="baixa",
                motivo="Nenhum texto fornecido.",
                origem="nao_classificado",
            )

        resultado_llm = self._classificar_com_llm(texto)
        if resultado_llm is not None:
            return resultado_llm

        logger.info("LLM falhou → acionando fallback por regras.")
        categoria_regras, confianca_regras = self._fallback.classificar_com_confianca(
            texto, nome_arquivo
        )

        if categoria_regras != CATEGORIA_REVISAO:
            logger.info(
                "Fallback regras: '%s' | %s", categoria_regras, confianca_regras
            )
            return ResultadoClassificacao(
                categoria=categoria_regras,
                confianca=confianca_regras,
                motivo="Classificado por regras após falha do LLM.",
                origem="fallback_regras",
            )

        logger.warning("Nenhum método classificou o documento → Requer Revisão.")
        return ResultadoClassificacao(
            categoria=CATEGORIA_REVISAO,
            confianca="baixa",
            motivo="Nenhum método conseguiu classificar com segurança.",
            origem="nao_classificado",
        )

    def classificar_compativel(self, texto: str, nome_arquivo: str = "") -> tuple[str, str]:
        resultado = self.classificar(texto, nome_arquivo)
        return resultado.categoria, resultado.confianca

    def _classificar_com_llm(
        self,
        texto: str,
        max_tentativas: int = 2,
    ) -> Optional[ResultadoClassificacao]:
        texto_limitado = texto[:3000] if len(texto) > 3000 else texto

        for tentativa in range(1, max_tentativas + 1):
            prompt = PROMPT_CLASSIFICACAO_LLM.format(texto=texto_limitado)
            if tentativa == 2:
                prompt = "Responda APENAS com JSON, sem explicações:\n" + prompt

            payload = {
                "model": configuracoes.OLLAMA_MODELO,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "top_p": 0.85,
                    "num_ctx": 4096,
                    "num_predict": 200,
                },
            }

            inicio = time.perf_counter()
            try:
                url = f"{configuracoes.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
                resposta = httpx.post(url, json=payload, timeout=60.0)
                resposta.raise_for_status()
                latencia_ms = (time.perf_counter() - inicio) * 1000

                texto_resposta = resposta.json().get("response", "").strip()
                resultado = self._parsear_resposta(texto_resposta, latencia_ms, tentativa)
                if resultado is not None:
                    return resultado

                logger.warning(
                    "Tentativa %d/%d: JSON inválido ou categoria desconhecida.",
                    tentativa,
                    max_tentativas,
                )

            except httpx.ConnectError:
                logger.warning("Tentativa %d: Ollama indisponível (conexão).", tentativa)
                return None
            except httpx.TimeoutException:
                logger.warning("Tentativa %d: timeout ao chamar Ollama.", tentativa)
            except httpx.HTTPStatusError as e:
                logger.warning(
                    "Tentativa %d: Ollama HTTP %s", tentativa, e.response.status_code
                )
                return None
            except Exception as e:
                logger.error("Tentativa %d: erro inesperado — %s", tentativa, e, exc_info=True)

        return None

    def _parsear_resposta(
        self,
        texto_resposta: str,
        latencia_ms: float,
        tentativas: int,
    ) -> Optional[ResultadoClassificacao]:
        texto_limpo = re.sub(r"```json|```", "", texto_resposta).strip()
        match = re.search(r"\{.*\}", texto_limpo, re.DOTALL)
        if not match:
            return None

        try:
            dados = json.loads(match.group())
        except json.JSONDecodeError:
            return None

        categoria = str(dados.get("categoria", "")).strip()
        confianca = str(dados.get("confianca", "baixa")).strip()
        motivo = str(dados.get("motivo", "")).strip()

        if categoria not in CATEGORIAS_VALIDAS:
            logger.warning("LLM retornou categoria inválida: '%s'", categoria)
            return None

        if confianca not in ("alta", "media", "baixa"):
            confianca = "media"

        logger.info(
            "LLM: '%s' | confianca=%s | latencia=%.0fms | tentativas=%d",
            categoria,
            confianca,
            latencia_ms,
            tentativas,
        )
        return ResultadoClassificacao(
            categoria=categoria,
            confianca=confianca,
            motivo=motivo,
            origem="llm",
            latencia_ms=latencia_ms,
            tentativas_llm=tentativas,
        )
