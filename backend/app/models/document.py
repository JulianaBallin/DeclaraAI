"""
Modelo de banco de dados para documentos fiscais salvos pelo usuário.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
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

    # Conteúdo extraído
    texto_extraido = Column(Text, nullable=True)

    # Metadados detectados por heurísticas
    data_detectada = Column(String(50), nullable=True)
    valor_detectado = Column(String(50), nullable=True)
    emitente_detectado = Column(String(255), nullable=True)

    # Localização do arquivo no servidor
    caminho_arquivo = Column(String(500), nullable=True)

    # Timestamp automático de criação (sem timezone — SQLite armazena como TEXT ISO)
    criado_em = Column(
        DateTime(),
        server_default=func.now(),
        nullable=False,
    )
