"""
Configuração do banco de dados relacional com SQLAlchemy.
Utiliza SQLite para persistência dos documentos salvos pelo usuário.
"""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import configuracoes
import logging

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Classe base para todos os modelos SQLAlchemy."""
    pass


# Motor do banco de dados
# check_same_thread=False necessário para SQLite com FastAPI (múltiplas threads)
motor = create_engine(
    configuracoes.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=configuracoes.DEBUG,
)

# Fábrica de sessões
SessaoLocal = sessionmaker(autocommit=False, autoflush=False, bind=motor)


def obter_db():
    """
    Dependência do FastAPI para injeção de sessão de banco de dados.
    Garante que a sessão seja fechada após cada requisição.
    """
    db = SessaoLocal()
    try:
        yield db
    finally:
        db.close()


def _migrar_colunas_documentos():
    """SQLite: adiciona colunas novas em `documentos` se o arquivo já existia."""
    try:
        insp = inspect(motor)
        if not insp.has_table("documentos"):
            return
        existentes = {c["name"] for c in insp.get_columns("documentos")}
        novas_colunas = [
            ("tipo_documento", "VARCHAR(200)"),
            ("referencia_irpf", "VARCHAR(500)"),
            ("validade_fiscal", "BOOLEAN"),
            ("confianca_classificacao", "VARCHAR(10)"),
            ("chave_acesso", "VARCHAR(44)"),
            ("cnpj_emitente", "VARCHAR(20)"),
            ("nome_beneficiario", "VARCHAR(255)"),
            ("nome_tomador_nfs_e", "VARCHAR(255)"),
            ("codigo_verificacao", "VARCHAR(64)"),
            ("identificador_fiscal", "VARCHAR(64)"),
            ("tipo_leiaute", "VARCHAR(30)"),
            ("categoria_conteudo", "VARCHAR(200)"),
            ("status_irpf", "VARCHAR(200)"),
            ("motivo_status_irpf", "TEXT"),
            ("validade_fiscal_legenda", "VARCHAR(500)"),
        ]
        with motor.begin() as conn:
            for coluna, tipo_sql in novas_colunas:
                if coluna not in existentes:
                    conn.execute(
                        text(f"ALTER TABLE documentos ADD COLUMN {coluna} {tipo_sql}")
                    )
                    logger.info("Coluna %s adicionada à tabela documentos.", coluna)
    except Exception as e:
        logger.warning("Migração leve documentos: %s", e)


def criar_tabelas():
    """Cria todas as tabelas no banco de dados se não existirem."""
    Base.metadata.create_all(bind=motor)
    _migrar_colunas_documentos()
    logger.info("Tabelas do banco de dados verificadas/criadas.")
