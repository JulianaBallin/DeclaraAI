"""
Configuração do banco de dados relacional com SQLAlchemy.
Utiliza SQLite para persistência dos documentos salvos pelo usuário.
"""

from sqlalchemy import create_engine
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


def criar_tabelas():
    """Cria todas as tabelas no banco de dados se não existirem."""
    Base.metadata.create_all(bind=motor)
    logger.info("Tabelas do banco de dados verificadas/criadas.")
