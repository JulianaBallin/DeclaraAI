<h1 align="center">🤖 DeclaraAI</h1>

<p align="center">
  <img src="https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExcHRiNnd1OTJ5YXlmMWtsNWJsZGI0ZnA5NmNnMXQzbHJjYWhoamRwaSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/5fpKNaivstvfmpejxd/giphy.gif" width="260">
</p>

<p align="center">
  Assistente inteligente com <strong>RAG</strong> para organização de documentos e apoio à declaração do imposto de renda.<br>
  <em>Projeto Acadêmico — UEA • Disciplina de RAG</em>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/python-3.11-blue?style=for-the-badge&logo=python">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.111-green?style=for-the-badge&logo=fastapi">
  <img alt="Streamlit" src="https://img.shields.io/badge/Streamlit-1.35-red?style=for-the-badge&logo=streamlit">
  <img alt="ChromaDB" src="https://img.shields.io/badge/ChromaDB-0.5-orange?style=for-the-badge">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-✔-blue?style=for-the-badge&logo=docker">
</p>

---

## Descrição

O **DeclaraAI** é um Micro SaaS com pipeline **RAG (Retrieval-Augmented Generation)** que auxilia usuários leigos na organização de documentos fiscais e na compreensão do processo de declaração do IRPF. O sistema processa documentos enviados pelo usuário (recibos, notas fiscais, informes), classifica-os automaticamente por categoria tributária e responde dúvidas com base em uma base de conhecimento estruturada.

---

## Funcionalidades

| Funcionalidade | Descrição |
|---|---|
| **Chat RAG** | Perguntas em linguagem natural respondidas com base na base de conhecimento tributário |
| **Upload de documentos** | Processamento de PDF, TXT e HTML com extração automática de dados |
| **Classificação tributária** | Categorização inteligente por tipo de documento fiscal |
| **Histórico** | Armazenamento e consulta com filtros por categoria, nome e período |
| **Resumo anual** | Organização por categoria para facilitar o preenchimento da declaração |

---

## Arquitetura

```
Usuário → Streamlit (8501)
              ↓
         FastAPI (8000)
         ├── Chat RAG
         │   ├── ChromaDB (busca semântica)
         │   └── Ollama (geração de resposta)
         ├── Upload & Classificação
         │   ├── Extração (pdfplumber / BeautifulSoup)
         │   └── Classificação por palavras-chave
         └── Histórico
             └── SQLite (SQLAlchemy)
```

### Pipeline RAG

```
[Documentos] → [Loader] → [Chunker 600/80] → [Embeddings MiniLM] → [ChromaDB]
                                                                          ↓
[Pergunta] ──────────────────────────────────────────────────────→ [Retriever]
                                                                          ↓
                                                              [Contexto + Prompt]
                                                                          ↓
                                                                   [Ollama LLM]
                                                                          ↓
                                                                    [Resposta]
```

---

## Estrutura do Projeto

```
DeclaraAI/
├── backend/
│   ├── app/
│   │   ├── main.py                    # Ponto de entrada FastAPI
│   │   ├── api/
│   │   │   ├── routes_chat.py         # POST /chat, POST /ingest, GET /status
│   │   │   ├── routes_documents.py    # POST /documents/upload, POST /documents/save
│   │   │   └── routes_history.py      # GET /history, GET /history/summary
│   │   ├── core/
│   │   │   ├── config.py              # Configurações via pydantic-settings
│   │   │   └── database.py            # SQLAlchemy + SQLite
│   │   ├── models/
│   │   │   └── document.py            # ORM: tabela de documentos
│   │   ├── schemas/
│   │   │   └── document.py            # Schemas Pydantic de entrada/saída
│   │   ├── services/
│   │   │   ├── extraction_service.py  # Extração de texto e metadados
│   │   │   ├── classification_service.py  # Classificação tributária
│   │   │   ├── history_service.py     # Persistência no SQLite
│   │   │   └── rag_service.py         # Orquestrador do pipeline RAG
│   │   ├── rag/
│   │   │   ├── loader.py              # Carregamento de documentos
│   │   │   ├── chunker.py             # Fragmentação com overlap
│   │   │   ├── embeddings.py          # sentence-transformers (singleton)
│   │   │   ├── vector_store.py        # ChromaDB (CRUD vetorial)
│   │   │   ├── retriever.py           # Busca semântica + estrutura re-ranking
│   │   │   └── generator.py           # Geração via Ollama
│   │   └── utils/
│   │       └── file_parsers.py        # Parsers PDF, TXT, HTML
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app.py                         # Interface Streamlit (4 abas)
│   ├── requirements.txt
│   └── Dockerfile
├── data/
│   ├── uploads/                       # Documentos enviados pelos usuários
│   ├── knowledge_base/                # Base de conhecimento para ingestão
│   │   └── guia_imposto_renda.txt     # Guia completo do IRPF (incluído)
│   └── chroma_db/                     # Banco vetorial persistente
├── docs/
│   └── diagrams/
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) e [Docker Compose](https://docs.docker.com/compose/) instalados
- Pelo menos **8 GB de RAM** (modelo Mistral requer ~4–5 GB)
- Espaço em disco: ~5 GB para modelos e dependências

---

## Execução com Docker (recomendado)

### 1. Clonar o repositório

```bash
git clone https://github.com/JulianaBallin/DeclaraAI.git
cd DeclaraAI
```

### 2. Configurar variáveis de ambiente (opcional)

```bash
cp .env.example .env
# Edite o .env se necessário
```

### 3. Subir os containers

```bash
docker-compose up --build
```

> Na primeira execução, o Docker baixará as imagens e instalará as dependências.
> Pode levar alguns minutos dependendo da conexão.

### 4. Baixar o modelo no Ollama

```bash
# Em outro terminal, após os containers subirem:
docker exec -it declaraai-ollama ollama pull mistral
```

> Aguarde o download completo (~4 GB).

### 5. Acessar a aplicação

| Serviço | URL |
|---|---|
| Interface Streamlit | http://localhost:8501 |
| API FastAPI (Swagger) | http://localhost:8000/docs |
| Ollama | http://localhost:11434 |

---

## Execução Local (sem Docker)

### Pré-requisitos adicionais

- Python 3.11+
- [Ollama](https://ollama.ai) instalado localmente

### Backend

```bash
cd backend

# Criar e ativar ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Linux/Mac
# ou: .venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp ../.env.example ../.env
# Edite: OLLAMA_BASE_URL=http://localhost:11434

# Criar estrutura de dados
mkdir -p ../data/uploads ../data/knowledge_base ../data/chroma_db

# Iniciar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
pip install -r requirements.txt

export API_URL=http://localhost:8000  # Linux/Mac
# ou: set API_URL=http://localhost:8000  # Windows

streamlit run app.py
```

### Ollama

```bash
# Terminal 1: iniciar servidor
ollama serve

# Terminal 2: baixar modelo
ollama pull mistral
```

---

## Endpoints da API

### Chat RAG

| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/chat` | Enviar pergunta ao assistente |
| `POST` | `/ingest` | Re-indexar base de conhecimento |
| `GET` | `/status` | Status e métricas do sistema RAG |

### Documentos

| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/documents/upload` | Upload e processamento de documento |
| `POST` | `/documents/save` | Salvar documento no histórico |
| `GET` | `/documents/categorias` | Listar categorias disponíveis |

### Histórico

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/history` | Listar histórico (filtros: categoria, nome, período) |
| `GET` | `/history/summary` | Resumo anual por categoria |
| `DELETE` | `/history/{id}` | Excluir documento do histórico |

---

## Exemplos de Uso

### Chat via cURL

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "Quais despesas médicas posso deduzir no IR?"}'
```

### Upload de documento

```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "arquivo=@/caminho/para/recibo.pdf"
```

### Re-indexar base de conhecimento

```bash
curl -X POST http://localhost:8000/ingest
```

---

## Configuração

Todas as configurações são feitas via variáveis de ambiente (arquivo `.env`):

| Variável | Padrão | Descrição |
|---|---|---|
| `OLLAMA_MODELO` | `mistral` | Modelo LLM a usar no Ollama |
| `MODELO_EMBEDDINGS` | `paraphrase-multilingual-MiniLM-L12-v2` | Modelo de embeddings |
| `CHUNK_SIZE` | `600` | Tamanho de cada chunk (caracteres) |
| `CHUNK_OVERLAP` | `80` | Sobreposição entre chunks |
| `TOP_K_RESULTADOS` | `5` | Chunks recuperados por consulta |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | URL do servidor Ollama |

---

## Adicionando Conteúdo à Base de Conhecimento

1. Coloque arquivos `.pdf`, `.txt` ou `.html` em `data/knowledge_base/`
2. Chame o endpoint de re-indexação:

```bash
curl -X POST http://localhost:8000/ingest
```

O sistema fragmentará os textos em chunks de 600 caracteres com 80 de overlap,
gerará embeddings e persistirá no ChromaDB automaticamente.

---

## Tecnologias

| Componente | Tecnologia |
|---|---|
| API REST | FastAPI 0.111 |
| Interface Web | Streamlit 1.35 |
| Banco Vetorial | ChromaDB 0.5 |
| Embeddings | sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2) |
| LLM | Ollama (Mistral, Llama3, etc.) |
| Banco Relacional | SQLite + SQLAlchemy 2.0 |
| Extração PDF | pdfplumber |
| Extração HTML | BeautifulSoup4 |
| Containerização | Docker + Docker Compose |

---

## Pipeline RAG — Decisões Técnicas

| Decisão | Justificativa |
|---|---|
| **chunk_size = 600** | Suficiente para capturar contexto fiscal sem diluir relevância |
| **overlap = 80** | Preserva frases cortadas na fronteira de chunks |
| **paraphrase-multilingual-MiniLM-L12-v2** | Suporte a PT-BR, 384 dims, leve e eficiente |
| **cosine similarity** | Mais robusta para textos de comprimentos variados |
| **temperatura = 0.3** | Respostas conservadoras e factuais no domínio fiscal |
| **Singleton embeddings** | Evita múltiplos carregamentos do modelo em memória |
| **SQLite** | Suficiente para protótipo acadêmico, zero configuração |

---

## Limitações

- Não substitui contador ou validação oficial da Receita Federal
- A qualidade das respostas depende do modelo Ollama configurado
- Extração por heurísticas pode falhar em documentos mal formatados
- Base de conhecimento deve ser atualizada manualmente
- Requer conexão à internet apenas para baixar modelos na primeira execução

---

## Avaliação do Sistema

O sistema pode ser avaliado com base em:

- **Precisão da recuperação**: relevância dos chunks retornados
- **Qualidade das respostas**: coerência e fidelidade ao contexto
- **Classificação de documentos**: acurácia da categorização tributária
- **Extração de metadados**: taxa de sucesso na identificação de datas/valores

---

## Equipe

| Nome | Matrícula |
|---|---|
| Juliana Ballin Lima | 2315310011 |
| Fernando Luiz Da Silva Freire | 2315310007 |

---

<h3 align="center">UEA • Projeto de RAG • DeclaraAI</h3>
