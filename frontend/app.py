"""
Interface web do DeclaraAI construída com Streamlit.

Organizada em 5 abas:
- Chat: perguntas em linguagem natural respondidas pelo pipeline RAG
- Upload: envio e processamento de documentos fiscais
- Histórico: consulta e filtragem dos documentos salvos
- Resumo: visão anual agrupada por categoria tributária
- Avaliação: métricas quantitativas do pipeline RAG
"""

import base64
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
       OCULTA A BARRA PADRÃO DO STREAMLIT (Deploy / Settings)
    ================================================================ */
    [data-testid="stHeader"]  { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }
    #MainMenu                 { display: none !important; }

    /* ================================================================
       FUNDO — branco com degradê suave fixo
    ================================================================ */
    html, body {
        background: #FFFFFF;
    }
    .stApp {
        background: linear-gradient(180deg, #FFFFFF 0%, #FDF5EE 100%) !important;
        background-attachment: fixed !important;
        min-height: 100vh;
        color: #1A1A1A;
    }

    [data-testid="stSidebar"]        { background-color: #F7F0EA; }
    [data-testid="stSidebarContent"] { background-color: #F7F0EA; }

    /* ================================================================
       NAVBAR FIXA — fundo escuro com degradê (logo + abas)
    ================================================================ */
    .navbar-bg {
        position: fixed;
        top: 0; left: 0; right: 0;
        height: 66px;
        background: linear-gradient(90deg, #1A1A1A 0%, #3D1800 55%, #1A1A1A 100%);
        z-index: 9997;
        border-bottom: 2px solid #FF6B35;
    }

    /* Empurra conteúdo abaixo da navbar */
    .main .block-container {
        padding-top: 84px !important;
        padding-left: 6.5rem !important;
        padding-right: 6.5rem !important;
        max-width: 100% !important;
    }

    /* ================================================================
       ABAS — fixas no canto superior direito dentro da navbar
    ================================================================ */
    .stTabs [data-baseweb="tab-list"] {
        position: fixed !important;
        top: 0 !important;
        right: 1.5rem !important;
        height: 66px !important;
        background: transparent !important;
        border: none !important;
        z-index: 9999 !important;
        display: flex !important;
        align-items: center !important;
        padding: 0 !important;
        gap: 2px !important;
    }

    .stTabs [data-baseweb="tab"] {
        height: 66px !important;
        border-radius: 0 !important;
        border-bottom: 3px solid transparent !important;
        padding: 0 0.85rem !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        color: #DDDDDD !important;
        background: transparent !important;
        transition: color 0.15s ease, background-color 0.15s ease;
    }

    /* Aba selecionada — fundo diferenciado com contraste */
    .stTabs [aria-selected="true"] {
        color: #FFD700 !important;
        background-color: rgba(255, 107, 53, 0.25) !important;
        border-radius: 6px !important;
        border-bottom: 3px solid #FF6B35 !important;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: #FF6B35 !important;
        background: rgba(255, 107, 53, 0.12) !important;
        border-radius: 6px !important;
    }

    /* ================================================================
       TIPOGRAFIA
    ================================================================ */
    h1, h2, h3, h4 {
        color: #1A1A1A !important;
        margin-top: 1.6rem !important;
        margin-bottom: 0.85rem !important;
    }

    p, li, .stMarkdown p {
        color: #2A2A2A !important;
        font-size: 1.1rem !important;
        line-height: 1.8 !important;
    }

    label, .stSelectbox label, .stTextInput label,
    .stFileUploader label, .stDateInput label {
        color: #333333 !important;
        font-size: 1.02rem !important;
    }

    .stCaption, caption { color: #666666 !important; font-size: 0.9rem !important; }

    /* ================================================================
       BOTÕES — degradê suave
    ================================================================ */
    .stButton > button[kind="primary"],
    .stButton > button[kind="primary"]:focus,
    .stButton > button[kind="primary"]:active {
        background: linear-gradient(135deg, #D05000 0%, #A03800 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px;
        font-weight: 700;
        font-size: 1rem;
        padding: 0.52rem 1.5rem;
        transition: opacity 0.2s ease;
    }
    .stButton > button[kind="primary"]:hover { opacity: 0.88; }

    .stButton > button[kind="secondary"],
    .stButton > button[kind="secondary"]:focus {
        background: linear-gradient(135deg, #FFD700 0%, #FFC000 100%) !important;
        color: #333333 !important;
        border: none !important;
        border-radius: 8px;
        font-weight: 600;
        font-size: 1rem;
        transition: opacity 0.2s ease;
    }
    .stButton > button[kind="secondary"]:hover { opacity: 0.85; }

    /* Botão de download */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #D05000 0%, #A03800 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
    }
    .stDownloadButton > button:hover { opacity: 0.88; }

    /* ================================================================
       COMPONENTES
    ================================================================ */
    div[data-testid="stExpander"] {
        background-color: #FAFAFA;
        border: 1px solid #E5E5E5;
        border-radius: 10px;
    }
    div[data-testid="stExpander"] summary { color: #C04A00; font-weight: 600; font-size: 1rem; }

    [data-testid="stMetric"] {
        background-color: #FFF8F4;
        border: 1px solid #F0D5C0;
        border-radius: 10px;
        padding: 0.85rem;
    }
    [data-testid="stMetricLabel"] { color: #555555 !important; font-size: 0.9rem; }
    [data-testid="stMetricValue"] { color: #C04A00 !important; font-weight: 700; font-size: 1.4rem !important; }

    .stTextInput > div > div > input,
    .stTextArea textarea,
    .stSelectbox > div > div {
        background-color: #FAFAFA !important;
        border: 1px solid #DDDDDD !important;
        color: #1A1A1A !important;
        border-radius: 8px;
        font-size: 1rem !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea textarea:focus {
        border-color: #C04A00 !important;
        box-shadow: 0 0 0 2px rgba(192, 74, 0, 0.15);
    }

    [data-testid="stChatMessage"] {
        background-color: #F9F9F9;
        border-radius: 12px;
        border: 1px solid #EEEEEE;
        margin-bottom: 8px;
    }

    [data-testid="stChatInput"] textarea {
        background-color: #FAFAFA !important;
        color: #1A1A1A !important;
        border: 1.5px solid #C04A00 !important;
        border-radius: 12px;
        font-size: 1rem !important;
    }

    .stProgress > div > div > div { background-color: #C04A00; }

    hr { border-color: #EEEEEE !important; }

    [data-testid="stFileUploader"] {
        background-color: #FAFAFA;
        border: 2px dashed #C04A00;
        border-radius: 10px;
        padding: 1rem;
    }

    /* ================================================================
       MENSAGENS — verde / vinho / amarelo
    ================================================================ */
    .msg-success {
        background-color: #E8F5E9; border-left: 4px solid #2E7D32;
        color: #1B5E20; padding: 0.75rem 1.1rem;
        border-radius: 0 8px 8px 0; font-weight: 500;
        font-size: 1.05rem; margin: 0.5rem 0;
    }
    .msg-error {
        background-color: #FFEBEE; border-left: 4px solid #C62828;
        color: #7B0000; padding: 0.75rem 1.1rem;
        border-radius: 0 8px 8px 0; font-weight: 500;
        font-size: 1.05rem; margin: 0.5rem 0;
    }
    .msg-warning {
        background-color: #FFFDE7; border-left: 4px solid #F9A825;
        color: #3E3000; padding: 0.75rem 1.1rem;
        border-radius: 0 8px 8px 0; font-weight: 500;
        font-size: 1.05rem; margin: 0.5rem 0;
    }
    .msg-info {
        background-color: #FFF3E0; border-left: 4px solid #C04A00;
        color: #7A2D00; padding: 0.75rem 1.1rem;
        border-radius: 0 8px 8px 0; font-weight: 500;
        font-size: 1.05rem; margin: 0.5rem 0;
    }

    .badge-categoria {
        display: inline-block; background-color: #C04A00;
        color: #ffffff; font-size: 0.82rem; font-weight: 700;
        padding: 2px 10px; border-radius: 20px; margin-left: 6px;
    }

    /* ================================================================
       RODAPÉ — fundo laranja suave
    ================================================================ */
    .footer-bar {
        background-color: #FFF0E0;
        border-top: 1px solid #FFCCA0;
        color: #7A3800;
        text-align: center;
        padding: 0.75rem;
        font-size: 0.9rem;
        font-weight: 500;
        margin-top: 2.5rem;
        border-radius: 8px;
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
# Cabeçalho — logo em PNG embutida em base64 na navbar fixa escura
# O arquivo logo.png está na mesma pasta do app.py (copiado no Dockerfile)
# ---------------------------------------------------------------------------

LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo.png")

if os.path.exists(LOGO_PATH):
    with open(LOGO_PATH, "rb") as _f:
        _logo_b64 = base64.b64encode(_f.read()).decode()
    st.markdown(
        f'<div class="navbar-bg">'
        f'<img src="data:image/png;base64,{_logo_b64}" height="46" '
        f'style="padding-left:2.5rem;padding-top:10px;">'
        f'</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<div class="navbar-bg">'
        '<span style="color:#FF6B35;font-size:1.8rem;font-weight:800;'
        'padding-left:2.5rem;line-height:66px;">🦁 DeclaraAI</span>'
        '</div>',
        unsafe_allow_html=True,
    )

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

    if "mensagens_chat" not in st.session_state:
        st.session_state.mensagens_chat = [
            {
                "papel": "assistant",
                "conteudo": (
                    "Olá! 👋 Sou o **DeclaraAI**, seu assistente para o Imposto de Renda.\n\n"
                    "Pode me perguntar sobre deduções, documentos necessários, prazos, "
                    "categorias tributárias, rendimentos isentos... estou aqui para ajudar! 😊\n\n"
                    "Como posso te ajudar hoje?"
                ),
            }
        ]

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

    # ── Uploads recentes ────────────────────────────────────────────────────
    st.divider()
    st.subheader("Uploads Recentes")

    try:
        _resp_rec = requests.get(
            f"{API_URL}/history", params={"limite": 20}, timeout=TIMEOUT_PADRAO
        )
        _recentes = _resp_rec.json() if _resp_rec.status_code == 200 else []
    except Exception:
        _recentes = []

    if _recentes:
        for _doc in _recentes:
            _criado = (_doc.get("criado_em") or "")[:10] or "N/A"
            st.markdown(
                f"📄 **{_doc['nome_arquivo']}** — "
                f"<span class='badge-categoria'>{_doc['categoria']}</span> "
                f"&nbsp; `{_doc['tipo_arquivo'].upper()}` &nbsp; {_criado}",
                unsafe_allow_html=True,
            )
    else:
        msg_aviso("Nenhum documento enviado ainda.")


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


def _baixar_arquivo_base(nome_arquivo: str) -> bytes | None:
    """Busca os bytes do arquivo da base de conhecimento para download."""
    try:
        r = requests.get(
            f"{API_URL}/knowledge/files/{nome_arquivo}/download",
            timeout=TIMEOUT_PADRAO,
        )
        if r.status_code == 200:
            return r.content
    except Exception:
        pass
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
            # Sem st.rerun() explícito — o clique já dispara um rerun

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
                col_nome, col_tipo, col_tam, col_dl, col_del = st.columns([4, 1, 1, 1, 1])

                with col_nome:
                    st.markdown(f"{icone} **{arq['nome']}**")
                with col_tipo:
                    st.caption(arq["tipo"].upper())
                with col_tam:
                    st.caption(f"{arq['tamanho_kb']} KB")
                with col_dl:
                    _bytes_arq = _baixar_arquivo_base(arq["nome"])
                    if _bytes_arq:
                        st.download_button(
                            label="⬇",
                            data=_bytes_arq,
                            file_name=arq["nome"],
                            mime="application/octet-stream",
                            key=f"dl_base_{arq['nome']}",
                            help="Baixar arquivo",
                            use_container_width=True,
                        )
                with col_del:
                    if st.button(
                        "🗑",
                        key=f"del_base_{arq['nome']}",
                        type="secondary",
                        help="Remover da base",
                        use_container_width=True,
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


def _baixar_texto_documento(doc_id: int) -> bytes | None:
    """Busca o texto extraído de um documento para download."""
    try:
        r = requests.get(f"{API_URL}/history/{doc_id}/download", timeout=TIMEOUT_PADRAO)
        if r.status_code == 200:
            return r.content
    except Exception:
        pass
    return None


_ICONES_CAT = {
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


def _buscar_nomes_documentos() -> list[str]:
    """Retorna lista de nomes únicos de documentos no histórico."""
    try:
        r = requests.get(f"{API_URL}/history", params={"limite": 500}, timeout=TIMEOUT_PADRAO)
        if r.status_code == 200:
            return sorted({d["nome_arquivo"] for d in r.json()})
    except Exception:
        pass
    return []


with aba_historico:
    col_h_titulo, col_h_reload = st.columns([11, 1])
    with col_h_titulo:
        st.header("Histórico de Documentos")
    with col_h_reload:
        st.write("")  # alinhamento vertical
        if st.button("🔄", key="btn_reload_hist", help="Atualizar Histórico"):
            for _k in ("hist_documentos", "hist_nomes"):
                if _k in st.session_state:
                    del st.session_state[_k]

    # Carrega lista de nomes para o filtro
    if "hist_nomes" not in st.session_state:
        st.session_state["hist_nomes"] = _buscar_nomes_documentos()

    with st.expander("Filtros", expanded=False):
        col_cat, col_nome, col_inicio, col_fim = st.columns(4)
        with col_cat:
            categorias_disp = ["Todas as categorias"] + _buscar_categorias()
            hist_cat = st.selectbox("Categoria", categorias_disp, key="hist_cat")
        with col_nome:
            nomes_disp = ["Todos os arquivos"] + st.session_state["hist_nomes"]
            hist_nome_sel = st.selectbox("Nome do arquivo", nomes_disp, key="hist_nome_sel")
        with col_inicio:
            hist_inicio = st.date_input("Data início", value=None, key="hist_inicio")
        with col_fim:
            hist_fim = st.date_input("Data fim", value=None, key="hist_fim")

        if st.button("Aplicar Filtros", type="secondary"):
            if "hist_documentos" in st.session_state:
                del st.session_state["hist_documentos"]

    # Carrega documentos na sessão para não perder entre reruns
    if "hist_documentos" not in st.session_state:
        filtros: dict = {"limite": 200}
        if st.session_state.get("hist_cat", "Todas as categorias") != "Todas as categorias":
            filtros["categoria"] = st.session_state["hist_cat"]
        _nome_sel = st.session_state.get("hist_nome_sel", "Todos os arquivos")
        if _nome_sel and _nome_sel != "Todos os arquivos":
            filtros["nome"] = _nome_sel
        if st.session_state.get("hist_inicio"):
            filtros["data_inicio"] = st.session_state["hist_inicio"].isoformat()
        if st.session_state.get("hist_fim"):
            filtros["data_fim"] = st.session_state["hist_fim"].isoformat()
        st.session_state["hist_documentos"] = _buscar_historico(filtros) or []

    documentos = st.session_state["hist_documentos"]

    # ── Dashboard: totais por categoria ──────────────────────────────────
    if documentos:
        contagem: dict = {}
        for d in documentos:
            cat = d.get("categoria") or "Documento Não Classificado"
            contagem[cat] = contagem.get(cat, 0) + 1

        st.subheader("Resumo")
        metricas = [("Total de Documentos", len(documentos), "📁")] + [
            (cat, qtd, _ICONES_CAT.get(cat, "📁")) for cat, qtd in sorted(contagem.items())
        ]
        cols_met = st.columns(min(len(metricas), 4))
        for idx, (label, valor, icone) in enumerate(metricas):
            cols_met[idx % 4].metric(f"{icone} {label}", valor)

        st.divider()
        st.subheader("Documentos por Categoria")

        for cat, qtd in sorted(contagem.items()):
            icone = _ICONES_CAT.get(cat, "📁")
            docs_cat = [d for d in documentos if (d.get("categoria") or "Documento Não Classificado") == cat]

            with st.expander(f"{icone} {cat} — {qtd} documento(s)", expanded=False):
                for doc in docs_cat:
                    criado_em = (doc.get("criado_em") or "")[:10] or "N/A"
                    col_info, col_acoes = st.columns([3, 1])

                    with col_info:
                        st.markdown(
                            f"**📄 {doc['nome_arquivo']}**  \n"
                            f"Tipo: `{doc['tipo_arquivo'].upper()}` &nbsp;|&nbsp; "
                            f"Data detectada: {doc.get('data_detectada') or '—'} &nbsp;|&nbsp; "
                            f"Valor: {doc.get('valor_detectado') or '—'}  \n"
                            f"Emitente: {doc.get('emitente_detectado') or '—'} &nbsp;|&nbsp; "
                            f"Salvo em: {criado_em}"
                        )

                    with col_acoes:
                        texto_bytes = _baixar_texto_documento(doc["id"])
                        nome_dl = doc["nome_arquivo"].rsplit(".", 1)[0] + "_extraido.txt"
                        if texto_bytes:
                            st.download_button(
                                label="⬇ Baixar",
                                data=texto_bytes,
                                file_name=nome_dl,
                                mime="text/plain",
                                key=f"dl_{doc['id']}",
                                use_container_width=True,
                            )
                        if st.button(
                            "🗑 Excluir",
                            key=f"excluir_{doc['id']}",
                            type="secondary",
                            use_container_width=True,
                        ):
                            try:
                                r = requests.delete(
                                    f"{API_URL}/history/{doc['id']}",
                                    timeout=TIMEOUT_PADRAO,
                                )
                                if r.status_code == 200:
                                    msg_sucesso("Documento removido.")
                                    if "hist_documentos" in st.session_state:
                                        del st.session_state["hist_documentos"]
                                    st.rerun()
                                else:
                                    msg_erro("Erro ao remover documento.")
                            except Exception as e:
                                msg_erro(f"Erro: {e}")

                    st.divider()
    else:
        msg_aviso("Nenhum documento encontrado. Envie documentos na aba Upload.")


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
