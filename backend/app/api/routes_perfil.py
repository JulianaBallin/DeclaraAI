"""
Rotas para perfil do declarante e verificação de titularidade.

O perfil é armazenado apenas na sessão do backend (em memória por processo).
Para persistência real entre sessões, o frontend usa seu próprio session_state.
"""

from fastapi import APIRouter
from app.schemas.document import PerfilDeclarante, RespostaVerificacaoTitularidade
from app.services.titularidade_service import verificar_titularidade
import logging

logger = logging.getLogger(__name__)

roteador = APIRouter()

# Armazenamento em memória (session-level — adequado para uso single-user/local)
_perfil_sessao: dict = {}


@roteador.post(
    "/perfil",
    summary="Registrar perfil do declarante",
    description="Armazena nome completo e CPF do declarante para a sessão atual.",
)
async def registrar_perfil(perfil: PerfilDeclarante):
    """Salva o perfil do declarante na sessão corrente."""
    _perfil_sessao["nome_completo"] = perfil.nome_completo
    _perfil_sessao["cpf"] = perfil.cpf
    logger.info("Perfil do declarante registrado: %s", perfil.nome_completo)
    return {"mensagem": "Perfil registrado com sucesso.", "nome": perfil.nome_completo}


@roteador.get(
    "/perfil",
    summary="Consultar perfil do declarante",
    description="Retorna o perfil do declarante registrado na sessão.",
)
async def consultar_perfil():
    """Retorna o perfil atual ou indica que não foi registrado."""
    if not _perfil_sessao:
        return {"registrado": False, "nome_completo": None, "cpf": None}
    return {
        "registrado": True,
        "nome_completo": _perfil_sessao.get("nome_completo"),
        "cpf": _perfil_sessao.get("cpf"),
    }


@roteador.post(
    "/verificar-titularidade",
    response_model=RespostaVerificacaoTitularidade,
    summary="Verificar se o beneficiário é o declarante ou dependente",
    description=(
        "Compara o nome do beneficiário extraído do documento com o nome do declarante registrado. "
        "Foca nos sobrenomes para detectar dependentes familiares."
    ),
)
async def verificar_titularidade_documento(
    nome_beneficiario: str,
):
    """Verifica titularidade usando o perfil registrado na sessão."""
    nome_declarante = _perfil_sessao.get("nome_completo", "")
    resultado = verificar_titularidade(nome_declarante, nome_beneficiario)
    return RespostaVerificacaoTitularidade(**resultado)
