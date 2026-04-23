"""
Modelo de banco de dados para documentos fiscais salvos pelo usuário.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from app.core.database import Base


class Documento(Base):
    """
    Representa um documento fiscal salvo no histórico do usuário.

    Campos extraídos automaticamente por heurísticas (data, valor, emitente)
    são armazenados como strings para flexibilidade, pois os formatos variam
    entre diferentes tipos de documentos.
    """

    __tablename__ = "documentos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Identificação do arquivo
    nome_arquivo = Column(String(255), nullable=False, index=True)
    tipo_arquivo = Column(String(10), nullable=False)  # pdf, txt, html

    # Classificação tributária sugerida
    categoria = Column(String(100), nullable=True, index=True)

    tipo_documento = Column(String(200), nullable=True)
    tipo_leiaute = Column(String(30), nullable=True)
    categoria_conteudo = Column(String(200), nullable=True)
    status_irpf = Column(String(200), nullable=True)
    motivo_status_irpf = Column(Text, nullable=True)
    validade_fiscal_legenda = Column(String(500), nullable=True)
    referencia_irpf = Column(String(500), nullable=True)

    # M1: validade fiscal e confiança da classificação
    validade_fiscal = Column(Boolean, nullable=True)          # True = NF-e/NFC-e/NFSe; False = recibo/declaração
    confianca_classificacao = Column(String(10), nullable=True)  # alta | media | baixa

    # Conteúdo extraído
    texto_extraido = Column(Text, nullable=True)

    # Metadados detectados por heurísticas
    data_detectada = Column(String(50), nullable=True)
    valor_detectado = Column(String(50), nullable=True)
    emitente_detectado = Column(String(255), nullable=True)

    # M2: campos estruturados para NF-e / identificador NFS-e municipal
    chave_acesso = Column(String(44), nullable=True)
    codigo_verificacao = Column(String(64), nullable=True)
    identificador_fiscal = Column(String(64), nullable=True)
    cnpj_emitente = Column(String(20), nullable=True)    # CNPJ ou CPF do emitente
    nome_beneficiario = Column(String(255), nullable=True)  # destinatário/paciente/aluno
    nome_tomador_nfs_e = Column(String(255), nullable=True)  # tomador/pagador (NFS-e)

    # Localização do arquivo no servidor
    caminho_arquivo = Column(String(500), nullable=True)

    # Timestamp automático de criação (sem timezone — SQLite armazena como TEXT ISO)
    criado_em = Column(
        DateTime(),
        server_default=func.now(),
        nullable=False,
    )
