"""
Schemas Pydantic para validação e serialização de dados da API.
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


# ---------------------------------------------------------------------------
# Schemas de Documento
# ---------------------------------------------------------------------------

class DocumentoBase(BaseModel):
    """Campos comuns a todos os schemas de documento."""
    nome_arquivo: str
    tipo_arquivo: str
    categoria: Optional[str] = None
    tipo_documento: Optional[str] = None
    referencia_irpf: Optional[str] = None
    validade_fiscal: Optional[bool] = None
    confianca_classificacao: Optional[str] = None
    data_detectada: Optional[str] = None
    valor_detectado: Optional[str] = None
    emitente_detectado: Optional[str] = None
    chave_acesso: Optional[str] = None
    cnpj_emitente: Optional[str] = None
    nome_beneficiario: Optional[str] = None


class DocumentoSalvar(DocumentoBase):
    """Schema para salvar documento no histórico (enviado pelo frontend)."""
    texto_extraido: Optional[str] = None
    caminho_arquivo: Optional[str] = None


class DocumentoResumo(DocumentoBase):
    """Schema resumido para listagem no histórico (sem texto completo)."""
    id: int
    criado_em: datetime

    model_config = {"from_attributes": True}


class DocumentoCompleto(DocumentoBase):
    """Schema completo incluindo texto extraído."""
    id: int
    texto_extraido: Optional[str] = None
    criado_em: datetime

    model_config = {"from_attributes": True}


class DocumentoProcessado(BaseModel):
    """Resultado do processamento de upload de documento."""
    nome_arquivo: str
    tipo_arquivo: str
    categoria: str
    tipo_documento: Optional[str] = None
    referencia_irpf: Optional[str] = None
    validade_fiscal: Optional[bool] = None
    confianca_classificacao: Optional[str] = None
    texto_extraido: str
    data_detectada: Optional[str] = None
    valor_detectado: Optional[str] = None
    emitente_detectado: Optional[str] = None
    chave_acesso: Optional[str] = None
    cnpj_emitente: Optional[str] = None
    nome_beneficiario: Optional[str] = None
    caminho_arquivo: Optional[str] = None


# ---------------------------------------------------------------------------
# Schemas de Chat
# ---------------------------------------------------------------------------

class RequisicaoChat(BaseModel):
    """Requisição de pergunta ao sistema RAG."""
    pergunta: str
    historico: Optional[List[dict]] = []


class RespostaChat(BaseModel):
    """Resposta gerada pelo pipeline RAG."""
    resposta: str
    contexto_utilizado: Optional[List[str]] = []
    fontes: Optional[List[str]] = []
    chunks_recuperados: Optional[int] = 0
    scores_contexto: Optional[List[float]] = []  # Scores de similaridade (0–1)


# ---------------------------------------------------------------------------
# Schemas de Resumo
# ---------------------------------------------------------------------------

class ItemResumo(BaseModel):
    """Item individual dentro do resumo de uma categoria."""
    id: int
    nome: str
    data_detectada: Optional[str] = None
    valor_detectado: Optional[str] = None
    emitente: Optional[str] = None
    criado_em: Optional[str] = None


class CategoriaResumo(BaseModel):
    """Resumo de documentos agrupados por categoria tributária."""
    quantidade: int
    documentos: List[ItemResumo]
    valores: List[str]


class ResumoAnual(BaseModel):
    """Resumo anual de todos os documentos organizados por categoria."""
    ano: int
    total_documentos: int
    categorias: dict


# ---------------------------------------------------------------------------
# Schemas de Perfil do Declarante (M4)
# ---------------------------------------------------------------------------

class PerfilDeclarante(BaseModel):
    """Dados do titular da declaração fornecidos pelo usuário."""
    nome_completo: str
    cpf: str


class RespostaVerificacaoTitularidade(BaseModel):
    """Resultado da verificação de nome do beneficiário vs. declarante."""
    status: str          # "titular" | "provavel_dependente" | "terceiro" | "nao_verificado"
    mensagem: str
    requer_confirmacao: bool
