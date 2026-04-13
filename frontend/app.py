"""
Interface web do DeclaraAI construída com Streamlit.

Organizada em 4 abas:
- Chat: perguntas em linguagem natural respondidas pelo pipeline RAG
- Upload: envio e processamento de documentos fiscais
- Histórico: consulta e filtragem dos documentos salvos
- Resumo: visão anual agrupada por categoria tributária
"""

import os
from datetime import datetime

import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Configuração global
# ---------------------------------------------------------------------------

API_URL = os.getenv("API_URL", "http://localhost:8000")
TIMEOUT_CHAT = 180
TIMEOUT_UPLOAD = 90
TIMEOUT_PADRAO = 30

st.set_page_config(
    page_title="DeclaraAI",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# CSS customizado mínimo
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    .metric-label { font-size: 0.85rem; color: #555; }
    .stTabs [data-baseweb="tab"] { font-size: 1rem; padding: 0.5rem 1.2rem; }
    div[data-testid="stExpander"] { border: 1px solid #e0e0e0; border-radius: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Cabeçalho
# ---------------------------------------------------------------------------

st.title("DeclaraAI")
st.caption(
    "Assistente inteligente para organização de documentos e apoio à declaração do IR"
)
st.divider()

# ---------------------------------------------------------------------------
# Abas principais
# ---------------------------------------------------------------------------

aba_chat, aba_upload, aba_historico, aba_resumo = st.tabs(
    ["💬 Chat", "📄 Upload", "📚 Histórico", "📊 Resumo Anual"]
)


# ===========================================================================
# ABA CHAT
# ===========================================================================

def _chamar_api_chat(pergunta: str) -> dict | None:
    """Envia pergunta à API e retorna o resultado ou None em caso de erro."""
    try:
        resposta = requests.post(
            f"{API_URL}/chat",
            json={"pergunta": pergunta},
            timeout=TIMEOUT_CHAT,
        )
        if resposta.status_code == 200:
            return resposta.json()
        st.error(f"Erro da API: {resposta.status_code} — {resposta.text}")
    except requests.exceptions.ConnectionError:
        st.error(
            "Não foi possível conectar ao servidor. "
            "Verifique se o backend está rodando em: " + API_URL
        )
    except requests.exceptions.Timeout:
        st.error(
            "O modelo demorou demais para responder. "
            "Certifique-se de que o Ollama está carregado e tente novamente."
        )
    except Exception as erro:
        st.error(f"Erro inesperado: {erro}")
    return None


with aba_chat:
    st.header("Chat com Assistente RAG")
    st.write(
        "Faça perguntas sobre imposto de renda em linguagem natural. "
        "O assistente busca respostas na base de conhecimento tributário."
    )

    # Inicializa histórico de mensagens na sessão
    if "mensagens_chat" not in st.session_state:
        st.session_state.mensagens_chat = []

    # Exibe histórico de mensagens
    for mensagem in st.session_state.mensagens_chat:
        with st.chat_message(mensagem["papel"]):
            st.markdown(mensagem["conteudo"])
            if mensagem.get("fontes"):
                with st.expander("Fontes consultadas"):
                    for fonte in mensagem["fontes"]:
                        st.write(f"- {fonte}")

    # Campo de entrada do usuário
    pergunta_usuario = st.chat_input("Digite sua dúvida sobre IR...")

    if pergunta_usuario:
        # Exibe mensagem do usuário imediatamente
        with st.chat_message("user"):
            st.markdown(pergunta_usuario)
        st.session_state.mensagens_chat.append(
            {"papel": "user", "conteudo": pergunta_usuario}
        )

        # Obtém e exibe resposta do assistente
        with st.chat_message("assistant"):
            with st.spinner("Buscando na base de conhecimento..."):
                resultado = _chamar_api_chat(pergunta_usuario)

            if resultado:
                resposta = resultado.get("resposta", "Sem resposta.")
                fontes = resultado.get("fontes", [])
                chunks = resultado.get("chunks_recuperados", 0)

                st.markdown(resposta)

                col1, col2 = st.columns([3, 1])
                with col2:
                    st.caption(f"Trechos consultados: {chunks}")

                if fontes:
                    with st.expander("Fontes consultadas"):
                        for fonte in fontes:
                            st.write(f"- {fonte}")

                st.session_state.mensagens_chat.append({
                    "papel": "assistant",
                    "conteudo": resposta,
                    "fontes": fontes,
                })

    # Botão para limpar histórico
    if st.session_state.mensagens_chat:
        if st.button("Limpar conversa", key="limpar_chat"):
            st.session_state.mensagens_chat = []
            st.rerun()


# ===========================================================================
# ABA UPLOAD
# ===========================================================================

def _processar_upload(arquivo) -> dict | None:
    """Envia arquivo para a API e retorna os dados processados."""
    try:
        resposta = requests.post(
            f"{API_URL}/documents/upload",
            files={
                "arquivo": (
                    arquivo.name,
                    arquivo.getvalue(),
                    arquivo.type or "application/octet-stream",
                )
            },
            timeout=TIMEOUT_UPLOAD,
        )
        if resposta.status_code == 200:
            return resposta.json().get("dados")
        st.error(f"Erro no processamento: {resposta.status_code} — {resposta.text}")
    except requests.exceptions.ConnectionError:
        st.error("Backend indisponível. Verifique se o servidor está em execução.")
    except Exception as erro:
        st.error(f"Erro ao processar arquivo: {erro}")
    return None


def _salvar_documento(dados: dict) -> bool:
    """Envia os dados do documento para salvar no histórico."""
    try:
        resposta = requests.post(
            f"{API_URL}/documents/save",
            json=dados,
            timeout=TIMEOUT_PADRAO,
        )
        if resposta.status_code == 200:
            info = resposta.json()
            st.success(
                f"Documento salvo com sucesso! "
                f"ID: {info['id']} | Categoria: {info['categoria']}"
            )
            return True
        st.error(f"Erro ao salvar: {resposta.text}")
    except Exception as erro:
        st.error(f"Erro: {erro}")
    return False


with aba_upload:
    st.header("Upload de Documento Fiscal")
    st.write(
        "Envie recibos médicos, notas fiscais, comprovantes de educação, "
        "informes de rendimentos e outros documentos para organização automática."
    )

    arquivo_enviado = st.file_uploader(
        "Selecione o arquivo",
        type=["pdf", "txt", "html"],
        help="Formatos aceitos: PDF, TXT, HTML (máx. recomendado: 10 MB)",
    )

    if arquivo_enviado:
        col_btn, col_info = st.columns([1, 3])
        with col_btn:
            processar = st.button("Processar Documento", type="primary", use_container_width=True)

        if processar:
            with st.spinner("Extraindo texto e classificando..."):
                dados_processados = _processar_upload(arquivo_enviado)

            if dados_processados:
                st.session_state.documento_processado = dados_processados
                st.success("Documento processado com sucesso!")

    # Exibe resultado do processamento
    if "documento_processado" in st.session_state and st.session_state.documento_processado:
        dados = st.session_state.documento_processado

        st.subheader("Dados Extraídos")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Categoria Sugerida", dados.get("categoria", "N/A"))
        col2.metric("Data Detectada", dados.get("data_detectada") or "Não encontrada")
        col3.metric("Valor Detectado", dados.get("valor_detectado") or "Não encontrado")
        col4.metric("Emitente", dados.get("emitente_detectado") or "Não identificado")

        with st.expander("Texto Extraído (primeiros 2000 caracteres)"):
            texto_completo = dados.get("texto_extraido", "")
            trecho = texto_completo[:2000]
            if len(texto_completo) > 2000:
                trecho += "\n\n[...texto truncado...]"
            st.text_area(
                label="",
                value=trecho,
                height=200,
                disabled=True,
                label_visibility="collapsed",
            )

        st.divider()
        st.subheader("Salvar no Histórico?")
        st.write(
            "Deseja salvar este documento para consultar no histórico e incluir "
            "no resumo anual?"
        )

        col_salvar, col_descartar = st.columns(2)
        with col_salvar:
            if st.button("Salvar Documento", type="primary", use_container_width=True):
                if _salvar_documento(dados):
                    st.session_state.documento_processado = None
                    st.rerun()
        with col_descartar:
            if st.button("Descartar", use_container_width=True):
                st.session_state.documento_processado = None
                st.rerun()


# ===========================================================================
# ABA HISTÓRICO
# ===========================================================================

def _buscar_categorias() -> list[str]:
    """Recupera categorias disponíveis da API."""
    try:
        resposta = requests.get(f"{API_URL}/documents/categorias", timeout=TIMEOUT_PADRAO)
        if resposta.status_code == 200:
            return resposta.json().get("categorias", [])
    except Exception:
        pass
    return []


def _buscar_historico(params: dict) -> list | None:
    """Consulta o histórico de documentos com filtros."""
    try:
        resposta = requests.get(
            f"{API_URL}/history", params=params, timeout=TIMEOUT_PADRAO
        )
        if resposta.status_code == 200:
            return resposta.json()
        st.error(f"Erro: {resposta.status_code}")
    except requests.exceptions.ConnectionError:
        st.error("Backend indisponível.")
    except Exception as erro:
        st.error(f"Erro: {erro}")
    return None


with aba_historico:
    st.header("Histórico de Documentos")

    # Painel de filtros
    with st.expander("Filtros de busca", expanded=True):
        col_cat, col_nome, col_inicio, col_fim = st.columns(4)

        with col_cat:
            categorias = ["Todas as categorias"] + _buscar_categorias()
            categoria_selecionada = st.selectbox("Categoria", categorias)

        with col_nome:
            nome_busca = st.text_input("Nome do arquivo", placeholder="Ex: recibo_jan")

        with col_inicio:
            data_inicio = st.date_input("Data início", value=None)

        with col_fim:
            data_fim = st.date_input("Data fim", value=None)

    if st.button("Buscar Documentos", type="primary"):
        filtros: dict = {"limite": 100}

        if categoria_selecionada != "Todas as categorias":
            filtros["categoria"] = categoria_selecionada
        if nome_busca:
            filtros["nome"] = nome_busca
        if data_inicio:
            filtros["data_inicio"] = data_inicio.isoformat()
        if data_fim:
            filtros["data_fim"] = data_fim.isoformat()

        with st.spinner("Buscando documentos..."):
            documentos = _buscar_historico(filtros)

        if documentos is not None:
            st.write(f"**{len(documentos)} documento(s) encontrado(s)**")

            if not documentos:
                st.info("Nenhum documento encontrado com os filtros aplicados.")
            else:
                for doc in documentos:
                    criado_em = doc.get("criado_em", "")[:10] if doc.get("criado_em") else "N/A"
                    titulo = f"📄 {doc['nome_arquivo']} — {doc['categoria']} ({criado_em})"

                    with st.expander(titulo):
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.write(f"**Tipo:** `{doc['tipo_arquivo'].upper()}`")
                            st.write(f"**Categoria:** {doc['categoria']}")

                        with col2:
                            st.write(f"**Data detectada:** {doc.get('data_detectada') or '—'}")
                            st.write(f"**Valor:** {doc.get('valor_detectado') or '—'}")

                        with col3:
                            st.write(
                                f"**Emitente:** {doc.get('emitente_detectado') or '—'}"
                            )
                            st.write(f"**Salvo em:** {criado_em}")

                        # Botão de exclusão
                        if st.button(
                            "Excluir do histórico",
                            key=f"excluir_{doc['id']}",
                            type="secondary",
                        ):
                            try:
                                r = requests.delete(
                                    f"{API_URL}/history/{doc['id']}",
                                    timeout=TIMEOUT_PADRAO,
                                )
                                if r.status_code == 200:
                                    st.success("Documento removido.")
                                    st.rerun()
                                else:
                                    st.error("Erro ao remover documento.")
                            except Exception as e:
                                st.error(f"Erro: {e}")


# ===========================================================================
# ABA RESUMO ANUAL
# ===========================================================================

with aba_resumo:
    st.header("Resumo Anual para Declaração do IR")
    st.write(
        "Visualize seus documentos organizados por categoria tributária. "
        "Use este resumo como referência ao preencher a declaração."
    )

    ano_atual = datetime.now().year
    ano_selecionado = st.selectbox(
        "Selecione o ano",
        options=list(range(ano_atual, ano_atual - 6, -1)),
        index=0,
    )

    if st.button("Gerar Resumo", type="primary"):
        with st.spinner("Gerando resumo anual..."):
            try:
                resposta = requests.get(
                    f"{API_URL}/history/summary",
                    params={"ano": ano_selecionado},
                    timeout=TIMEOUT_PADRAO,
                )
            except requests.exceptions.ConnectionError:
                st.error("Backend indisponível.")
                resposta = None

        if resposta and resposta.status_code == 200:
            resumo = resposta.json()

            # Métricas gerais
            col1, col2 = st.columns(2)
            col1.metric("Ano de Referência", resumo["ano"])
            col2.metric("Total de Documentos", resumo["total_documentos"])

            st.divider()

            if not resumo["categorias"]:
                st.info(
                    f"Nenhum documento encontrado para o ano {ano_selecionado}. "
                    "Salve documentos na aba Upload para começar."
                )
            else:
                st.subheader("Documentos por Categoria Tributária")

                # Ícones por categoria
                icones = {
                    "Recibo Médico": "🏥",
                    "Comprovante Educacional": "🎓",
                    "Informe de Rendimentos": "💼",
                    "Nota Fiscal": "🧾",
                    "Previdência Privada": "🏦",
                    "Doações": "❤️",
                    "Pensão Alimentícia": "👨‍👧",
                    "Aluguel": "🏠",
                    "Documento Não Classificado": "📄",
                }

                for categoria, dados_cat in resumo["categorias"].items():
                    icone = icones.get(categoria, "📁")
                    quantidade = dados_cat["quantidade"]
                    titulo_expander = (
                        f"{icone} {categoria} — {quantidade} documento(s)"
                    )

                    with st.expander(titulo_expander, expanded=True):
                        for doc in dados_cat["documentos"]:
                            col_nome, col_data, col_valor, col_emit = st.columns(
                                [3, 2, 2, 3]
                            )
                            col_nome.write(f"📄 {doc['nome']}")
                            col_data.write(doc.get("data_detectada") or "—")
                            col_valor.write(doc.get("valor_detectado") or "—")
                            col_emit.write(doc.get("emitente") or "—")

                        # Exibe valores detectados se disponíveis
                        if dados_cat["valores"]:
                            st.caption(
                                f"Valores detectados: {', '.join(dados_cat['valores'])}"
                            )

        elif resposta:
            st.error(f"Erro ao gerar resumo: {resposta.status_code}")

# ---------------------------------------------------------------------------
# Rodapé
# ---------------------------------------------------------------------------
st.divider()
st.caption(
    "DeclaraAI — Projeto Acadêmico UEA | "
    "Este sistema não substitui a orientação de um contador profissional."
)
