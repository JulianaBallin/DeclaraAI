"""
Classificação híbrida: regras (score + margem) → LLM (JSON) → Requer Revisão.
"""

import json
import logging
import re
from typing import Optional

import httpx

from app.core.config import configuracoes
from app.services.document_kind_service import texto_eh_recibo_aluguel

logger = logging.getLogger(__name__)

LIMIAR_SCORE: float = 4.0
MARGEM_MINIMA: float = 2.0
# Quando DANFE/NFC-e/etc. estão presentes, “Recibo Médico” não deve ganhar só por termos de saúde.
BONUS_NOTA_FISCAL_DFE: float = 4.0


def _evidencia_nfse(texto: str, nome_arquivo: str) -> bool:
    b = f"{texto} {nome_arquivo}".lower()
    return bool(
        re.search(r"nota\s+fiscal\s+de\s+servi[çc]os\s+eletr", b)
        or re.search(r"\bnfs[\s.-]*e\b", b)
        or re.search(r"\bnfse\b", b)
    )


CATEGORIAS_TRIBUTARIAS: dict[str, dict] = {
    "Recibo Médico": {
        "palavras": [
            "médico", "médica", "consulta", "clínica", "hospital", "saúde",
            "dentista", "odontológico", "odontologia", "odontoclínica",
            "procedimento odontológico", "tratamento odontológico",
            "psicólogo", "psiquiatra", "fisioterapia", "fisioterapeuta",
            "fonoaudiólogo", "terapia ocupacional", "terapia", "exame",
            "laboratório", "farmácia", "medicamento", "remédio",
            "plano de saúde", "cirurgia", "internação", "prontuário",
            "receita médica", "nutricionista", "psicopedagogo",
            "oftalmologia", "cardiologia", "ortopedia", "dermatologia",
            "ginecologia", "pediatria", "anestesia", "radiologia",
            "ressonância", "tomografia", "ultrassom", "colonoscopia",
            "endoscopia", "hemograma",
            "CRM", "CRO", "CRP", "CRF", "CREFITO",
            "infinity odontologia", "odontologia ltda",
        ],
        "peso": 2.0,
    },
    "Comprovante Educacional": {
        "palavras": [
            "escola", "colégio", "universidade", "faculdade", "mensalidade",
            "matrícula", "educação", "ensino", "curso", "aula", "professor",
            "aluno", "semestre", "graduação", "pós-graduação", "pós graduação",
            "MEC", "vestibular", "ENEM", "bolsa", "pedagógico", "creche",
            "pré-escola", "técnico", "tecnológico", "especialização",
            "IFAM", "UEA", "UFAM", "ensino médio", "ensino fundamental",
        ],
        "peso": 2.0,
    },
    "Informe de Rendimentos": {
        "palavras": [
            "informe de rendimentos", "rendimentos", "salário", "remuneração",
            "empregador", "INSS", "IRRF", "imposto retido", "imposto de renda retido",
            "décimo terceiro", "13º salário", "férias", "rescisão", "CLT",
            "holerite", "contracheque", "rendimento tributável", "rendimento isento",
            "comprovante de rendimentos", "DIRF", "declaração anual",
        ],
        "peso": 2.0,
    },
    "Nota Fiscal": {
        "palavras": [
            "nota fiscal",
            "NF-e",
            "NFC-e",
            "NF-Se",
            "NFe",
            "DANFE",
            "chave de acesso",
            "valor dos serviços",
            "protocolo de autorização",
            "ICMS",
            "IPI",
            "ISS",
            "produto",
            "produtos",
            "mercadoria",
            "compra",
            "venda",
            "série",
            "número NF",
            "emissão fiscal",
            "SEFAZ",
            "supermercado",
            "restaurante",
            "loja",
            "comércio",
        ],
        "peso": 1.0,
    },
    "Previdência Privada": {
        "palavras": [
            "previdência privada", "PGBL", "VGBL", "fundo de pensão",
            "contribuição previdenciária", "plano de previdência",
            "previdência complementar", "pecúlio",
        ],
        "peso": 2.0,
    },
    "Doações": {
        "palavras": [
            "doação", "donatário", "recibo de doação", "ONG", "entidade",
            "filantropia", "beneficente", "sem fins lucrativos", "associação",
            "fundação", "doador",
        ],
        "peso": 1.5,
    },
    "Pensão Alimentícia": {
        "palavras": [
            "pensão alimentícia", "alimentos", "pensionista", "decisão judicial",
            "acordo judicial", "alimentando", "pensão", "guarda",
        ],
        "peso": 2.0,
    },
    "Aluguel": {
        "palavras": [
            "aluguel", "locação", "locatário", "locador", "imóvel", "contrato",
            "recibo de aluguel", "arrendamento", "IPTU", "condomínio",
        ],
        "peso": 1.5,
    },
}

CATEGORIA_PADRAO = "Documento Não Classificado"
CATEGORIA_REVISAO = "Requer Revisão"
CATEGORIAS_VALIDAS = set(CATEGORIAS_TRIBUTARIAS.keys()) | {CATEGORIA_PADRAO}

PROMPT_CLASSIFICACAO = """\
Você é um classificador de documentos fiscais brasileiros para o sistema DeclaraAI.

Analise o texto do documento abaixo e classifique em UMA das categorias:
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
1. Responda APENAS com JSON válido. Nenhum texto antes ou depois.
2. O campo "confianca" deve ser exatamente: "alta", "media" ou "baixa".
3. O campo "motivo" deve ser uma frase curta (máx 15 palavras).
4. Se não conseguir classificar com segurança, use "Documento Não Classificado".
5. Não invente categorias fora da lista acima.
6. DANFE, NFC-e, NF-e ou chave de acesso (44 dígitos) indicam Nota Fiscal, inclusive de clínica ou odontologia.

Formato obrigatório:
{{"categoria": "Nome Exato da Categoria", "confianca": "alta", "motivo": "Justificativa breve."}}

TEXTO DO DOCUMENTO:
{texto}

RESPOSTA JSON:"""


class ServicoClassificacao:
    def _documento_fiscal_eletronico_evidente(self, texto: str, nome_arquivo: str) -> bool:
        """True se o texto é claramente NF-e/NFC-e (DANFE, chave, etc.)."""
        if texto_eh_recibo_aluguel(f"{texto}\n{nome_arquivo}"):
            return False
        blob = f"{texto}\n{nome_arquivo}"
        t = blob.lower()
        if re.search(r"\bdanfe\b", t):
            return True
        if re.search(r"\bnfc[\s-]?e\b", t):
            return True
        if re.search(r"\bnf[\s-]?se\b", t):
            return True
        if re.search(r"\bnf[\s-]?e\b", t):
            return True
        if re.search(r"\bnfe\b", t):
            return True
        if "documento auxiliar da nota fiscal" in t:
            return True
        if "nota fiscal de consumidor" in t:
            return True
        if "nota fiscal eletrônica" in t:
            return True
        digitos = re.sub(r"\D", "", blob)
        if not re.search(
            r"chave\s+(de\s+)?acesso|danfe|nf-?e|nfce|nfs-?e|nfe|nota\s+fiscal", t,
        ):
            return False
        return bool(re.search(r"\d{44}", digitos))

    def _calcular_pontuacoes(self, texto: str, nome_arquivo: str) -> dict[str, float]:
        texto_analise = f"{texto} {nome_arquivo}".lower()
        pontuacoes: dict[str, float] = {}
        for categoria, config in CATEGORIAS_TRIBUTARIAS.items():
            pontuacao = sum(
                config["peso"]
                for palavra in config["palavras"]
                if re.search(rf"\b{re.escape(palavra.lower())}\b", texto_analise)
            )
            if pontuacao > 0:
                pontuacoes[categoria] = pontuacao
        return pontuacoes

    def _avaliar_regras(self, pontuacoes: dict[str, float]) -> Optional[str]:
        if not pontuacoes:
            logger.info("Regras: sem palavras-chave → fallback LLM.")
            return None

        scores_ordenados = sorted(pontuacoes.values(), reverse=True)
        score_max = scores_ordenados[0]
        categoria_vencedora = max(pontuacoes, key=pontuacoes.get)

        if score_max < LIMIAR_SCORE:
            logger.info(
                "Regras: score %.1f < limiar %.1f → fallback LLM.",
                score_max,
                LIMIAR_SCORE,
            )
            return None

        if len(scores_ordenados) >= 2:
            diferenca = score_max - scores_ordenados[1]
            if diferenca < MARGEM_MINIMA:
                logger.info(
                    "Regras: diferença %.1f entre '%s' (%.1f) e 2º (%.1f) < margem %.1f → LLM.",
                    diferenca,
                    categoria_vencedora,
                    score_max,
                    scores_ordenados[1],
                    MARGEM_MINIMA,
                )
                return None

        segundo = scores_ordenados[1] if len(scores_ordenados) >= 2 else 0.0
        logger.info(
            "Regras aceitas: '%s' score=%.1f margem=%.1f",
            categoria_vencedora,
            score_max,
            score_max - segundo,
        )
        return categoria_vencedora

    def _classificar_com_llm(self, texto: str) -> tuple[Optional[str], str]:
        """Retorna (categoria, confianca). confianca pode ser 'alta', 'media', 'baixa' ou 'desconhecida'."""
        texto_limitado = texto[:3000] if len(texto) > 3000 else texto
        prompt = PROMPT_CLASSIFICACAO.format(texto=texto_limitado)

        payload = {
            "model": configuracoes.OLLAMA_MODELO,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.85,
                "num_ctx": 4096,
                "num_predict": 200,
            },
        }

        try:
            url = f"{configuracoes.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
            resposta = httpx.post(url, json=payload, timeout=60.0)
            resposta.raise_for_status()
            texto_resposta = resposta.json().get("response", "").strip()
            texto_resposta = re.sub(r"```json|```", "", texto_resposta).strip()

            match = re.search(r"\{.*\}", texto_resposta, re.DOTALL)
            if match:
                texto_resposta = match.group()

            dados = json.loads(texto_resposta)
            categoria = str(dados.get("categoria", "")).strip()
            confianca = str(dados.get("confianca", "desconhecida")).strip()
            motivo = str(dados.get("motivo", "")).strip()

            if categoria not in CATEGORIAS_VALIDAS:
                logger.warning("LLM categoria inválida: '%s'", categoria)
                return None, "baixa"

            logger.info("LLM: '%s' | %s | %s", categoria, confianca, motivo)
            return categoria, confianca

        except json.JSONDecodeError as e:
            logger.warning("LLM JSON inválido: %s", e)
            return None, "baixa"
        except httpx.ConnectError:
            logger.warning("Ollama indisponível (conexão).")
            return None, "baixa"
        except httpx.TimeoutException:
            logger.warning("Timeout ao chamar Ollama.")
            return None, "baixa"
        except httpx.HTTPStatusError as e:
            logger.warning("Ollama HTTP %s", e.response.status_code)
            return None, "baixa"
        except Exception as e:
            logger.error("Erro ao chamar LLM: %s", e, exc_info=True)
            return None, "baixa"

    def classificar(self, texto: str, nome_arquivo: str = "") -> str:
        """Mantido por compatibilidade — retorna apenas a categoria."""
        categoria, _ = self.classificar_com_confianca(texto, nome_arquivo)
        return categoria

    def classificar_com_confianca(self, texto: str, nome_arquivo: str = "") -> tuple[str, str]:
        """Retorna (categoria, confianca). confianca: 'alta' | 'media' | 'baixa'."""
        if not texto and not nome_arquivo:
            return CATEGORIA_PADRAO, "baixa"

        if texto_eh_recibo_aluguel(f"{texto}\n{nome_arquivo}"):
            logger.info("Recibo de aluguel detectado → categoria 'Aluguel' (alta).")
            return "Aluguel", "alta"

        if _evidencia_nfse(texto, nome_arquivo):
            logger.info("NFS-e detectada no texto → categoria 'Nota Fiscal' com confiança alta.")
            return "Nota Fiscal", "alta"

        pontuacoes = self._calcular_pontuacoes(texto, nome_arquivo)
        if self._documento_fiscal_eletronico_evidente(texto, nome_arquivo):
            pontuacoes.pop("Recibo Médico", None)
            pontuacoes.pop("Comprovante Educacional", None)
            nf = pontuacoes.get("Nota Fiscal", 0.0) + BONUS_NOTA_FISCAL_DFE
            pontuacoes["Nota Fiscal"] = max(nf, LIMIAR_SCORE)
            logger.info("Prioridade DFE: fora de competição recibo/ensino; reforço em Nota Fiscal.")

        categoria_regras = self._avaliar_regras(pontuacoes)
        if categoria_regras is not None:
            scores = sorted(pontuacoes.values(), reverse=True)
            margem = (scores[0] - scores[1]) if len(scores) >= 2 else scores[0]
            confianca = "alta" if margem >= 4.0 else "media"
            logger.info("Classificação final (regras): '%s' | %s", categoria_regras, confianca)
            return categoria_regras, confianca

        logger.info("Acionando fallback LLM…")
        categoria_llm, confianca_llm = self._classificar_com_llm(texto)
        if categoria_llm is not None:
            logger.info("Classificação final (LLM): '%s' | %s", categoria_llm, confianca_llm)
            return categoria_llm, confianca_llm

        logger.warning("Inconclusivo. Pontuações: %s → Requer Revisão.", pontuacoes)
        return CATEGORIA_REVISAO, "baixa"

    def listar_categorias(self) -> list[str]:
        return list(CATEGORIAS_TRIBUTARIAS.keys()) + [CATEGORIA_PADRAO, CATEGORIA_REVISAO]
