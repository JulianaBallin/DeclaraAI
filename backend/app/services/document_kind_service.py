"""
Rótulos para exibição: tipo de documento fiscal vs. referência na declaração IRPF.
Inclui validade fiscal por tipo, fichas/códigos oficiais da Receita Federal e
avaliação de dedutibilidade pelo conteúdo do documento.
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


# ---------------------------------------------------------------------------
# Avaliação de dedutibilidade pelo conteúdo do documento
# ---------------------------------------------------------------------------

# Cada entrada: (padrões de detecção, mensagem de aviso, exceções que tornam dedutível)
_PADROES_NAO_DEDUTIVEIS: list[tuple[list[str], str, list[str]]] = [
    (
        ["roupa", "vestuário", "vestuario", "calçado", "calcado", "tênis", "tenis",
         "camisa", "calça", "calca", "vestido", "saia", "blusa", "camiseta",
         "sapato", "sandália", "sandalia", "moda", "confecção", "confeccao",
         "renner", "riachuelo", "c&a ", " cea ", "marisa", "zara", "hering",
         "track&field", "lupo", "reserva", "osklen", "animale", "shoulder",
         "loja de roupas", "loja de calçados", "boutique"],
        "Roupas e calçados NÃO são dedutíveis no IRPF, independentemente do valor ou finalidade.",
        [],
    ),
    (
        ["smartphone", "celular", "iphone", "notebook", "computador", "tablet",
         "televisão", "televisao", "tv ", " tv\n", "monitor", "eletrodoméstico",
         "eletrodomestico", "geladeira", "fogão", "fogao", "máquina de lavar",
         "lava-louças", "ar condicionado", "aspirador", "liquidificador",
         "americanas", "magazine luiza", "magalu", "casas bahia", "fast shop",
         "kabum", "ponto frio", "extra.com"],
        "Eletrônicos e eletrodomésticos NÃO são dedutíveis no IRPF.",
        [],
    ),
    (
        ["supermercado", "hipermercado", "mercado", "mercearia", "hortifruti",
         "açougue", "padaria", "pão de açúcar", "carrefour", "extra ", "walmart",
         "assaí", "atacadão", "comper", "savegnago", "send", "super muffato",
         "condor", "rede mais", "mercadinhos são luiz"],
        (
            "Compras de supermercado e alimentos NÃO são dedutíveis no IRPF. "
            "Exceto alimentos incluídos em conta hospitalar de internação."
        ),
        ["internação", "conta hospitalar", "hospital", "dieta enteral", "nutrição parenteral"],
    ),
    (
        ["combustível", "combustivel", "gasolina", "etanol", "diesel", "gnv",
         "posto de combustível", "posto ipiranga", "posto shell", "posto petrobras",
         "posto br", "ale combustíveis", "raízen"],
        "Combustível NÃO é dedutível no IRPF para pessoa física.",
        [],
    ),
    (
        ["restaurante", "lanchonete", "pizzaria", "hamburger", "hambúrguer",
         "churrascaria", "sushi", "delivery", "ifood", "uber eats", "rappi",
         "mcdonalds", "mc donalds", "burguer king", "bob's", "subway",
         "refeição", "almoço", "jantar", "café da manhã", "bar e restaurante"],
        (
            "Alimentação em restaurantes NÃO é dedutível no IRPF. "
            "Apenas alimentação prescrita como parte de tratamento hospitalar é dedutível."
        ),
        ["internação", "dieta hospitalar", "nutrição clínica"],
    ),
    (
        ["perfume", "cosmético", "cosmetico", "maquiagem", "batom", "base",
         "creme facial", "creme corporal", "shampoo", "condicionador", "tintura",
         "salão de beleza", "cabeleireiro", "manicure", "pedicure", "depilação",
         "o boticário", "natura ", "avon ", "vult", "quem disse berenice",
         "mac cosméticos", "sephora", "beauty", "perfumaria"],
        "Cosméticos, perfumes e serviços de beleza NÃO são dedutíveis no IRPF.",
        [],
    ),
    (
        ["academia", "ginástica", "musculação", "musculacao", "crossfit",
         "pilates", "yoga", "spinning", "smartfit", "bodytech", "bio ritmo",
         "runner", "cia athletica", "swim", "natação", "natacao", "futebol",
         "tênis esportivo", "clube esportivo", "mensalidade academia"],
        (
            "Academia e atividades físicas NÃO são dedutíveis como despesa médica no IRPF. "
            "Exceção: se prescrita por médico como tratamento de saúde, com laudo e CID, "
            "pode ser dedutível — consulte um contador."
        ),
        ["prescrição médica", "prescricao medica", "laudo médico", "fisioterapia", "reabilitação"],
    ),
    (
        ["curso de inglês", "curso de ingles", "curso de espanhol",
         "curso de francês", "curso de frances", "curso de alemão", "curso de alemao",
         "curso de mandarim", "curso de japonês", "curso de japonês",
         "curso livre", "curso profissionalizante",
         "speak up", "wizard", "fisk", "ccaa", "cultura inglesa",
         "yázigi", "yazigi", "skill idiomas", "english", "english school"],
        (
            "Cursos de idiomas e cursos livres NÃO são dedutíveis no IRPF. "
            "Apenas cursos com reconhecimento MEC são dedutíveis (ensino fundamental, "
            "médio, superior, técnico reconhecido pelo MEC e pós-graduação stricto sensu)."
        ),
        [],
    ),
    (
        ["farmácia", "farmacia", "drogaria", "drogasil", "raia drogasil",
         "ultrafarma", "panvel", "droga raia", "pacheco", "pague menos",
         "farmácias associadas", "medicamento", "remédio", "remedio",
         "comprimido", "cápsula", "capsula", "xarope", "pomada", "antibiótico",
         "antibiotic", "vitamina", "suplemento alimentar"],
        (
            "Medicamentos adquiridos em farmácia NÃO são dedutíveis no IRPF. "
            "A única exceção é quando o medicamento está incluído na conta emitida pelo "
            "hospital durante uma internação. Guarde o documento, mas não lance como dedução."
        ),
        ["internação", "conta hospitalar", "hospital", "clínica de internação"],
    ),
    (
        ["pet shop", "veterinário", "veterinario", "petco", "petz", "cobasi",
         "ração", "racao", "banho e tosa", "plano pet"],
        "Gastos com animais de estimação NÃO são dedutíveis no IRPF.",
        [],
    ),
    (
        ["vgbl", "vida gerador de benefício"],
        (
            "VGBL NÃO é dedutível no IRPF — é tratado como seguro de vida. "
            "Apenas PGBL (código 36) é dedutível, até 12% da renda bruta tributável."
        ),
        [],
    ),
]


def avaliar_dedutibilidade_conteudo(texto: str, categoria: str) -> dict:
    """
    Avalia se o conteúdo do documento é dedutível no IRPF detectando
    padrões de gastos sabidamente não dedutíveis.

    Complementa a classificação por categoria: um documento classificado como
    'Nota Fiscal' pode conter roupas (não dedutível) ou serviços médicos (dedutível).
    A categoria por si só não garante dedutibilidade — o conteúdo decide.

    Args:
        texto: Texto extraído do documento.
        categoria: Categoria tributária atribuída pelo classificador.

    Returns:
        Dicionário com:
            - dedutivel (bool|None): False = não dedutível; None = inconclusivo
            - aviso (str|None): mensagem explicativa ao usuário
            - nivel (str): "erro" (certamente não dedutível) | "aviso" | "ok"
    """
    t = texto.lower()

    for padroes, mensagem, excecoes in _PADROES_NAO_DEDUTIVEIS:
        if any(p in t for p in padroes):
            # Verifica se há exceção que torna o documento dedutível
            if excecoes and any(e in t for e in excecoes):
                continue
            return {
                "dedutivel": False,
                "aviso": mensagem,
                "nivel": "erro",
            }

    # Verificação adicional: doação para pessoa física ou entidade não habilitada
    if categoria == "Doações":
        if re.search(r"\b(cpf|pessoa física|amigo|familiar|vizinho|igreja|templo|culto)\b", t):
            return {
                "dedutivel": False,
                "aviso": (
                    "Doações a pessoas físicas, igrejas ou entidades não habilitadas pelo governo "
                    "NÃO são dedutíveis no IRPF. Somente doações para fundos oficiais (ECA, FIA, "
                    "PRONAC, Fundo do Idoso etc.) são dedutíveis."
                ),
                "nivel": "aviso",
            }

    # Verificação: pensão alimentícia sem decisão judicial
    if categoria == "Pensão Alimentícia":
        tem_judicial = any(
            p in t for p in [
                "decisão judicial", "decisao judicial", "sentença", "sentenca",
                "processo", "acordo judicial", "escritura pública", "escritura publica",
                "homologado", "vara de família", "vara de familia",
            ]
        )
        if not tem_judicial:
            return {
                "dedutivel": None,
                "aviso": (
                    "Atenção: não foi detectada referência a decisão judicial ou escritura pública. "
                    "Pensão paga voluntariamente sem decisão judicial NÃO é dedutível no IRPF. "
                    "Confirme se existe sentença ou escritura antes de lançar."
                ),
                "nivel": "aviso",
            }

    return {"dedutivel": None, "aviso": None, "nivel": "ok"}
