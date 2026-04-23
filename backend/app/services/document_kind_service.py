"""
Rótulos para exibição: tipo de documento fiscal vs. referência na declaração IRPF.
Inclui validade fiscal por tipo, fichas/códigos oficiais da Receita Federal e
avaliação de dedutibilidade pelo conteúdo do documento.
"""

import re


def _formatar_reais_br(valor: float) -> str:
    s = f"{abs(valor):.2f}"
    p_int, _, dec = s.partition(".")
    b = []
    for i, c in enumerate(p_int[::-1]):
        if i and i % 3 == 0:
            b.append(".")
        b.append(c)
    num = "".join(reversed(b))
    if valor < 0:
        num = f"-{num}"
    return f"R$ {num},{dec}"


def texto_eh_recibo_pensao_alimenticia(texto: str) -> bool:
    t = (texto or "")[:25000].lower()
    if not t.strip():
        return False
    if re.search(r"recibo\s+de\s+pens", t) and re.search(
        r"aliment|judicial|vara|processo|senten",
        t,
    ):
        return True
    return bool(
        re.search(r"pens[aã]o\s+aliment", t)
        and re.search(
            r"alimentante|alimentando|representante\s+legal|"
            r"recebedor|decis[aã]o|senten[çc]a|vara|processo",
            t,
        )
    )


def texto_eh_recibo_aluguel(texto: str) -> bool:
    """Recibo de locação: não tratar como NF-e nem usar chave 44 solta no texto."""
    t = (texto or "")[:25000].lower()
    if re.search(r"recibo\s+de\s+aluguel|recibo\s+.*\baluguel\b", t):
        return True
    return bool(
        re.search(r"\brecibo\b", t)
        and re.search(
            r"\b(aluguel|loca[çc][aã]o|locat[áa]rio|locat[aá]rio|locador|locadora|im[oó]vel|inquilino)\b",
            t,
        )
    )


def texto_recibo_comprovante_que_nao_e_nfs_e(texto: str) -> bool:
    """
    Recibo/comprovante cujo rodapé ou título nega tratar-se de nota (NFS-e) emitida
    em prefeitura, ou título de consulta médica — evita falso 'NFS-e' por menção '(NFS-e)'.
    """
    t = (texto or "")[:20000].lower()
    if not re.search(r"\brecibo\b", t):
        return False
    if texto_eh_recibo_pensao_alimenticia(texto):
        return False
    if re.search(
        r"n[ãa]o\s+substitui.{0,200}(?:nfs-?e|nfe|nf-?e|nota\s+fiscal)",
        t,
    ):
        return True
    if re.search(
        r"recibo\s+de\s+consulta\s+m[ée]dica|recibo\s+de\s+procedimento",
        t,
    ) and re.search(
        r"crm|cardiolog|m[ée]dico|cl[íi]nica|odont|consulta",
        t,
    ):
        return True
    if re.search(r"recebi\s+do\(?a\)?\s+sr\(?a\)?\s*\.|recebemos\s+de", t) and re.search(
        r"crm|cardiolog|m[ée]dico|consulta\s+m[ée]dica|cl[íi]nica",
        t,
    ):
        return True
    if re.search(r"comprova(?:r)?\s+pagamento", t) and re.search(
        r"irpf|dedu[çc][aã]o|crm|consulta\s+m[ée]dica",
        t,
    ):
        return True
    return False


def _texto_eh_informe_rendimentos(texto: str) -> bool:
    t = texto[:15000].lower()
    if not re.search(
        r"informe\s+de\s+rendimentos|dirf\b|informe\s+anual|comprovante\s+de\s+rendimentos",
        t,
    ):
        return False
    return bool(
        re.search(
            r"rendimentos\s+tribut|fonte\s+pagadora|irrf|inss|retid|"
            r"empregad|v[ií]nculo|clt|sal[áa]rios|ordenad",
            t,
        )
    )


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
    "NFS-e",
    "DANFE",
}

_TIPOS_SEM_VALIDADE_FISCAL = {
    "Recibo",
    "Comprovante",
    "Declaração",
    "Holerite",
    "Contracheque",
}


def ajustar_categoria_irpf_por_tipo_documento(
    tipo_resumido: str,
    categoria_sugerida: str,
    texto: str = "",
) -> str:
    """
    Alinha a categoria interna (quadros de referência) ao formato do documento.
    Recibo simples não deve ser agrupado como "Nota Fiscal".
    """
    tl = (texto or "")[:20000].lower()
    if tipo_resumido in (
        "Recibo de pagamento",
        "Recibo",
        "Comprovante",
    ):
        if categoria_sugerida == "Aluguel":
            return "Aluguel"
        if categoria_sugerida == "Pensão Alimentícia" or (
            re.search(r"recibo\s+de\s+pens|pens[aã]o\s+aliment", tl)
            and re.search(
                r"alimentante|alimentando|senten[çc]a|processo|vara|judicial|representante",
                tl,
            )
        ):
            return "Pensão Alimentícia"
        if categoria_sugerida == "Previdência Privada" or _texto_parece_previdencia_pgbl(
            texto
        ):
            return "Previdência Privada"
        return "Documento Não Classificado"
    if tipo_resumido in ("NFS-e", "NFC-e", "NF-e") or (
        tipo_resumido
        and (
            tipo_resumido.startswith("NF-e")
            or tipo_resumido.startswith("NFC-e")
            or tipo_resumido.startswith("NFS-e")
        )
    ):
        return "Nota Fiscal"
    if "informe" in (tipo_resumido or "").lower() and "rendimento" in (
        tipo_resumido or ""
    ).lower():
        return "Informe de Rendimentos"
    return categoria_sugerida


def texto_declara_ficticio_ou_teste_sem_validade_fiscal(texto: str) -> bool:
    t = (texto or "").lower()
    if re.search(r"documento\s+fict[ií]cio", t):
        return True
    if re.search(
        r"fins?\s+de\s+teste|teste\s+de\s+sistema|apenas\s+para\s+teste", t
    ) and re.search(
        r"sem\s+validade\s+fiscal|n[aã]o\s+tem\s+validade", t,
    ):
        return True
    if re.search(r"n[aã]o\s+tem\s+validade\s+fiscal", t) and re.search(
        r"teste|fict|simul", t,
    ):
        return True
    return False


def legenda_validade_fiscal(
    validade: bool | None,
    tipo_documento: str = "",
    texto: str = "",
) -> str:
    if texto and texto_declara_ficticio_ou_teste_sem_validade_fiscal(texto):
        return (
            "O documento indica ser fictício, de teste ou sem validade fiscal perante a "
            "administração tributária. Não substitui NFS-e com valor jurídico."
        )
    t = (tipo_documento or "").lower()
    if validade is True:
        return (
            "Documento com validade fiscal (eletrônico): NF-e, NFC-e ou NFS-e. "
            "Há chave e/ou consulta em órgão fiscal (Receita/prefeitura)."
        )
    if validade is False:
        if (texto or "").strip() and re.search(
            r"n[ãa]o\s+substitui.*nfs-?e",
            (texto or "").lower(),
        ):
            return (
                "Comprovante simples: comprova pagamento e, conforme o texto, **não substitui** "
                "NFS-e / nota de prefeitura. Guarde com o extrato bancário e confira o beneficiário."
            )
        if "informe" in t and "rendimento" in t:
            return (
                "Informe de rendimentos emitido pela fonte pagadora — documento "
                "comprobatório do empregador para preenchimento do IRPF (rendimentos e "
                "retenções/deduções na fonte), sem chave de NF-e."
            )
        if "recibo" in t and "nfe" not in t and "nf-e" not in t:
            return (
                "Comprovante simples — sem chave/validade fiscal eletrônica direta na Receita. "
                "Pode comprovar pagamento, mas não substitui NF-e/NFS-e."
            )
        return (
            "Comprovante simples: sem chave/validade fiscal direta na Receita. "
            "não se confunde com nota eletrônica, mas pode comprovar pagamento."
        )
    return "Não foi possível determinar automaticamente,  veja o original."


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
    if "informe" in t and "rendimento" in t:
        return False
    return None


def inferir_tipo_documento(texto: str, nome_arquivo: str = "") -> str:
    """Identifica o layout/tipo fiscal mais provável a partir do texto extraído."""
    b = f"{texto}\n{nome_arquivo}".lower()
    if texto_eh_recibo_aluguel(texto):
        return "Recibo de aluguel"

    if texto_eh_recibo_pensao_alimenticia(texto):
        return "Recibo de pensão alimentícia (processo / beneficiário — conferir documentação)"

    if texto_recibo_comprovante_que_nao_e_nfs_e(texto):
        if re.search(
            r"consulta\s+m[ée]dica|cardiolog|crm|m[ée]dico|cl[íi]nica",
            b,
        ):
            return "Recibo de consulta médica (não confundir com menção a NFS-e no rodapé)"
        return "Recibo ou comprovante de serviço de saúde (texto nega nota de prefeitura / NFS-e)"

    if re.search(r"comprovante\s+de\s+pagamento", b) and (
        "mensalidade" in b
        or re.search(
            r"\b(ano letivo|turma|série|serie|ensino médio|ensino medio|matr[íi]cula|aluno)\b",
            b,
        )
    ):
        return "Comprovante de pagamento de mensalidade escolar (recibo educacional)"

    if re.search(
        r"comprovante\s+de\s+contribui[çc][aã]o\s+previdenci|contribui[çc][aã]o\s+previdenci[aá]ria\s+privad",
        b,
    ) or (re.search(r"\bpgbl\b", b) and re.search(r"previd|contrib", b)):
        return "Comprovante de contribuição à previdência privada (PGBL — confirmar no contrato)"

    if re.search(r"\bnfc[\s-]?e\b", b) or "nota fiscal de consumidor" in b:
        if re.search(r"\bdanfe\b", b):
            return "NFC-e + DANFE (cupom / documento auxiliar)"
        return "NFC-e — Nota Fiscal de Consumidor Eletrônica"
    if re.search(r"\bnf[\s-]?se\b", b) or re.search(
        r"\bnfse\b", b
    ) or (re.search(r"nfs-?e", b) and not texto_recibo_comprovante_que_nao_e_nfs_e(texto)):
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

    if re.search(r"recibo\s+de\s+pagamento", b) and any(
        x in b
        for x in (
            "curso de idiomas",
            "curso de inglês",
            "curso de ingles",
            "ensino de idiomas",
            "cultura inglesa",
            "speak up",
            "wizard",
            "fisk",
            "ccaa",
        )
    ):
        return "Recibo de pagamento — curso de idiomas"

    return "Tipo não identificado automaticamente — verifique o PDF ou a categoria escolhida"


def rotulo_leiaute_fiscal(texto: str, nome_arquivo: str = "") -> str:
    b = f"{texto}\n{nome_arquivo}".lower()
    if texto_eh_recibo_aluguel(texto):
        return "—"
    if texto_recibo_comprovante_que_nao_e_nfs_e(texto):
        return "—"
    if re.search(
        r"nota\s+fiscal\s+de\s+servi[çc]os|nfs-?e|\bnfse\b",
        b,
    ):
        return "NFS-e"
    if re.search(r"nfc-?e|nota fiscal de consumidor", b):
        return "NFC-e"
    if re.search(r"\bdanfe\b|documento auxiliar da nota fiscal", b):
        return "NF-e / DANFE"
    if re.search(r"\bnf-?e\b|\bnfe\b", b) and not re.search(
        r"nota\s+fiscal\s+de\s+servi[çc]os",
        b,
    ):
        return "NF-e"
    dconcat = re.sub(r"\D", "", texto + nome_arquivo)
    if re.search(r"\d{44}", dconcat) and re.search(
        r"chave\s+(de\s+)?acesso|chave\s+de\s+acesso|danfe|nf-?e|nfce|nfs-?e", b
    ):
        return "NF-e / NFC-e (chave 44)"
    return "—"


def inferir_tipo_documento_resumido(texto: str, nome_arquivo: str = "") -> str:
    b = f"{texto}\n{nome_arquivo}".lower()
    if _texto_eh_informe_rendimentos(texto):
        return "Informe de rendimentos"
    if texto_eh_recibo_aluguel(texto):
        return "Recibo"
    if texto_recibo_comprovante_que_nao_e_nfs_e(texto):
        return "Recibo"
    if re.search(
        r"nota\s+fiscal\s+de\s+servi[çc]os\s+eletr|nfs-?e|\bnfse\b",
        b,
    ):
        return "NFS-e"
    r = rotulo_leiaute_fiscal(texto, nome_arquivo)
    if r in ("NFS-e", "NFC-e"):
        return r
    if r and r != "—" and (r.startswith("NF-e") or "chave 44" in r):
        return "NF-e"
    if re.search(r"\brecibo\b|recibo\s+de", b) and not re.search(
        r"nota\s+fiscal\s+de\s+servi[çc]os|nfs-?e|\bnfse\b",
        b,
    ):
        return "Recibo"
    if re.search(r"comprovante", b) and not re.search(
        r"nota\s+fiscal|nfs-?e|nf-?e\b|nfc-?e",
        b,
    ):
        return "Comprovante"
    d = inferir_tipo_documento(texto, nome_arquivo)
    if (not texto_recibo_comprovante_que_nao_e_nfs_e(texto)) and (
        "nota fiscal de servi" in b
        or re.search(r"\bnfse\b", b)
        or "nfs-e" in b
    ):
        return "NFS-e"
    if d.lower().startswith("comprovante") and "nota fiscal" not in d[:60].lower():
        return "Comprovante"
    if d.startswith("Recibo") or re.search(r"\brecibo\b", b[:5000]):
        return "Recibo"
    if d.upper().startswith("NFC") or d.startswith("NFC-e"):
        return "NFC-e"
    if d.startswith("NF-e") or "Nota Fiscal Eletr" in d:
        return "NF-e"
    return d if len(d) < 70 else f"{d[:66]}…"


def inferir_categoria_conteudo(texto: str) -> str:
    t = texto.lower()
    if not t.strip():
        return "—"
    if _texto_eh_informe_rendimentos(texto):
        return "Rendimentos de trabalho / fonte pagadora"
    if re.search(
        r"\b(aluguel|arrendamento|recibo de aluguel|"
        r"loca[çc][aã]o|locat[aá]rio|locador)\b",
        t,
    ):
        return "Aluguel"
    if re.search(
        r"recibo\s+de\s+pens|pens[aã]o\s+aliment",
        t,
    ) and re.search(
        r"alimentante|alimentando|representante|judicial|"
        r"processo|senten[çc]a|vara",
        t,
    ):
        return "Pensão alimentícia"
    if _texto_parece_previdencia_pgbl(texto):
        if re.search(r"\bpgbl\b", t):
            return "Previdência privada — PGBL"
        return "Previdência privada"
    if re.search(
        r"(cultura inglesa|ensino de idiomas|curso de idiomas|curso de ingl[êe]s|"
        r"escola de idiomas|speak up|ccaa|wizard|fisk|l[íi]ngua\s+estrangeira|"
        r"atividade:.{0,120}idioma|discrimina[çc].{0,200}(idioma|ingl[êe]s|aula)\b)",
        t,
    ) or re.search(
        r"(cultura inglesa|ensino de idiomas|curso de idiomas|curso de ingl[êe]s)",
        t,
    ):
        return "Educação / curso livre"
    if _texto_parece_saude(texto):
        return "Saúde"
    if _texto_parece_curso_nao_mec(texto) and re.search(
        r"recibo|comprovante|aluno|m[oó]dulo|especializ",
        t,
    ) and re.search(
        r"idiom|ingl[êe]s|l[íi]ngua\s+estran|fisk|ccaa|wizard|speak|"
        r"curso[s]?\s+livre|n[aã]o\s+dedut|curso\s+de\s+ingl|curso\s+de\s+idio",
        t,
    ):
        return "Educação / curso livre"
    if _texto_parece_educacao(texto):
        return "Educação"
    return "Outro"


# Textos fixos de apoio à situação no IRPF (alinhados aos quatro estados principais)
_MOT_IRPF_DEDUTIVEL = (
    "Documento compatível com despesa dedutível, sem pendências relevantes "
    "identificadas pelo sistema."
)
_MOT_IRPF_NAO = (
    "Este documento não se enquadra como despesa dedutível nas regras consideradas "
    "pelo sistema."
)
_MOT_IRPF_NAO_CURSO_LIVRE_IDIOMAS = (
    "Curso de idiomas identificado como curso livre. Cursos livres e de idiomas "
    "não se enquadram como dedução de instrução no IRPF (código 01 do programa — ensino regular "
    "reconhecido pelo MEC), por isso o documento foi classificado como não dedutível nesse sentido."
)
_MOT_IRPF_POTENCIAL_SAUDE = (
    "Documento de saúde identificado, com emitente, valor e beneficiário extraídos. "
    "Ainda é necessário confirmar vínculo com titular/dependente e eventual reembolso."
)
_MOT_IRPF_ODO = (
    "Documento odontológico fiscal identificado, com procedimento, valor e consumidor extraídos. "
    "Compatível com despesas odontológicas em Pagamentos Efetuados; confirme se o beneficiário é "
    "titular ou dependente no programa."
)
_MOT_IRPF_POTENCIAL_MED = (
    "Recibo de serviço de saúde com indícios (consulta, especialidade, CRM ou clínica). "
    "Compatível com Pagamentos Efetuados; confirme o beneficiário (titular/dependente) e o nome no documento."
)
_MOT_IRPF_REVISAR = (
    "O sistema não encontrou evidências suficientes para classificar com segurança."
)
_MOT_IRPF_INFORME = (
    "Informe fornecido pela fonte pagadora. Transcreva os valores para os quadros de "
    "rendimentos, retenções e contribuições conforme o programa de declaração do IRPF."
)
_MOT_IRPF_ALUGUEL_PF = (
    "Recibo de aluguel entre pessoas físicas, com locador(a), locatário, valor e data "
    "identificados quando o texto permite."
)
_LAUDO_REF_ALUGUEL_PAGO = (
    "**Ficha:** Pagamentos Efetuados  \n"
    "**Código 70** — aluguéis (pagos a pessoa física)  \n"
    "Aluguel pago a PF **não é “dedução”** no mesmo sentido de saúde/instrução: costuma ser "
    "**informação declaratória** em Pagamentos Efetuados, conforme o caso.  \n"
    "O **locador** pessoa física recolhe **carnê-leão** (ou tributação aplicável) sobre o "
    "valor recebido; guarde o comprovante de repasse.  \n"
    "Confirme regras do programa do ano e orientação de um contador se necessário."
)
_MOT_IRPF_POTENCIAL_EDU = (
    "NFS-e de educação (mensalidade/instrução) com indícios de dedução por instrução (ex.: "
    "código de serviço 8.01, código 01). Há tomador e aluno: confirme se o aluno é dependente, "
    "se o pagador é o titular e o valor pago (líquido) no original."
)
_MOT_IRPF_POTENCIAL_EDU_COMP = (
    "Comprovante de mensalidade escolar com aluno, responsável, valor pago e indícios de "
    "ensino regular / código 01 (Instrução) em Pagamentos Efetuados. Confirme titular/dependente."
)
_MOT_IRPF_PENSAO_JUD = (
    "Recibo de pensão alimentícia com processo ou decisão judicial, sentença ou referência a "
    "código 30 / Pagamentos Efetuados. Confirme representante, alimentando e alimentante no programa."
)
_MOT_IRPF_PENSAO_SEM = (
    "Recibo de pensão alimentícia: confirme se existe decisão judicial ou escritura, "
    "requisito para dedução; pensão puramente voluntária não gera a mesma regra no IRPF."
)
_MOT_IRPF_PGBL = (
    "Comprovante de contribuição para plano PGBL, com total anual, renda de referência e "
    "percentual em relação ao teto de 12% quando constam no documento. Confirme que o "
    "plano é PGBL (código 36 em Pagamentos Efetuados) e não VGBL."
)


def _layout_nfs_e_no_texto(texto: str) -> bool:
    t = (texto or "").lower()
    return bool(
        re.search(
            r"nota\s+fiscal\s+de\s+servi[çc]os\s+eletr|nfs-?e|\bnfse\b",
            t,
        )
    )


def _sinais_educacao_instrucao_dedutivel(texto: str) -> bool:
    t = (texto or "").lower()
    if re.search(
        r"dedut[ií]vel\s+no\s+irpf|dedut[ií]vel.*c[óo]digo\s*01|"
        r"c[óo]digo\s*01.*instru[çc]",
        t,
    ) and re.search(
        r"escola|col[eé]gio|ensino|instru[çc][aã]o|mensalidade|aluno",
        t,
    ):
        return True
    if re.search(
        r"8[\s.,-]*01|8\.01|dedut[ií]vel.*irpf|instru[çc][aã]o.*c[óo]digo|"
        r"c[óo]digo\s*0?1\b|servi[çc]o.*8[.,\s]*01",
        t,
    ):
        if re.search(
            r"escola|col[eé]gio|colegio|universidade|ensino|mensalidade|mec",
            t,
        ):
            return True
    if re.search(
        r"mensalidade|ensino\s+m[ée]dio|ensino\s+regular|materiais?\s+escolar",
        t,
    ) and re.search(
        r"escola|col[eé]gio|colegio|cnae|prestac",
        t,
    ):
        return True
    if re.search(r"dedu[çc][aã]o\s+irpf|irpf.*c[óo]digo|ficha.{0,40}pagamentos", t) and (
        re.search(r"c[óo]digo\s*0?1\b|c[óo]digo\s*01", t)
        and re.search(
            r"instru[çc][aã]o|ensino\s+(m[ée]dio|regular|fundamental)|col[eé]gio|escola",
            t,
        )
    ):
        return True
    return bool(
        re.search(
            r"dedut[ií]vel|instru[çc][aã]o|quadro\s+de\s+dedu",
            t,
        )
        and re.search(
            r"escola|col[eé]gio|colegio|ensino|mensalidade",
            t,
        )
    )


def _texto_tem_sinais_pensao_judicial(texto: str) -> bool:
    t = (texto or "")[:20000].lower()
    return bool(
        re.search(
            r"decis[aã]o\s+judicial|senten[çc]a|processo\s+n[ºo°]?"
            r"|vara\s+de\s+fam|acordo\s+judicial|escritura\s+p[úu]blica|homologad|despach|"
            r"c[óo]digo\s*30|ficha.{0,50}pagamentos\s+efetuados|pens[aã]o.{0,80}dedut",
            t,
        )
    )


def _texto_parece_previdencia_pgbl(texto: str) -> bool:
    t = (texto or "")[:25000].lower()
    if not t.strip():
        return False
    tem_pgbl = bool(
        re.search(
            r"\bpgbl\b|plano\s+gerador\s+de\s+benef[íi]cio|"
            r"plano\s+gerador",
            t,
        )
    )
    tem_privada = bool(
        re.search(
            r"previd[eê]ncia\s+(complementar|privada)|"
            r"comprovante\s+de\s+contribui[çc][aã]o\s+previdenci",
            t,
        )
    )
    tem_cod36_ou_regra = bool(
        re.search(r"c[óo]digo\s*36", t)
        or re.search(
            r"12\s*,?\s*%\b|12\s*%\b|"
            r"limite\s+dedut[ií]v|"
            r"renda\s+bruta\s+tribut",
            t,
        )
    )
    if tem_pgbl and (tem_privada or tem_cod36_ou_regra or "participante" in t):
        return True
    if re.search(
        r"contribui[çc][aã]o\s+previdenci[aá]ria\s+privat",
        t,
    ) and (tem_pgbl or re.search(r"c[óo]digo\s*36|previd|plano", t)):
        return True
    return False


def _texto_tem_sinais_fortes_despesa_medica(texto: str) -> bool:
    t = (texto or "")[:20000].lower()
    if _texto_eh_informe_rendimentos(texto):
        return False
    return bool(
        re.search(
            r"crm|consulta\s+m[ée]dica|cardiolog|m[ée]dico|"
            r"recebi\s+do\(?a\)?\s+sr\(?a\)?|especialid",
            t,
        )
    )


def _texto_declara_idioma_curso_livre_nao_dedutivel(texto: str) -> bool:
    t = (texto or "")[:20000].lower()
    if not t.strip():
        return False
    tem_idioma = bool(
        re.search(
            r"curso[s]?\s+de\s+idiom|idiomas?\s*\(|ingl[êe]s|espa[ñn]ol|l[íi]ngua",
            t,
        )
    )
    recusa = bool(
        re.search(
            r"n[aã]o\s+s[aã]o\s+dedut|n[aã]o\s+dedut[íi]vel|curso[s]?\s+livre"
            r"|sem\s+reconhecimento\s+mec|somente.+(?:código\s*)?01",
            t,
        )
    )
    return tem_idioma and recusa


def resumir_status_irpf(
    avaliacao: dict,
    *,
    texto: str = "",
    validade_fiscal: bool | None = None,
    categoria_conteudo: str = "",
    nome_beneficiario: str | None = None,
    categoria_interna: str = "",
) -> dict[str, str]:
    def par(status: str, motivo: str) -> dict[str, str]:
        return {"status_irpf": status, "motivo_status_irpf": motivo}

    if not avaliacao:
        return par("Revisar manualmente", _MOT_IRPF_REVISAR)
    if _texto_eh_informe_rendimentos(texto) or categoria_interna == (
        "Informe de Rendimentos"
    ):
        return par(
            "Lançar em Rendimentos Tributáveis (PJ) e retenções/deduções na fonte",
            _MOT_IRPF_INFORME,
        )
    d = avaliacao.get("dedutivel")
    if d is False:
        av = (avaliacao.get("aviso") or "").strip()
        if av:
            return par("Não dedutível", av)
        if _texto_declara_idioma_curso_livre_nao_dedutivel(texto):
            return par("Não dedutível", _MOT_IRPF_NAO_CURSO_LIVRE_IDIOMAS)
        if _texto_parece_curso_nao_mec(texto) and (
            categoria_conteudo.startswith("Educação") or categoria_conteudo == "Outro"
        ):
            return par("Não dedutível", _MOT_IRPF_NAO_CURSO_LIVRE_IDIOMAS)
        return par("Não dedutível", _MOT_IRPF_NAO)
    if d is True:
        return par("Dedutível", _MOT_IRPF_DEDUTIVEL)
    nb = (nome_beneficiario or "").strip()
    if categoria_conteudo == "Aluguel" or texto_eh_recibo_aluguel(texto):
        return par(
            "Lançar em Pagamentos Efetuados (código 70) — aluguel pago a pessoa física",
            _MOT_IRPF_ALUGUEL_PF,
        )
    if categoria_conteudo == "Pensão alimentícia" or (
        categoria_interna == "Pensão Alimentícia"
    ) or texto_eh_recibo_pensao_alimenticia(texto):
        if _texto_tem_sinais_pensao_judicial(texto):
            return par(
                "Potencialmente dedutível — confirmar decisão judicial e "
                "lançamento no código 30 (Pagamentos Efetuados)",
                _MOT_IRPF_PENSAO_JUD,
            )
        return par(
            "Potencialmente dedutível — confirmar título e documentação de pensão",
            _MOT_IRPF_PENSAO_SEM,
        )
    if _texto_parece_previdencia_pgbl(texto) or categoria_conteudo.startswith(
        "Previdência"
    ) or categoria_interna == "Previdência Privada":
        return par(
            "Potencialmente dedutível — confirmar limite global de 12% e plano PGBL",
            _MOT_IRPF_PGBL,
        )
    alvo_sau = categoria_conteudo == "Saúde" or _texto_parece_saude(texto)
    if (
        len(nb) >= 3
        and alvo_sau
        and _texto_parece_odontologia(texto)
    ):
        return par(
            "Potencialmente dedutível — confirmar titular/dependente",
            _MOT_IRPF_ODO,
        )
    if len(nb) >= 3 and alvo_sau:
        return par(
            "Potencialmente dedutível — requer conferência",
            _MOT_IRPF_POTENCIAL_SAUDE,
        )
    if alvo_sau and len(nb) < 3 and _texto_tem_sinais_fortes_despesa_medica(texto):
        if _texto_parece_odontologia(texto):
            return par(
                "Potencialmente dedutível — confirmar titular/dependente",
                _MOT_IRPF_ODO,
            )
        return par(
            "Potencialmente dedutível — confirmar titular/dependente",
            _MOT_IRPF_POTENCIAL_MED,
        )
    alvo_edu = categoria_conteudo.startswith("Educação") or _texto_parece_educacao(
        texto
    )
    if alvo_edu and _sinais_educacao_instrucao_dedutivel(texto):
        if _layout_nfs_e_no_texto(texto) and len(nb) >= 3:
            return par(
                "Potencialmente dedutível — confirmar titular/dependente",
                _MOT_IRPF_POTENCIAL_EDU,
            )
        if len(nb) >= 3 or re.search(
            r"c[óo]digo\s*0?1|pagamentos\s+efetuad|ensino\s+m[ée]dio\s+regular",
            (texto or "")[:20000],
            re.IGNORECASE,
        ):
            return par(
                "Potencialmente dedutível — confirmar titular/dependente",
                _MOT_IRPF_POTENCIAL_EDU_COMP,
            )
    if avaliacao.get("aviso"):
        return par(
            "Revisar manualmente",
            (avaliacao.get("aviso") or "").strip() or _MOT_IRPF_REVISAR,
        )
    return par("Revisar manualmente", _MOT_IRPF_REVISAR)


def _texto_parece_saude(texto: str) -> bool:
    if _texto_eh_informe_rendimentos(texto):
        return False
    t = texto.lower()
    if re.search(
        r"(odontolog|clínica|clinica|hospital|médic|medic|dentist|psicolog|fisio|"
        r"farmácia|farmacia|procedimento|consulta|saúde|saude)",
        t,
    ):
        return True
    if re.search(r"laborat[oó]rio", t) and re.search(
        r"(an[aá]lise|exame|patolog|cl[ií]nic|coleta|sangue|urin)",
        t,
    ):
        return True
    return False


def _texto_parece_odontologia(texto: str) -> bool:
    t = (texto or "")[:20000].lower()
    return bool(
        re.search(
            r"odontol|odont\w{3,}|\bdentist|endodont|"
            r"\bdente\b|dentes|reabilita[çc].{0,20}oral|"
            r"pr[óo]tese.{0,15}dent|implantodont|"
            r"restaura[çc].{0,25}(composta|dente|resin)|"
            r"\bcro[-\s]?\d|\bcro[-\s]*[a-z]{2}\b|odont",
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


def _texto_parece_ensino_fiscal(texto: str) -> bool:
    t = texto.lower()
    return bool(
        re.search(
            r"(ensino de idiomas|8593[0-9]{0,3}|cnae.{0,12}859|"
            r"instru[cç][aã]o[,\s].{0,40}pedag|atividade[:\s].{0,12}0?802|"
            r"treinamento[,\s].{0,25}pedag|cultura inglesa)",
            t,
        )
    )


def _texto_parece_curso_nao_mec(texto: str) -> bool:
    t = texto.lower()
    if _texto_parece_ensino_fiscal(texto):
        return True
    return bool(
        re.search(
            r"(curso de idi|ensino de idi|curso de ingl[êe]s|l[íi]ngua\s+estrangeira|"
            r"ingl[êe]s|idiomas|speak up|wizard|ccaa|cultura inglesa|"
            r"atividade:.{0,30}0?802|0802)",
            t,
        )
    )


def referencia_irpf(categoria: str, texto: str = "") -> str:
    """Texto curto ligando a categoria do app ao quadro usual da declaração IRPF."""
    if categoria == "Aluguel" or texto_eh_recibo_aluguel(texto):
        return _LAUDO_REF_ALUGUEL_PAGO

    if categoria == "Pensão Alimentícia" or (
        categoria in ("Documento Não Classificado", "Requer Revisão")
        and texto_eh_recibo_pensao_alimenticia(texto)
    ):
        p = _REF_IRPF_POR_CATEGORIA["Pensão Alimentícia"]
        return "\n\n".join(
            [
                f"Ficha: **{p['ficha']}**  \nCódigo: **{p['codigo']}**",
                p["observacao"],
            ]
        )

    if categoria == "Documento Não Classificado" and _texto_parece_curso_nao_mec(texto):
        return (
            "**Não lance** como dedução de instrução (código **01** do programa). "
            "Cursos de idiomas e cursos livres **não** se enquadram no ensino regular "
            "reconhecido pelo MEC, portanto **não** usam essa faixa. Guarde o comprovante "
            "como comprovante de pagamento; para o IRPF, trate como **não dedutível** "
            "nesse quadro."
        )

    if categoria in ("Documento Não Classificado", "Requer Revisão"):
        if _texto_parece_previdencia_pgbl(texto):
            pp = _REF_IRPF_POR_CATEGORIA["Previdência Privada"]
            return "\n\n".join(
                [
                    f"Ficha: **{pp['ficha']}**  \nCódigo: **{pp['codigo']}**",
                    pp["observacao"],
                ]
            )
        if _texto_parece_educacao(texto) and _sinais_educacao_instrucao_dedutivel(
            texto
        ):
            refe = _REF_IRPF_POR_CATEGORIA["Comprovante Educacional"]
            limf = _formatar_reais_br(refe["limite"])
            return "\n\n".join(
                [
                    f"Ficha: **{refe['ficha']}**  \nCódigo: **{refe['codigo']}**",
                    f"**Limite anual:** {limf} por pessoa/ano (ensino MEC, código 01).",
                    refe["observacao"],
                ]
            )
        if _texto_parece_odontologia(texto):
            return (
                "Ficha: **Pagamentos Efetuados**  \n"
                "Código: **10 — Dentista**  \n\n"
                "Despesas odontológicas costumam seguir a mesma lógica de despesas médicas "
                "(sem limite de valor no conjunto das despesas elegíveis), desde que o "
                "beneficiário seja titular ou dependente. Confira o programa e o ano-calendário."
            )
        if _texto_parece_saude(texto):
            ref = _REF_IRPF_POR_CATEGORIA["Recibo Médico"]
            return "\n\n".join(
                [
                    f"Ficha: **{ref['ficha']}**  \nCódigo: **{ref['codigo']}**",
                    ref["observacao"],
                ]
            )

    if categoria == "Nota Fiscal":
        if _texto_parece_educacao(texto) or _texto_parece_ensino_fiscal(texto):
            ref = _REF_IRPF_POR_CATEGORIA["Comprovante Educacional"]
            lim = _formatar_reais_br(ref["limite"])
            return "\n\n".join(
                [
                    f"Ficha: **{ref['ficha']}**  \nCódigo: **{ref['codigo']}**",
                    f"**Limite anual:** {lim} por pessoa/ano (ensino MEC, código 01).",
                    ref["observacao"],
                ]
            )
        if _texto_parece_saude(texto):
            ref = _REF_IRPF_POR_CATEGORIA["Recibo Médico"]
            return "\n\n".join(
                [
                    f"Ficha: **{ref['ficha']}**  \nCódigo: **{ref['codigo']}**",
                    ref["observacao"],
                ]
            )

    entry = _REF_IRPF_POR_CATEGORIA.get(categoria)
    if not entry:
        return "Escolha a categoria adequada e confira a instrução do IRPF do ano-calendário."

    partes = [f"Ficha: **{entry['ficha']}**  \nCódigo: **{entry['codigo']}**"]
    if entry.get("limite") is not None:
        partes.append(
            f"**Limite anual:** {_formatar_reais_br(entry['limite'])} por pessoa/ano"
        )
    partes.append(entry["observacao"])
    return "\n\n".join(partes)


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
        ["curso de inglês", "curso de ingles", "curso de espanhol",
         "curso de francês", "curso de frances", "curso de alemão", "curso de alemao",
         "curso de mandarim", "curso de japonês", "curso de japonês",
         "curso livre", "curso profissionalizante", "curso de idiomas",
         "speak up", "wizard", "fisk", "ccaa", "cultura inglesa",
         "yázigi", "yazigi", "skill idiomas", "english", "english school",
         "ensino de idiomas", "língua estrangeira", "lingua estrangeira"],
        _MOT_IRPF_NAO_CURSO_LIVRE_IDIOMAS,
        [],
    ),
    (
        ["perfume", "cosmético", "cosmetico", "maquiagem", "batom",
         "creme facial", "creme corporal", "shampoo", "condicionador", "tintura",
         "salão de beleza", "cabeleireiro", "manicure", "pedicure", "depilação",
         "o boticário", "natura ", "avon ", "vult", "quem disse berenice",
         "mac cosméticos", "sephora", "beauty", "perfumaria"],
        "Cosméticos, perfumes e serviços de beleza NÃO são dedutíveis no IRPF.",
        [
            "base de cálculo", "base de calculo", "nota fiscal de servi",
            "nfs-e", "nfse", "cultura inglesa", "ensino de idiomas",
        ],
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
        [
            "pet shop",
            "veterinário",
            "veterinario",
            "petco",
            "petz",
            "cobasi",
            "banho e tosa",
            "plano pet",
        ],
        "Gastos com animais de estimação NÃO são dedutíveis no IRPF.",
        [
            "odontol",
            "odonto",
            "endodont",
            "odontológ",
            "procedimento odontol",
        ],
    ),
    (
        ["vgbl", "vida gerador de benefício"],
        (
            "VGBL NÃO é dedutível no IRPF — é tratado como seguro de vida. "
            "Apenas PGBL (código 36) é dedutível, até 12% da renda bruta tributável."
        ),
        ["pgbl", "p g b l", "plano pgbl", "plano pgb", "plano gerador de benefício livre"],
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

    if _texto_eh_informe_rendimentos(texto):
        return {"dedutivel": None, "aviso": None, "nivel": "ok"}

    for padroes, mensagem, excecoes in _PADROES_NAO_DEDUTIVEIS:
        if excecoes and any(e in t for e in excecoes):
            continue
        gatilho = False
        for p in padroes:
            if p in t:
                gatilho = True
                break
        if not gatilho and "animais" in (mensagem or ""):
            gatilho = bool(
                re.search(r"\bra[cç][aã]o\b", t, re.IGNORECASE)
                or re.search(r"\bracao\b", t, re.IGNORECASE)
            )
        if gatilho:
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
                "código 30", "codigo 30", "despach",
            ]
        )
        if not tem_judicial and re.search(
            r"c[óo]digo\s*30|ficha.{0,40}pagamentos\s+efetuados",
            t,
        ):
            tem_judicial = True
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
