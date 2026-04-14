"""
Interface web do DeclaraAI construída com Streamlit.

Organizada em 5 abas:
- Chat: perguntas em linguagem natural respondidas pelo pipeline RAG
- Upload: envio e processamento de documentos fiscais
- Histórico: consulta e filtragem dos documentos salvos
- Resumo: visão anual agrupada por categoria tributária
- Avaliação: métricas quantitativas do pipeline RAG
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
    page_icon="🦁",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# CSS customizado — paleta: laranja (#FF6B35), amarelo (#FFD700), preto, branco
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    /* ================================================================
       FUNDO — degradê radial suave, escuro neutro sem cast de cor
    ================================================================ */
    .stApp {
        background: radial-gradient(ellipse at 50% 0%, #1e1e1e 0%, #0D0D0D 65%);
        color: #E8E8E8;
    }

    [data-testid="stSidebar"]        { background-color: #111111; }
    [data-testid="stSidebarContent"] { background-color: #111111; }

    /* ================================================================
       MARGENS LATERAIS — 2x maior; sem padding-top extra
    ================================================================ */
    .main .block-container {
        padding-top: 2rem !important;
        padding-left: 5rem !important;
        padding-right: 5rem !important;
        max-width: 100% !important;
    }

    /* ================================================================
       CABEÇALHO — logo inline, sem altura forçada
    ================================================================ */
    .bloco-logo {
        display: flex;
        align-items: center;
        padding-bottom: 0;
        margin-bottom: 0;
    }

    /* ================================================================
       ABAS — estilo underline, alinhadas à direita
    ================================================================ */
    .stTabs [data-baseweb="tab-list"] {
        background-color: transparent;
        border-radius: 0;
        padding: 0;
        gap: 0;
        border-bottom: 1px solid #2a2a2a;
        justify-content: flex-end;
    }

    .stTabs [data-baseweb="tab"] {
        font-size: 0.92rem;
        font-weight: 600;
        color: #CCCCCC;
        border-radius: 0;
        padding: 0.65rem 1.1rem;
        background-color: transparent;
        border-bottom: 3px solid transparent;
        margin-bottom: -1px;
        transition: color 0.18s ease, border-color 0.18s ease;
    }

    .stTabs [aria-selected="true"] {
        background-color: transparent !important;
        color: #FF6B35 !important;
        border-bottom: 3px solid #FF6B35 !important;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: #FFD700 !important;
        background-color: rgba(255, 215, 0, 0.04) !important;
    }

    /* ================================================================
       TIPOGRAFIA — fontes mais brancas, parágrafos maiores
    ================================================================ */
    h1, h2, h3, h4 {
        color: #F5F5F5 !important;
        margin-top: 1.6rem !important;
        margin-bottom: 0.85rem !important;
    }

    p, li, .stMarkdown p {
        color: #DEDEDE !important;
        font-size: 1.05rem !important;
        line-height: 1.7 !important;
    }

    label, .stSelectbox label, .stTextInput label,
    .stFileUploader label, .stDateInput label {
        color: #CCCCCC !important;
        font-size: 1rem !important;
    }

    .stCaption, caption { color: #AAAAAA !important; }

    /* ================================================================
       BOTÕES
    ================================================================ */
    .stButton > button[kind="primary"] {
        background-color: #FF6B35;
        color: #ffffff;
        border: none;
        border-radius: 8px;
        font-weight: 700;
        padding: 0.5rem 1.2rem;
        transition: background-color 0.2s ease;
    }
    .stButton > button[kind="primary"]:hover { background-color: #e55a25; }

    .stButton > button[kind="secondary"] {
        background-color: #1a1a1a;
        color: #FFD700;
        border: 1.5px solid #FFD700;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .stButton > button[kind="secondary"]:hover {
        background-color: #FFD700;
        color: #0D0D0D;
    }

    /* ================================================================
       COMPONENTES
    ================================================================ */
    div[data-testid="stExpander"] {
        background-color: #1a1a1a;
        border: 1px solid #333333;
        border-radius: 10px;
    }
    div[data-testid="stExpander"] summary { color: #FFD700; font-weight: 600; }

    [data-testid="stMetric"] {
        background-color: #1a1a1a;
        border: 1px solid #333333;
        border-radius: 10px;
        padding: 0.8rem;
    }
    [data-testid="stMetricLabel"] { color: #BBBBBB !important; font-size: 0.85rem; }
    [data-testid="stMetricValue"] { color: #FFD700 !important; font-weight: 700; }

    .stTextInput > div > div > input,
    .stTextArea textarea,
    .stSelectbox > div > div {
        background-color: #1a1a1a !important;
        border: 1px solid #333333 !important;
        color: #F0F0F0 !important;
        border-radius: 8px;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea textarea:focus {
        border-color: #FF6B35 !important;
        box-shadow: 0 0 0 2px rgba(255, 107, 53, 0.25);
    }

    [data-testid="stChatMessage"] {
        background-color: #1a1a1a;
        border-radius: 12px;
        border: 1px solid #2a2a2a;
        margin-bottom: 8px;
    }

    [data-testid="stChatInput"] textarea {
        background-color: #1a1a1a !important;
        color: #F5F5F5 !important;
        border: 1.5px solid #FF6B35 !important;
        border-radius: 12px;
    }

    .stProgress > div > div > div { background-color: #FF6B35; }

    hr { border-color: #2a2a2a !important; }

    [data-testid="stFileUploader"] {
        background-color: #1a1a1a;
        border: 2px dashed #FF6B35;
        border-radius: 10px;
        padding: 1rem;
    }

    /* ================================================================
       MENSAGENS DE ESTADO — alto contraste
    ================================================================ */
    .msg-success {
        background-color: #0a2e1a; border-left: 4px solid #00c853;
        color: #a5f0c0; padding: 0.7rem 1rem;
        border-radius: 0 8px 8px 0; font-weight: 500;
        font-size: 1.02rem; margin: 0.5rem 0;
    }
    .msg-error {
        background-color: #2e0a0a; border-left: 4px solid #FF3B3B;
        color: #f5a5a5; padding: 0.7rem 1rem;
        border-radius: 0 8px 8px 0; font-weight: 500;
        font-size: 1.02rem; margin: 0.5rem 0;
    }
    .msg-warning {
        background-color: #2a1f00; border-left: 4px solid #FFD700;
        color: #ffe080; padding: 0.7rem 1rem;
        border-radius: 0 8px 8px 0; font-weight: 500;
        font-size: 1.02rem; margin: 0.5rem 0;
    }
    .msg-info {
        background-color: #0a1e2e; border-left: 4px solid #FF6B35;
        color: #ffc4a8; padding: 0.7rem 1rem;
        border-radius: 0 8px 8px 0; font-weight: 500;
        font-size: 1.02rem; margin: 0.5rem 0;
    }

    .badge-categoria {
        display: inline-block; background-color: #FF6B35;
        color: #ffffff; font-size: 0.78rem; font-weight: 700;
        padding: 2px 10px; border-radius: 20px; margin-left: 6px;
    }

    /* ================================================================
       RODAPÉ
    ================================================================ */
    .footer-bar {
        background-color: #111111;
        border-top: 1px solid #2a2a2a;
        color: #888888;
        text-align: center;
        padding: 0.7rem;
        font-size: 0.85rem;
        border-radius: 0 0 8px 8px;
        margin-top: 2.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Helpers de mensagem com contraste adequado
# ---------------------------------------------------------------------------

def msg_sucesso(texto: str) -> None:
    st.markdown(f'<div class="msg-success">✅ {texto}</div>', unsafe_allow_html=True)


def msg_erro(texto: str) -> None:
    st.markdown(f'<div class="msg-error">❌ {texto}</div>', unsafe_allow_html=True)


def msg_aviso(texto: str) -> None:
    st.markdown(f'<div class="msg-warning">⚠️ {texto}</div>', unsafe_allow_html=True)


def msg_info(texto: str) -> None:
    st.markdown(f'<div class="msg-info">ℹ️ {texto}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Cabeçalho — logo à esquerda (SVG inline), espaço vazio à direita
# As abas ficam logo abaixo alinhadas à direita via CSS (justify-content: flex-end)
# ---------------------------------------------------------------------------

LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "diagrams", "logo.svg")

col_logo, col_vazio = st.columns([2, 3])
with col_logo:
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "r") as f:
            _svg = f.read()
        # Reduz para exibição no cabeçalho mantendo proporção (460×132 → 230×66)
        _svg_header = _svg.replace('width="460"', 'width="230"').replace('height="132"', 'height="66"')
        st.markdown(f'<div class="bloco-logo">{_svg_header}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<span style="font-size:2.8rem;">🦁</span>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Abas principais — renderizadas logo abaixo da logo, alinhadas à direita via CSS
# ---------------------------------------------------------------------------

aba_chat, aba_upload, aba_base, aba_historico, aba_resumo, aba_avaliacao = st.tabs(
    ["💬 Chat", "📄 Upload", "🗂️ Base de Conhecimento", "📚 Histórico", "📊 Resumo Anual", "🔬 Avaliação"]
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
        msg_erro(f"Erro da API: {resposta.status_code} — {resposta.text}")
    except requests.exceptions.ConnectionError:
        msg_erro(
            "Não foi possível conectar ao servidor. "
            "Verifique se o backend está rodando em: " + API_URL
        )
    except requests.exceptions.Timeout:
        msg_aviso(
            "O modelo demorou demais para responder. "
            "Certifique-se de que o Ollama está carregado e tente novamente."
        )
    except Exception as erro:
        msg_erro(f"Erro inesperado: {erro}")
    return None


with aba_chat:
    st.header("Chat com Assistente RAG")
    msg_info(
        "Faça perguntas sobre imposto de renda em linguagem natural. "
        "O assistente busca respostas na base de conhecimento tributário."
    )

    if "mensagens_chat" not in st.session_state:
        st.session_state.mensagens_chat = []

    for mensagem in st.session_state.mensagens_chat:
        with st.chat_message(mensagem["papel"]):
            st.markdown(mensagem["conteudo"])
            if mensagem.get("fontes"):
                with st.expander("Fontes consultadas"):
                    for fonte in mensagem["fontes"]:
                        st.write(f"- {fonte}")

    pergunta_usuario = st.chat_input("Digite sua dúvida sobre IR...")

    if pergunta_usuario:
        with st.chat_message("user"):
            st.markdown(pergunta_usuario)
        st.session_state.mensagens_chat.append(
            {"papel": "user", "conteudo": pergunta_usuario}
        )

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
        msg_erro(f"Erro no processamento: {resposta.status_code} — {resposta.text}")
    except requests.exceptions.ConnectionError:
        msg_erro("Backend indisponível. Verifique se o servidor está em execução.")
    except Exception as erro:
        msg_erro(f"Erro ao processar arquivo: {erro}")
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
            msg_sucesso(
                f"Documento salvo! ID: {info['id']} | Categoria: {info['categoria']}"
            )
            return True
        msg_erro(f"Erro ao salvar: {resposta.text}")
    except Exception as erro:
        msg_erro(f"Erro: {erro}")
    return False


with aba_upload:
    st.header("Upload de Documento Fiscal")
    msg_info(
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
                msg_sucesso("Documento processado com sucesso!")

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
# ABA BASE DE CONHECIMENTO
# ===========================================================================

def _listar_arquivos_base() -> dict | None:
    """Consulta a API para listar os arquivos da base de conhecimento."""
    try:
        resposta = requests.get(f"{API_URL}/knowledge/files", timeout=TIMEOUT_PADRAO)
        if resposta.status_code == 200:
            return resposta.json()
        msg_erro(f"Erro ao listar arquivos: {resposta.status_code}")
    except requests.exceptions.ConnectionError:
        msg_erro("Backend indisponível.")
    except Exception as erro:
        msg_erro(f"Erro: {erro}")
    return None


def _enviar_para_base(arquivo) -> dict | None:
    """Envia arquivo para a base de conhecimento via API."""
    try:
        resposta = requests.post(
            f"{API_URL}/knowledge/upload",
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
            return resposta.json()
        msg_erro(f"Erro no upload: {resposta.status_code} — {resposta.text}")
    except requests.exceptions.ConnectionError:
        msg_erro("Backend indisponível.")
    except requests.exceptions.Timeout:
        msg_aviso("O servidor demorou demais. Tente novamente.")
    except Exception as erro:
        msg_erro(f"Erro inesperado: {erro}")
    return None


def _remover_arquivo_base(nome_arquivo: str) -> bool:
    """Remove um arquivo da base de conhecimento via API."""
    try:
        resposta = requests.delete(
            f"{API_URL}/knowledge/files/{nome_arquivo}",
            timeout=TIMEOUT_PADRAO,
        )
        if resposta.status_code == 200:
            return True
        msg_erro(f"Erro ao remover: {resposta.status_code} — {resposta.text}")
    except Exception as erro:
        msg_erro(f"Erro: {erro}")
    return False


with aba_base:
    st.header("Base de Conhecimento")
    msg_info(
        "Gerencie os documentos de referência que o assistente usa para responder perguntas. "
        "Adicione PDFs, TXTs ou HTMLs com conteúdo fiscal (guias, instruções, tabelas da Receita Federal)."
    )

    # -----------------------------------------------------------------------
    # Seção: upload de novo documento
    # -----------------------------------------------------------------------
    st.subheader("Adicionar Documento à Base")

    arquivo_base = st.file_uploader(
        "Selecione o arquivo de referência",
        type=["pdf", "txt", "html"],
        key="uploader_base",
        help="Formatos aceitos: PDF, TXT, HTML. Ex: guia da Receita Federal, tabela de alíquotas.",
    )

    if arquivo_base:
        col_btn_base, col_info_base = st.columns([1, 3])
        with col_btn_base:
            enviar = st.button(
                "Adicionar à Base",
                type="primary",
                use_container_width=True,
                key="btn_enviar_base",
            )
        with col_info_base:
            st.caption(
                f"Arquivo selecionado: **{arquivo_base.name}** "
                f"({round(arquivo_base.size / 1024, 1)} KB)"
            )

        if enviar:
            with st.spinner("Salvando e re-indexando a base de conhecimento..."):
                resultado = _enviar_para_base(arquivo_base)

            if resultado:
                msg_sucesso(
                    f"'{resultado['arquivo']}' adicionado! "
                    f"Base re-indexada com {resultado['chunks_indexados']} trechos."
                )
                # Invalida o cache da listagem para forçar recarga
                if "dados_base" in st.session_state:
                    del st.session_state["dados_base"]
                st.rerun()

    st.divider()

    # -----------------------------------------------------------------------
    # Seção: arquivos já na base
    # -----------------------------------------------------------------------
    st.subheader("Arquivos na Base de Conhecimento")

    col_refresh, _ = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 Atualizar lista", key="btn_refresh_base"):
            if "dados_base" in st.session_state:
                del st.session_state["dados_base"]
            st.rerun()

    if "dados_base" not in st.session_state:
        with st.spinner("Carregando lista de arquivos..."):
            st.session_state.dados_base = _listar_arquivos_base()

    dados_base = st.session_state.get("dados_base")

    if dados_base:
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Arquivos na Base", dados_base.get("total_arquivos", 0))
        col_m2.metric("Trechos Indexados (chunks)", dados_base.get("chunks_indexados", 0))

        st.write("")

        arquivos_base = dados_base.get("arquivos", [])
        if not arquivos_base:
            msg_aviso(
                "Nenhum arquivo encontrado na base de conhecimento. "
                "Use o formulário acima para adicionar o primeiro documento."
            )
        else:
            icones_tipo = {"pdf": "📕", "txt": "📄", "html": "🌐", "htm": "🌐"}

            for arq in arquivos_base:
                icone = icones_tipo.get(arq["tipo"], "📁")
                col_nome, col_tipo, col_tam, col_del = st.columns([4, 1, 1, 1])

                with col_nome:
                    st.markdown(f"{icone} **{arq['nome']}**")
                with col_tipo:
                    st.caption(arq["tipo"].upper())
                with col_tam:
                    st.caption(f"{arq['tamanho_kb']} KB")
                with col_del:
                    if st.button(
                        "Remover",
                        key=f"del_base_{arq['nome']}",
                        type="secondary",
                    ):
                        with st.spinner(f"Removendo '{arq['nome']}'..."):
                            removido = _remover_arquivo_base(arq["nome"])
                        if removido:
                            msg_sucesso(f"'{arq['nome']}' removido da base.")
                            if "dados_base" in st.session_state:
                                del st.session_state["dados_base"]
                            st.rerun()

    elif dados_base is not None:
        msg_aviso("Nenhum arquivo na base de conhecimento.")


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
        msg_erro(f"Erro: {resposta.status_code}")
    except requests.exceptions.ConnectionError:
        msg_erro("Backend indisponível.")
    except Exception as erro:
        msg_erro(f"Erro: {erro}")
    return None


with aba_historico:
    st.header("Histórico de Documentos")

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
                msg_aviso("Nenhum documento encontrado com os filtros aplicados.")
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
                            st.write(f"**Emitente:** {doc.get('emitente_detectado') or '—'}")
                            st.write(f"**Salvo em:** {criado_em}")

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
                                    msg_sucesso("Documento removido.")
                                    st.rerun()
                                else:
                                    msg_erro("Erro ao remover documento.")
                            except Exception as e:
                                msg_erro(f"Erro: {e}")


# ===========================================================================
# ABA RESUMO ANUAL
# ===========================================================================

with aba_resumo:
    st.header("Resumo Anual para Declaração do IR")
    msg_info(
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
                msg_erro("Backend indisponível.")
                resposta = None

        if resposta and resposta.status_code == 200:
            resumo = resposta.json()

            col1, col2 = st.columns(2)
            col1.metric("Ano de Referência", resumo["ano"])
            col2.metric("Total de Documentos", resumo["total_documentos"])

            st.divider()

            if not resumo["categorias"]:
                msg_aviso(
                    f"Nenhum documento encontrado para o ano {ano_selecionado}. "
                    "Salve documentos na aba Upload para começar."
                )
            else:
                st.subheader("Documentos por Categoria Tributária")

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
                    titulo_expander = f"{icone} {categoria} — {quantidade} documento(s)"

                    with st.expander(titulo_expander, expanded=True):
                        for doc in dados_cat["documentos"]:
                            col_nome, col_data, col_valor, col_emit = st.columns([3, 2, 2, 3])
                            col_nome.write(f"📄 {doc['nome']}")
                            col_data.write(doc.get("data_detectada") or "—")
                            col_valor.write(doc.get("valor_detectado") or "—")
                            col_emit.write(doc.get("emitente") or "—")

                        if dados_cat["valores"]:
                            st.caption(
                                f"Valores detectados: {', '.join(dados_cat['valores'])}"
                            )

        elif resposta:
            msg_erro(f"Erro ao gerar resumo: {resposta.status_code}")


# ===========================================================================
# ABA AVALIAÇÃO
# ===========================================================================

def _exibir_gauge(label: str, valor: float, maximo: float = 100.0) -> None:
    """Exibe barra de progresso com legenda colorida."""
    pct = min(valor / maximo, 1.0)
    if pct >= 0.7:
        icone = "🟢"
    elif pct >= 0.4:
        icone = "🟡"
    else:
        icone = "🔴"
    st.markdown(f"**{label}:** `{valor:.1f}` / `{maximo:.0f}` {icone}")
    st.progress(pct)


with aba_avaliacao:
    st.header("Avaliação do Pipeline RAG")
    msg_info(
        "Métricas quantitativas para validar a qualidade da recuperação semântica "
        "e das respostas geradas pelo DeclaraAI."
    )

    with st.expander("ℹ️ Como funciona a avaliação?", expanded=False):
        st.markdown(
            """
**Métricas implementadas (inspiradas no RAGAS):**

| Métrica | Descrição |
|---|---|
| **Taxa de Recuperação** | % de perguntas com ao menos 1 chunk recuperado |
| **Score Médio de Contexto** | Similaridade cosseno média dos chunks retornados (0–1) |
| **Cobertura de Keywords** | % de termos esperados presentes na resposta gerada |

**Modos de avaliação:**
- **Recuperação (rápido):** testa apenas o retriever, sem chamar o LLM
- **Pipeline completo:** testa recuperação + geração via Ollama (mais lento)

8 perguntas cobrindo: obrigatoriedade, deduções médicas, educação, modalidades,
previdência, penalidades, autônomos e dependentes.
            """
        )

    if st.button("Ver Casos de Teste", key="btn_casos"):
        try:
            resp = requests.get(f"{API_URL}/evaluation/casos-teste", timeout=TIMEOUT_PADRAO)
            if resp.status_code == 200:
                dados = resp.json()
                st.write(f"**{dados['total']} casos de teste disponíveis:**")
                for caso in dados["casos_teste"]:
                    st.write(
                        f"**{caso['id']}.** [{caso['categoria']}] {caso['pergunta']} "
                        f"*(keywords: {caso['total_keywords']})*"
                    )
        except Exception as e:
            msg_erro(f"Erro: {e}")

    st.divider()

    col_rec, col_full = st.columns(2)

    with col_rec:
        st.subheader("Recuperação Semântica")
        st.caption("Rápido · Não requer Ollama")
        if st.button("Avaliar Recuperação", type="primary", use_container_width=True):
            with st.spinner("Avaliando recuperação..."):
                try:
                    resp = requests.post(f"{API_URL}/evaluation/recuperacao", timeout=120)
                except requests.exceptions.ConnectionError:
                    msg_erro("Backend indisponível.")
                    resp = None

            if resp and resp.status_code == 200:
                st.session_state.resultado_recuperacao = resp.json()
            elif resp:
                msg_erro(f"Erro {resp.status_code}: {resp.text[:200]}")

        if "resultado_recuperacao" in st.session_state:
            dados = st.session_state.resultado_recuperacao
            msg_sucesso("Avaliação concluída!")

            _exibir_gauge("Taxa de Recuperação (%)", dados.get("taxa_recuperacao_pct", 0))
            st.metric(
                "Score Médio de Contexto",
                f"{dados.get('score_medio_contexto', 0):.4f}",
                help="Similaridade cosseno média (0–1). Quanto maior, mais relevantes os chunks.",
            )
            st.metric("Chunks Indexados", dados.get("chunks_indexados", 0))
            st.metric(
                "Casos sem Contexto",
                dados.get("casos_sem_contexto", 0),
                delta=f"-{dados.get('casos_sem_contexto', 0)} falhas",
                delta_color="inverse",
            )

            msg_info(f"**Interpretação:** {dados.get('interpretacao', '')}")

            if dados.get("analise_falhas"):
                with st.expander("Casos de Falha"):
                    for falha in dados["analise_falhas"]:
                        st.write(f"- **{falha['categoria']}:** {falha['pergunta']}")

            with st.expander("Resultados Detalhados"):
                for r in dados.get("resultados", []):
                    st.markdown(
                        f"**{r['id']}. {r['pergunta']}**  \n"
                        f"Chunks: `{r['chunks_recuperados']}` | "
                        f"Score: `{r['score_medio_contexto']:.4f}` | "
                        f"{'✅' if r['contexto_encontrado'] else '❌'}"
                    )

    with col_full:
        st.subheader("Pipeline Completo")
        st.caption("Requer Ollama ativo · Pode demorar")
        if st.button("Avaliar Pipeline Completo", type="secondary", use_container_width=True):
            with st.spinner(
                "Executando avaliação completa (recuperação + LLM)... "
                "Isso pode levar alguns minutos."
            ):
                try:
                    resp = requests.post(f"{API_URL}/evaluation/completa", timeout=600)
                except requests.exceptions.ConnectionError:
                    msg_erro("Backend indisponível.")
                    resp = None
                except requests.exceptions.Timeout:
                    msg_aviso("Timeout — tente novamente ou verifique o Ollama.")
                    resp = None

            if resp and resp.status_code == 200:
                st.session_state.resultado_completo = resp.json()
            elif resp:
                msg_erro(f"Erro {resp.status_code}: {resp.text[:200]}")

        if "resultado_completo" in st.session_state:
            dados = st.session_state.resultado_completo
            msg_sucesso("Avaliação concluída!")

            _exibir_gauge("Taxa de Recuperação (%)", dados.get("taxa_recuperacao_pct", 0))
            _exibir_gauge("Cobertura de Keywords (%)", dados.get("media_cobertura_keywords_pct", 0))
            st.metric("Score Médio de Contexto", f"{dados.get('score_medio_contexto', 0):.4f}")
            st.metric("Casos com Falha", dados.get("casos_com_falha", 0), delta_color="inverse")

            msg_info(f"**Interpretação:** {dados.get('interpretacao', '')}")

            if dados.get("analise_falhas"):
                with st.expander("Análise de Falhas (cobertura < 50%)"):
                    for falha in dados["analise_falhas"]:
                        st.write(
                            f"- **{falha['categoria']}** — {falha['pergunta']}  \n"
                            f"  Cobertura: `{falha['cobertura_pct']:.1f}%`"
                        )

            with st.expander("Resultados Detalhados por Pergunta"):
                for r in dados.get("resultados", []):
                    status = "✅" if not r.get("falha") else "⚠️"
                    st.markdown(
                        f"**{status} {r['id']}. [{r['categoria']}]** {r['pergunta']}  \n"
                        f"Score: `{r['score_medio_contexto']:.4f}` | "
                        f"Cobertura: `{r['cobertura_keywords_pct']:.1f}%` | "
                        f"Chunks: `{r['chunks_recuperados']}`"
                    )
                    if r.get("resposta_preview"):
                        st.caption(f"Resposta: {r['resposta_preview']}...")
                    st.divider()


# ---------------------------------------------------------------------------
# Rodapé
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="footer-bar">'
    "DeclaraAI - Assistente Inteligente | "
    "Este sistema não substitui a orientação de um contador profissional."
    "</div>",
    unsafe_allow_html=True,
)
