<h1 align="center">🤖 DeclaraAI</h1>

<p align="center">
  <img src="https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExcHRiNnd1OTJ5YXlmMWtsNWJsZGI0ZnA5NmNnMXQzbHJjYWhoamRwaSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/5fpKNaivstvfmpejxd/giphy.gif" width="260">
</p>

<p align="center">
  Assistente inteligente com <strong>RAG</strong> para organização de documentos e apoio à declaração do imposto de renda.<br>
</p>

---

<h2 align="center">📝 Descrição do Projeto</h2>

O **DeclaraAI** é uma aplicação baseada em inteligência artificial que auxilia usuários na organização e compreensão do processo de declaração do imposto de renda.

O sistema permite o envio de documentos (recibos, notas fiscais, informes), realiza a extração e classificação automática das informações e mantém um histórico estruturado ao longo do ano. Utilizando um pipeline **RAG (Retrieval-Augmented Generation)**, também responde dúvidas com base em uma base de conhecimento tributária.

---

<h2 align="center">🎯 Objetivos</h2>

- Auxiliar usuários leigos na compreensão do imposto de renda;
- Organizar documentos ao longo do ano de forma inteligente;
- Automatizar a classificação e extração de informações de comprovantes;
- Utilizar RAG para responder dúvidas com base em conhecimento confiável;
- Gerar resumos estruturados para facilitar o preenchimento da declaração;

---

<h2 align="center">🤖 Tecnologias Utilizadas</h2>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10+-blue?style=for-the-badge&logo=python">
  <img alt="Docker" src="https://img.shields.io/badge/docker-✔-blue?style=for-the-badge&logo=docker">
  <img alt="RAG" src="https://img.shields.io/badge/RAG-✔-purple?style=for-the-badge">
  <img alt="ChromaDB" src="https://img.shields.io/badge/vector_db-ChromaDB-green?style=for-the-badge">
  <img alt="C4 Model" src="https://img.shields.io/badge/C4_Model-✔-purple?style=for-the-badge">
</p>

---

<h2 align="center">🧠 Pipeline RAG</h2>

O sistema implementa um pipeline completo de RAG:

- **Ingestão de documentos:** PDFs, TXT e HTML;
- **Pré-processamento:** limpeza e normalização de texto;
- **Chunking:** estratégia baseada em contexto semântico (400–700 tokens com overlap);
- **Embeddings:** modelos open-source (ex: sentence-transformers);
- **Banco vetorial:** ChromaDB;
- **Recuperação semântica:** busca por similaridade;
- **Geração de resposta:** LLM open-source via Ollama;

---

<h2 align="center">📁 Estrutura do Projeto</h2>

```bash
📦 declara-ai
├── 📄 README.md
├── 📄 docker-compose.yml
├── 📄 Dockerfile
├── 📁 docs/
│   └── 📁 diagrams/           # diagramas C4
├── 📁 backend/
│   ├── 📄 app.py              # API principal
│   ├── 📁 rag/                # pipeline RAG
│   ├── 📁 services/           # lógica de negócio
│   ├── 📁 models/             # modelos de dados
│   └── 📁 storage/            # persistência de documentos
├── 📁 frontend/               # interface (Streamlit ou similar)
└── 📁 data/
    ├── 📁 documents/          # documentos enviados
    └── 📁 vector_db/          # banco vetorial
````

---

<h2 align="center">🧩 Modelagem com C4</h2>

O projeto utiliza o modelo **C4** para representar a arquitetura:

* **C1 – Contexto:** interação entre usuário e sistema;
* **C2 – Contêineres:** frontend, backend, banco vetorial e armazenamento;
* **C3 – Componentes:** pipeline RAG, módulo de documentos, API;

---

<h2 align="center">🚀 Funcionalidades</h2>

| Funcionalidade            | Descrição                                          |
| ------------------------- | -------------------------------------------------- |
| Upload de documentos      | Envio de recibos, notas e comprovantes             |
| Extração automática       | Identificação de dados como valor, data e emitente |
| Classificação inteligente | Sugestão de categoria tributária                   |
| Histórico de documentos   | Armazenamento contínuo ao longo do ano             |
| Chat com RAG              | Respostas baseadas em conhecimento tributário      |
| Checklist automático      | Sugestão de documentos necessários                 |
| Resumo anual              | Organização para apoio à declaração                |

---

<h2 align="center">🐳 Como Executar com Docker</h2>

### 1. Clonar o repositório

```bash
git clone https://github.com/seu-usuario/declara-ai.git](https://github.com/JulianaBallin/DeclaraAI.git
cd declara-ai
```

### 2. Subir os containers

```bash
docker-compose up --build
```

### 3. Acessar a aplicação

```bash
http://localhost:8501
```

---

<h2 align="center">📊 Avaliação da Solução</h2>

O sistema será avaliado com base em:

* Precisão da recuperação semântica;
* Qualidade das respostas geradas;
* Avaliação manual dos resultados;
* Testes com diferentes tipos de documentos;
* Identificação de falhas e limitações;

---

<h2 align="center">⚠️ Limitações</h2>

* Não substitui contador ou validação oficial;
* Depende da qualidade dos documentos enviados;
* Pode exigir revisão humana em casos complexos;
* Base de conhecimento pode necessitar atualização;

---

<h2 align="center">👥 Equipe</h2>

| Nome                          | Matrícula  |
| ----------------------------- | ---------- |
| Juliana Ballin Lima           | 2315310011 |
| Fernando Luiz Da Silva Freire | 2315310007 |

---

<h3 align="center">UEA • Projeto de RAG • DeclaraAI</h3>

---
