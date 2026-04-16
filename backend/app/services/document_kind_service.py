"""
Rótulos para exibição: tipo de documento fiscal vs. referência na declaração IRPF.
Inclui validade fiscal por tipo e fichas/códigos oficiais da Receita Federal.
"""

import re

# ---------------------------------------------------------------------------
# M3 — Referências às fichas e códigos oficiais do programa IRPF
# Cada entry: texto descritivo com ficha, código e limite quando aplicável
# ---------------------------------------------------------------------------
_REF_IRPF_POR_CATEGORIA: dict[str, dict] = {
    "Recibo Médico": {
        "ficha": "Pagamentos Efetuados",
        "codigo": "09 — Médico (inclusive residente) / 10 — Dentista / "
                  "11 — Psicólogo / 12 — Fisioterapeuta / 13 — Fonoaudiólogo / "
                  "21 — Médico no exterior",
        "dedutivel": True,
        "limite": None,
        "observacao": (
            "Despesas médicas são dedutíveis sem limite de valor. "
            "O documento deve estar em nome do titular ou de dependente incluído na declaração. "
            "Recibos e declarações não têm validade fiscal direta — prefira NF-e ou NFS-e."
        ),
    },
    "Comprovante Educacional": {
        "ficha": "Pagamentos Efetuados",
        "codigo": "01 — Instrução (ensino regular reconhecido pelo MEC)",
        "dedutivel": True,
        "limite": 3561.50,
        "observacao": (
            "Limite anual de R$ 3.561,50 por pessoa (titular ou dependente). "
            "Somente ensino formal reconhecido pelo MEC: educação infantil, fundamental, "
            "médio, superior, técnico reconhecido e pós-graduação stricto sensu. "
            "Cursos livres, idiomas e cursinhos preparatórios NÃO são dedutíveis."
        ),
    },
    "Informe de Rendimentos": {
        "ficha": "Rendimentos Tributáveis Recebidos de PJ / Rendimentos Isentos / "
                 "Rendimentos Tributados Exclusivamente na Fonte",
        "codigo": "N/A — preencher conforme natureza dos rendimentos",
        "dedutivel": False,
        "limite": None,
        "observacao": (
            "Não é dedução — é rendimento a declarar. "
            "Lance os valores nas fichas correspondentes: Rendimentos Tributáveis (empregador, "
            "aluguéis), Isentos (FGTS, herança) ou Tributados Exclusivamente na Fonte (PLR, etc.)."
        ),
    },
    "Nota Fiscal": {
        "ficha": "Pagamentos Efetuados (varia conforme natureza)",
        "codigo": "Conforme natureza: 09–13 (saúde) / 01 (educação) / outros",
        "dedutivel": True,
        "limite": None,
        "observacao": (
            "A dedutibilidade depende do conteúdo da nota. "
            "NF-e, NFC-e e NFS-e possuem chave de acesso de 44 dígitos consultável no "
            "portal da Receita Federal em https://www.nfe.fazenda.gov.br/portal/consultaRecaptcha.aspx"
        ),
    },
    "Previdência Privada": {
        "ficha": "Pagamentos Efetuados",
        "codigo": "36 — Previdência Privada (PGBL) / VGBL não é dedutível",
        "dedutivel": True,
        "limite": None,  # 12% da renda bruta — calculado dinamicamente
        "observacao": (
            "PGBL (código 36): dedutível até 12% da renda bruta tributável no ano. "
            "VGBL: NÃO dedutível — é tratado como seguro de vida. "
            "Confira o tipo no contrato antes de lançar."
        ),
    },
    "Doações": {
        "ficha": "Doações Efetuadas",
        "codigo": "60 a 80 — conforme entidade e modalidade (ECA, FIA, PRONAC, etc.)",
        "dedutivel": True,
        "limite": None,  # percentual da renda — varia por modalidade
        "observacao": (
            "Doações para entidades habilitadas têm limite percentual sobre o imposto devido. "
            "Apenas doações incentivadas (ex.: Fundo da Criança, PRONAC, Lei Rouanet) são dedutíveis. "
            "Doações a pessoas físicas ou igrejas não são dedutíveis."
        ),
    },
    "Pensão Alimentícia": {
        "ficha": "Pagamentos Efetuados",
        "codigo": "30 — Pensão alimentícia",
        "dedutivel": True,
        "limite": None,
        "observacao": (
            "Dedutível integralmente, mas EXIGE sentença judicial ou escritura pública (acordo homologado). "
            "Pensão paga voluntariamente sem decisão judicial NÃO é dedutível. "
            "Lance o nome e CPF do beneficiário."
        ),
    },
    "Aluguel": {
        "ficha": "Pagamentos Efetuados (aluguel pago) / Rendimentos Tributáveis (aluguel recebido)",
        "codigo": "70 — Aluguéis (pago a PF) / rendimento tributável quando recebido",
        "dedutivel": None,  # depende: pago pode ser custo; recebido é rendimento
        "limite": None,
        "observacao": (
            "ALUGUEL PAGO: pode ser lançado como pagamento quando o locador é PF "
            "(gera obrigação de carnê-leão para o recebedor). "
            "ALUGUEL RECEBIDO: é rendimento tributável, não despesa dedutível — "
            "deve ser declarado na ficha de Rendimentos Tributáveis."
        ),
    },
    "Documento Não Classificado": {
        "ficha": "Indeterminado",
        "codigo": "—",
        "dedutivel": None,
        "limite": None,
        "observacao": "Revise o documento e escolha a categoria correta antes de lançar no IRPF.",
    },
    "Requer Revisão": {
        "ficha": "Indeterminado",
        "codigo": "—",
        "dedutivel": None,
        "limite": None,
        "observacao": "Classifique manualmente para saber em qual quadro do IRPF o comprovante se enquadra.",
    },
}

# ---------------------------------------------------------------------------
# M1 — Tipos de documento com validade fiscal direta (NF-e / NFC-e / NFSe)
# ---------------------------------------------------------------------------
_TIPOS_COM_VALIDADE_FISCAL = {
    "NF-e",
    "NFC-e",
    "NFSe",
    "DANFE",
}

_TIPOS_SEM_VALIDADE_FISCAL = {
    "Recibo",
    "Declaração",
    "Holerite",
    "Contracheque",
}


def validade_fiscal_do_tipo(tipo_documento: str) -> bool | None:
    """
    Retorna True se o tipo tem validade fiscal direta (consultável na Receita),
    False se não tem (recibo/declaração), None se indeterminado.
    """
    t = tipo_documento.lower()
    if any(x.lower() in t for x in _TIPOS_COM_VALIDADE_FISCAL):
        return True
    if any(x.lower() in t for x in _TIPOS_SEM_VALIDADE_FISCAL):
        return False
    if "não identificado" in t:
        return None
    return None


def inferir_tipo_documento(texto: str, nome_arquivo: str = "") -> str:
    """Identifica o layout/tipo fiscal mais provável a partir do texto extraído."""
    b = f"{texto}\n{nome_arquivo}".lower()

    if re.search(r"\bnfc[\s-]?e\b", b) or "nota fiscal de consumidor" in b:
        if re.search(r"\bdanfe\b", b):
            return "NFC-e + DANFE (cupom / documento auxiliar)"
        return "NFC-e — Nota Fiscal de Consumidor Eletrônica"
    if re.search(r"\bnf[\s-]?se\b", b) or "nfse" in b or "nfs-e" in b:
        return "NFSe — Nota Fiscal de Serviços Eletrônica"
    if re.search(r"\bnf[\s-]?e\b", b) or re.search(r"\bnfe\b", b):
        return "NF-e — Nota Fiscal Eletrônica (modelo 55)"
    if re.search(r"\bdanfe\b", b) or "documento auxiliar da nota fiscal" in b:
        return "DANFE / documento auxiliar de NF-e ou NFC-e"
    digitos = re.sub(r"\D", "", texto + nome_arquivo)
    if re.search(r"\d{44}", digitos) and "chave" in b:
        return "Documento com chave de acesso (44 dígitos) — típico de NF-e / NFC-e"

    if "informe de rendimentos" in b or "dirf" in b:
        return "Informe de rendimentos / DIRF"
    if "holerite" in b or "contracheque" in b:
        return "Holerite / contracheque"
    if "recibo de aluguel" in b or (re.search(r"\baluguel\b", b) and "locador" in b):
        return "Recibo ou contrato de aluguel"

    if any(
        p in b
        for p in (
            "pensão alimentícia",
            "pensao alimenticia",
            "decisão judicial",
            "acordo judicial",
        )
    ):
        return "Documento de pensão alimentícia / judicial"

    if "recibo" in b and any(x in b for x in ("médico", "medico", "clínica", "clinica", "odontologia")):
        return "Recibo ou comprovante de serviço de saúde (sem layout de NF-e)"

    return "Tipo não identificado automaticamente — verifique o PDF ou a categoria escolhida"


def _texto_parece_saude(texto: str) -> bool:
    t = texto.lower()
    return bool(
        re.search(
            r"(odontolog|clínica|clinica|hospital|médic|medic|dentist|psicolog|fisio|"
            r"laboratório|laboratorio|farmácia|farmacia|procedimento|consulta|saúde|saude)",
            t,
        )
    )


def _texto_parece_educacao(texto: str) -> bool:
    t = texto.lower()
    return bool(
        re.search(
            r"(escola|colégio|colegio|universidade|faculdade|mensalidade|"
            r"matrícula|matricula|ensino|\bmec\b)",
            t,
        )
    )


def referencia_irpf(categoria: str, texto: str = "") -> str:
    """Texto curto ligando a categoria do app ao quadro usual da declaração IRPF."""
    if categoria == "Nota Fiscal":
        if _texto_parece_saude(texto):
            ref = _REF_IRPF_POR_CATEGORIA["Recibo Médico"]
            return (
                f"Ficha: {ref['ficha']} | Código: {ref['codigo']}\n"
                f"{ref['observacao']}"
            )
        if _texto_parece_educacao(texto):
            ref = _REF_IRPF_POR_CATEGORIA["Comprovante Educacional"]
            return (
                f"Ficha: {ref['ficha']} | Código: {ref['codigo']}\n"
                f"Limite: R$ {ref['limite']:,.2f} por pessoa/ano\n"
                f"{ref['observacao']}"
            )

    entry = _REF_IRPF_POR_CATEGORIA.get(categoria)
    if not entry:
        return "Escolha a categoria adequada e confira a instrução do IRPF do ano-calendário."

    partes = [f"Ficha: {entry['ficha']} | Código: {entry['codigo']}"]
    if entry.get("limite"):
        partes.append(f"Limite anual: R$ {entry['limite']:,.2f} por pessoa")
    partes.append(entry["observacao"])
    return "\n".join(partes)


def info_categoria(categoria: str) -> dict:
    """Retorna o dicionário completo de informações da categoria para uso interno."""
    return _REF_IRPF_POR_CATEGORIA.get(
        categoria,
        _REF_IRPF_POR_CATEGORIA["Documento Não Classificado"],
    )
