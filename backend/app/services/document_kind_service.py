"""
Rótulos para exibição: tipo de documento fiscal vs. referência na declaração IRPF.
"""

import re

_REF_IRPF_POR_CATEGORIA: dict[str, str] = {
    "Recibo Médico": (
        "IRPF — Despesas médicas e com saúde (inclui odontologia): "
        "quadro de pagamentos / deduções legais, conforme instruções do programa."
    ),
    "Nota Fiscal": (
        "IRPF — Depende do conteúdo da nota: saúde, educação, carnê-leão etc. "
        "Lance no quadro correspondente à natureza do pagamento."
    ),
    "Comprovante Educacional": (
        "IRPF — Despesas com educação (ensino regular, dedução legal): "
        "quadro específico de educação no programa da declaração."
    ),
    "Informe de Rendimentos": (
        "IRPF — Rendimentos sujeitos ao tributo exigível ou tributados exclusivamente na fonte: "
        "preencha com base no informe (empregador, banco, etc.)."
    ),
    "Previdência Privada": (
        "IRPF — Previdência oficial e complementar / planos PGBL-VGBL conforme regras da instrução."
    ),
    "Doações": (
        "IRPF — Doações dedutíveis (arts. da lei aplicável): quadro de doações, "
        "sujeito a limites e entidades habilitadas."
    ),
    "Pensão Alimentícia": (
        "IRPF — Pensão alimentícia judicial (e regime de tributação exclusiva na fonte, se couber)."
    ),
    "Aluguel": (
        "IRPF — Aluguéis pagos a pessoa física (carnê-leão do beneficiário) ou deduções cabíveis, "
        "conforme caso e instrução."
    ),
    "Documento Não Classificado": "Revise o documento e escolha a categoria correta antes de lançar no IRPF.",
    "Requer Revisão": "Classifique manualmente para saber em qual quadro do IRPF o comprovante se enquadra.",
}


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
            return (
                "IRPF — Despesas médicas e com saúde: comprovante em nome de titular/dependente, "
                "com CNPJ do prestador (ex.: NFC-e de clínica/odontologia), conforme instrução."
            )
        if _texto_parece_educacao(texto):
            return (
                "IRPF — Despesas com educação: nota ou carnê de instituição habilitada, "
                "no quadro de educação do programa."
            )
        return _REF_IRPF_POR_CATEGORIA["Nota Fiscal"]

    return _REF_IRPF_POR_CATEGORIA.get(
        categoria,
        "Escolha a categoria adequada e confira a instrução do IRPF do ano-calendário.",
    )
