"""Gera documentos de simulação em PNG e PDF para a persona Ana Clara."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from fpdf import FPDF

OUT = Path(__file__).parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fonte(size=16, bold=False):
    try:
        if bold:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def nova_imagem(largura=900, altura=1200, bg=(255, 255, 255)):
    img = Image.new("RGB", (largura, altura), bg)
    return img, ImageDraw.Draw(img)


def linha(draw, y, texto, x=50, cor=(30, 30, 30), size=16, bold=False):
    draw.text((x, y), texto, fill=cor, font=fonte(size, bold))
    return y + size + 6


def separador(draw, y, largura=900):
    draw.line([(50, y), (largura - 50, y)], fill=(180, 180, 180), width=1)
    return y + 10


# ---------------------------------------------------------------------------
# PNG 1 – Recibo de consulta médica (Ana Clara)
# ---------------------------------------------------------------------------

def gerar_png_recibo_medico():
    img, draw = nova_imagem(900, 800)
    y = 40
    y = linha(draw, y, "RECIBO DE CONSULTA MÉDICA", x=180, size=22, bold=True, cor=(20, 80, 160))
    y = separador(draw, y + 8)
    y += 10
    y = linha(draw, y, "Dra. Fernanda Costa Oliveira  –  CRM/AM 18.765", size=17, bold=True)
    y = linha(draw, y, "Av. Djalma Batista, 1010, Sala 305 – Chapada – Manaus/AM", size=14)
    y = linha(draw, y, "Fone: (92) 3888-4422  |  contato@dracosta.med.br", size=14)
    y = separador(draw, y + 8)
    y += 10
    campos = [
        ("Paciente:",      "ANA CLARA RODRIGUES NASCIMENTO"),
        ("CPF:",           "071.234.567-18"),
        ("Especialidade:", "Clínica Médica – Consulta de Rotina"),
        ("Data:",          "14/03/2024"),
        ("Recibo Nº:",     "002341"),
        ("Valor Pago:",    "R$ 350,00  (trezentos e cinquenta reais)"),
        ("Pagamento:",     "PIX – 14/03/2024"),
    ]
    for label, valor in campos:
        draw.text((50, y), label, fill=(80, 80, 80), font=fonte(15, bold=True))
        draw.text((230, y), valor, fill=(20, 20, 20), font=fonte(15))
        y += 28

    y = separador(draw, y + 10)
    y += 10
    y = linha(draw, y, "IRPF: Despesas médicas são dedutíveis – código 21 (Médicos).", size=14, cor=(0, 120, 0))
    y = linha(draw, y, "Ficha: Pagamentos Efetuados.", size=14, cor=(0, 120, 0))
    y += 30
    draw.text((50, y), "Manaus, 14 de março de 2024.", fill=(60, 60, 60), font=fonte(14))
    y += 50
    draw.line([(50, y), (400, y)], fill=(80, 80, 80), width=1)
    y += 8
    draw.text((50, y), "Dra. Fernanda Costa Oliveira  –  CRM/AM 18.765", fill=(60, 60, 60), font=fonte(13))
    y += 40
    draw.text((50, y), "DOCUMENTO FICTÍCIO PARA FINS DE TESTE DE SISTEMA", fill=(180, 0, 0), font=fonte(12, bold=True))

    img.save(OUT / "08_recibo_medico_ana_clara.png")
    print("PNG gerado: 08_recibo_medico_ana_clara.png")


# ---------------------------------------------------------------------------
# PNG 2 – Comprovante de plano de saúde (Ana Clara)
# ---------------------------------------------------------------------------

def gerar_png_plano_saude():
    img, draw = nova_imagem(900, 700)
    y = 40
    y = linha(draw, y, "COMPROVANTE DE PLANO DE SAÚDE", x=180, size=22, bold=True, cor=(20, 80, 160))
    y = separador(draw, y + 8)
    y += 10
    y = linha(draw, y, "UNIMED MANAUS COOPERATIVA DE TRABALHO MÉDICO", size=17, bold=True)
    y = linha(draw, y, "CNPJ: 05.703.282/0001-70", size=14)
    y = linha(draw, y, "Av. Mário Ypiranga, 4220 – Adrianópolis – Manaus/AM", size=14)
    y = separador(draw, y + 8)
    y += 10
    campos = [
        ("Beneficiária:",    "ANA CLARA RODRIGUES NASCIMENTO"),
        ("CPF:",             "071.234.567-18"),
        ("Matrícula:",       "UN-2024-071234567"),
        ("Dependente 1:",    "Pedro Henrique Rodrigues Nascimento"),
        ("Dependente 2:",    "Sofia Rodrigues Nascimento"),
        ("Plano:",           "Unimed Nacional Ambulatorial + Hospitalar"),
        ("Período:",         "Janeiro a Dezembro/2024"),
        ("Total pago 2024:", "R$ 9.600,00"),
    ]
    for label, valor in campos:
        draw.text((50, y), label, fill=(80, 80, 80), font=fonte(15, bold=True))
        draw.text((280, y), valor, fill=(20, 20, 20), font=fonte(15))
        y += 28

    y = separador(draw, y + 10)
    y += 10
    y = linha(draw, y, "IRPF: Planos de saúde são dedutíveis – código 26 (Planos de Saúde).", size=14, cor=(0, 120, 0))
    y = linha(draw, y, "Inclua também os valores pagos pelos dependentes.", size=14, cor=(0, 120, 0))
    y += 30
    draw.text((50, y), "DOCUMENTO FICTÍCIO PARA FINS DE TESTE DE SISTEMA", fill=(180, 0, 0), font=fonte(12, bold=True))

    img.save(OUT / "09_plano_saude_ana_clara.png")
    print("PNG gerado: 09_plano_saude_ana_clara.png")


# ---------------------------------------------------------------------------
# PDF 1 – Recibo de mensalidade escolar (Pedro Henrique)
# ---------------------------------------------------------------------------

def gerar_pdf_mensalidade_pedro():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Cabeçalho
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(20, 80, 160)
    pdf.cell(0, 10, "RECIBO DE MENSALIDADE ESCOLAR", ln=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, "COLEGIO ESTADUAL PROGRESSO LTDA", ln=True, align="C")
    pdf.cell(0, 6, "CNPJ: 45.678.901/0001-23", ln=True, align="C")
    pdf.cell(0, 6, "Rua da Educacao, 800 - Aleixo - Manaus/AM", ln=True, align="C")
    pdf.ln(4)
    pdf.set_draw_color(180, 180, 180)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    # Dados
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(60, 7, "Recibo N.:", ln=False)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, "2024REC-001087", ln=True)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(60, 7, "Responsavel:", ln=False)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, "ANA CLARA RODRIGUES NASCIMENTO", ln=True)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(60, 7, "CPF:", ln=False)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, "071.234.567-18", ln=True)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(60, 7, "Aluno:", ln=False)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, "PEDRO HENRIQUE RODRIGUES NASCIMENTO (dependente)", ln=True)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(60, 7, "CPF Dependente:", ln=False)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, "234.567.891-73", ln=True)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(60, 7, "Serie/Turma:", ln=False)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, "6 Ano do Ensino Fundamental - Turma C", ln=True)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(60, 7, "Competencia:", ln=False)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, "Outubro/2024", ln=True)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(60, 7, "Valor Pago:", ln=False)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, "R$ 890,00 (oitocentos e noventa reais)", ln=True)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(60, 7, "Forma Pag.:", ln=False)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, "Boleto bancario - 05/10/2024", ln=True)

    pdf.ln(4)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Codigo do Servico: 8.01 - Ensino regular reconhecido pelo MEC", ln=True)
    pdf.ln(2)

    pdf.set_text_color(0, 120, 0)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6,
        "IRPF: Despesas de educacao sao dedutiveis - codigo 01 (Instrucao).\n"
        "Limite anual: R$ 3.561,50 por pessoa. Lancamento em nome do dependente.")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    pdf.cell(0, 7, "Manaus, 05 de outubro de 2024.", ln=True)
    pdf.ln(10)
    pdf.line(10, pdf.get_y(), 100, pdf.get_y())
    pdf.ln(4)
    pdf.cell(0, 6, "Setor Financeiro - Colegio Estadual Progresso", ln=True)
    pdf.ln(8)
    pdf.set_text_color(180, 0, 0)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 6, "DOCUMENTO FICTICIO PARA FINS DE TESTE DE SISTEMA - NAO TEM VALIDADE FISCAL", ln=True)

    pdf.output(str(OUT / "10_mensalidade_pedro_henrique.pdf"))
    print("PDF gerado: 10_mensalidade_pedro_henrique.pdf")


# ---------------------------------------------------------------------------
# PDF 2 - Conta hospitalar (Ana Clara - internação)
# ---------------------------------------------------------------------------

def gerar_pdf_conta_hospitalar():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(20, 80, 160)
    pdf.cell(0, 10, "CONTA HOSPITALAR - INTERNACAO", ln=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, "HOSPITAL E CLINICA SAO LUCAS LTDA", ln=True, align="C")
    pdf.cell(0, 6, "CNPJ: 34.678.901/0001-55", ln=True, align="C")
    pdf.cell(0, 6, "Av. Carvalho Leal, 1456 - Cachoeirinha - Manaus/AM", ln=True, align="C")
    pdf.ln(4)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    campos = [
        ("Paciente:",       "ANA CLARA RODRIGUES NASCIMENTO"),
        ("CPF:",            "071.234.567-18"),
        ("Prontuario:",     "HC-2024-008821"),
        ("Internacao:",     "18/11/2024  a  22/11/2024  (4 diarias)"),
        ("Diagnostico:",    "Apendicite aguda - CID K35.8"),
        ("Cirurgia:",       "Apendicectomia laparoscopica"),
    ]
    for label, valor in campos:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(60, 7, label, ln=False)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 7, valor, ln=True)

    pdf.ln(4)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "DISCRIMINACAO DOS VALORES", ln=True)
    pdf.ln(2)

    itens = [
        ("Diarias hospitalares (4x R$ 1.200,00)", "R$  4.800,00"),
        ("Honorarios medicos - cirurgia",          "R$  3.500,00"),
        ("Anestesia",                              "R$  1.200,00"),
        ("Medicamentos utilizados na internacao",  "R$    890,00"),
        ("Materiais cirurgicos",                   "R$    650,00"),
        ("Exames laboratoriais",                   "R$    380,00"),
        ("Exames de imagem (tomografia)",          "R$    520,00"),
    ]
    for desc, val in itens:
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(140, 6, desc, ln=False)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, val, ln=True, align="R")

    pdf.ln(2)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(140, 8, "TOTAL DA CONTA HOSPITALAR:", ln=False)
    pdf.cell(0, 8, "R$ 11.940,00", ln=True, align="R")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "Pago pelo plano de saude: R$ 9.552,00  |  Coparticipacao: R$ 2.388,00", ln=True)
    pdf.ln(4)

    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)
    pdf.set_text_color(0, 120, 0)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6,
        "IRPF: Despesas hospitalares (incluindo medicamentos utilizados na internacao)\n"
        "sao dedutíveis - codigos 21 (Medicos) e 26 (Planos). Deduzir apenas a coparticipacao\n"
        "nao coberta pelo plano: R$ 2.388,00.")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    pdf.cell(0, 7, "Manaus, 25 de novembro de 2024.", ln=True)
    pdf.ln(10)
    pdf.line(10, pdf.get_y(), 100, pdf.get_y())
    pdf.ln(4)
    pdf.cell(0, 6, "Faturamento - Hospital e Clinica Sao Lucas", ln=True)
    pdf.ln(8)
    pdf.set_text_color(180, 0, 0)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 6, "DOCUMENTO FICTICIO PARA FINS DE TESTE DE SISTEMA - NAO TEM VALIDADE FISCAL", ln=True)

    pdf.output(str(OUT / "11_conta_hospitalar_ana_clara.pdf"))
    print("PDF gerado: 11_conta_hospitalar_ana_clara.pdf")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    gerar_png_recibo_medico()
    gerar_png_plano_saude()
    gerar_pdf_mensalidade_pedro()
    gerar_pdf_conta_hospitalar()
    print("Todos os documentos gerados com sucesso.")
