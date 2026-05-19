# Roadmap — DeclaraAI: Artigo Acadêmico

Checklist de melhorias e experimentos necessários para publicação do artigo.
Cada seção explica **o que fazer**, **por que importa para o artigo** e **como executar**.

---

## 1. Experimentos de Chunking

> **Por que entra no artigo:** Uma das contribuições centrais de sistemas RAG é mostrar que a
> segmentação do texto afeta diretamente a qualidade das respostas. Comparar configurações
> fornece evidência empírica para justificar os parâmetros escolhidos.

### 1.1 Variações a testar

| Parâmetro       | Valores sugeridos                     |
|-----------------|---------------------------------------|
| `chunk_size`    | 200, 400, 600 (atual), 800, 1000      |
| `chunk_overlap` | 0, 40, 80 (atual), 120, 200           |

Testar combinações representativas (não todas): pequeno/sem overlap, médio/médio overlap,
grande/alto overlap, e a configuração atual como baseline.

### 1.2 Métricas de avaliação

- **Precisão\@K** — dos K chunks recuperados, quantos são realmente relevantes para a pergunta.
- **MRR (Mean Reciprocal Rank)** — posição média do primeiro chunk relevante nos resultados.
- **Fidelidade da resposta** — usando um LLM como juiz (ex.: GPT-4 via API ou Ollama) para
  avaliar se a resposta gerada está de acordo com o contexto recuperado.
- **Tempo de indexação e de busca** — custo computacional de cada configuração.

### 1.3 Como executar

- Criar um conjunto de perguntas de avaliação com respostas esperadas (`data/eval/perguntas.json`).
- Para cada combinação de chunk/overlap: limpar ChromaDB, re-indexar, rodar todas as perguntas,
  salvar métricas em CSV.
- O notebook `notebooks/01_experimentos_chunking.ipynb` (a criar — ver seção 5) vai ler
  esses CSVs e gerar os gráficos.

**Arquivos a criar/editar:**
- [ ] `data/eval/perguntas.json` — perguntas + respostas de referência
- [ ] `scripts/avaliar_chunking.py` — script que itera configurações e salva resultados
- [ ] `data/eval/resultados_chunking.csv` — saída dos experimentos

---

## 2. Experimentos com Diferentes LLMs

> **Por que entra no artigo:** Demonstrar que o sistema é independente do modelo e comparar
> custo/qualidade entre opções locais e mais leves é relevante para viabilidade prática.

### 2.1 Modelos a comparar (todos via Ollama, sem custo de API)

| Modelo              | Tamanho  | Perfil                                      |
|---------------------|----------|---------------------------------------------|
| `mistral`           | 4.1 GB   | Baseline atual — bom equilíbrio             |
| `llama3.2:3b`       | 2.0 GB   | Rápido, leve, razoável em português         |
| `phi4-mini`         | 2.5 GB   | Modelo pequeno da Microsoft, surpreendente  |
| `gemma3:4b`         | 3.3 GB   | Google, bom em raciocínio                   |
| `qwen2.5:7b`        | 4.7 GB   | Forte em idiomas não-ingleses               |

Para baixar: `docker exec declaraai-ollama ollama pull <nome-do-modelo>`

### 2.2 Métricas de avaliação

- **Qualidade da resposta** — avaliação humana (1-5) ou LLM-como-juiz nas mesmas perguntas
  da seção 1.
- **Latência** — tempo médio de geração (ms/token ou segundos por resposta).
- **Fidelidade ao contexto** — o modelo inventou informação que não estava no contexto?
- **Tamanho do modelo vs. qualidade** — curva de Pareto para orientar escolha prática.

### 2.3 Como executar

- Usar o mesmo conjunto de perguntas da avaliação de chunking.
- Alterar `OLLAMA_MODELO` no `.env` ou passar por parâmetro no script.
- Medir `time.perf_counter()` antes e depois de cada chamada ao Ollama.
- Salvar em `data/eval/resultados_llm.csv`.

**Arquivos a criar/editar:**
- [ ] `scripts/avaliar_llm.py` — itera modelos, roda perguntas, salva métricas
- [ ] `data/eval/resultados_llm.csv` — saída
- [ ] `.env.example` — documentar a variável `OLLAMA_MODELO`

---

## 3. LLM Dedicada para Classificação de Documentos

> **Por que entra no artigo:** A classificação atual usa regras + heurísticas. Substituir por
> um LLM com prompt estruturado eleva a robustez e é uma contribuição técnica relevante
> (comparar acurácia antes/depois).

### 3.1 O que fazer

Criar um serviço de classificação baseado em LLM que recebe o texto extraído do documento
e retorna JSON estruturado com:

```json
{
  "tipo_documento": "NF-e",
  "categoria_irpf": "despesa_saude",
  "dedutivel": true,
  "motivo": "Nota fiscal de consulta médica — dedutível sem limite",
  "confianca": 0.95
}
```

### 3.2 Abordagem sugerida

- **Prompt zero-shot** com instruções claras e lista de categorias possíveis.
- **Saída estruturada (JSON mode)** — Ollama suporta `format: "json"` na chamada.
- Usar modelo leve como `phi4-mini` ou `llama3.2:3b` (classificação é mais simples
  que geração livre, não precisa do modelo maior).
- Manter o serviço atual como fallback caso o LLM falhe.

### 3.3 Categorias a cobrir

`NF-e`, `NFC-e`, `NFS-e`, `recibo`, `holerite`, `extrato_bancário`, `informe_rendimentos`,
`DARF`, `carnê_leão`, `declaração_plano_saúde`, `laudo_médico`, `recibo_escolar`,
`comprovante_doação`, `contrato_aluguel`, `desconhecido`

### 3.4 Métricas para o artigo

- Acurácia da classificação em dataset anotado manualmente (criar 50-100 exemplos).
- Comparação: regras atuais vs. LLM classificador.
- Tempo de classificação com e sem LLM.

**Arquivos a criar/editar:**
- [ ] `backend/app/services/llm_classification_service.py` — novo serviço
- [ ] `backend/app/rag/prompts/classificacao.py` — prompt de classificação
- [ ] `data/eval/documentos_anotados.json` — dataset de avaliação
- [ ] `scripts/avaliar_classificacao.py` — script de avaliação

---

## 4. Novo Frontend (substituir Streamlit)

> **Por que importa:** Streamlit tem limitações de UX e não é adequado para produto final.
> Para o artigo, um frontend profissional demonstra completude da solução.

### 4.1 Recomendação de tecnologia

**React + Vite + shadcn/ui** é a escolha recomendada:
- React é o mais usado no mercado e com mais tutoriais disponíveis.
- Vite deixa o projeto rápido para configurar.
- shadcn/ui fornece componentes prontos (botões, cards, chat) sem precisar estilizar do zero.
- TypeScript opcional no início — pode começar em JavaScript puro.

**Alternativa mais simples:** Vue.js + Vuetify (curva de aprendizado menor que React,
mas menos material em português e comunidade menor).

### 4.2 Páginas a implementar

- [ ] **Chat RAG** — input de pergunta + histórico de conversa + indicador de fontes usadas
- [ ] **Upload de documentos** — drag-and-drop, barra de progresso, resultado da classificação
- [ ] **Base de conhecimento** — listar/remover arquivos indexados
- [ ] **Histórico** — listar documentos salvos com filtros por categoria
- [ ] **Status do sistema** — modelo carregado, chunks indexados, Ollama disponível

### 4.3 Como começar (passo a passo)

```bash
# Dentro da pasta frontend/
npm create vite@latest declaraai-ui -- --template react
cd declaraai-ui && npm install
npx shadcn@latest init
npx shadcn@latest add button card input textarea badge
```

A API do backend já está pronta em `http://localhost:8000` — o frontend só consome os
endpoints existentes via `fetch` ou `axios`.

**Arquivos a criar:**
- [ ] `frontend-react/` — novo diretório (manter `frontend/` até migração completa)
- [ ] `frontend-react/src/pages/Chat.jsx`
- [ ] `frontend-react/src/pages/Documentos.jsx`
- [ ] `frontend-react/src/services/api.js` — wrapper das chamadas ao backend

---

## 5. Notebook de Gráficos para o Artigo

> Jupyter notebooks que leem os CSVs dos experimentos e geram figuras prontas para
> inserir no LaTeX/Overleaf.

### 5.1 Notebooks a criar

- [ ] `notebooks/01_experimentos_chunking.ipynb`
  - Heatmap chunk_size × overlap vs. precisão\@K
  - Linha: tempo de indexação por configuração
  - Gráfico de barras: MRR por configuração

- [ ] `notebooks/02_comparacao_llm.ipynb`
  - Gráfico de barras agrupadas: qualidade vs. latência por modelo
  - Scatter plot: tamanho do modelo (GB) vs. score de qualidade (curva de Pareto)
  - Boxplot de latência por modelo

- [ ] `notebooks/03_classificacao_documentos.ipynb`
  - Matriz de confusão: regras vs. LLM classificador
  - Gráfico de barras: acurácia por categoria de documento
  - Comparação: tempo de classificação regras vs. LLM

- [ ] `notebooks/04_visao_geral_sistema.ipynb`
  - Diagrama de fluxo do pipeline RAG (matplotlib + patches)
  - Distribuição de chunks por documento da base de conhecimento
  - Gráfico de pizza: categorias de documentos no dataset de avaliação

### 5.2 Dependências

```bash
pip install jupyter matplotlib seaborn pandas scikit-learn plotly
```

Adicionar `requirements-dev.txt` separado para não inflar a imagem Docker do backend.

**Arquivos a criar:**
- [ ] `notebooks/` — criar diretório
- [ ] `requirements-dev.txt` — dependências de análise/visualização

---

## 6. Artigo no Overleaf

> Estrutura sugerida para artigo de 8-10 páginas no formato SBC
> (Sociedade Brasileira de Computação) ou IEEE — confirmar com o professor.

### 6.1 Estrutura do artigo

- [ ] **Resumo / Abstract** — problema, solução, principais resultados
- [ ] **1. Introdução** — contexto do IRPF, problema do usuário leigo, objetivo do trabalho
- [ ] **2. Trabalhos Relacionados** — outros sistemas RAG, assistentes fiscais, benchmarks de
  chunking
- [ ] **3. Arquitetura do Sistema** — diagrama do pipeline, componentes, tecnologias
- [ ] **4. Metodologia de Avaliação** — dataset de perguntas, métricas, modelos comparados
- [ ] **5. Experimentos e Resultados**
  - 5.1 Impacto do chunking
  - 5.2 Comparação de LLMs
  - 5.3 Classificação de documentos
- [ ] **6. Interface e Usabilidade** — screenshots do frontend, fluxo do usuário
- [ ] **7. Conclusão e Trabalhos Futuros**
- [ ] **Referências**

### 6.2 Figuras planejadas para o artigo

| Figura | Origem |
|--------|--------|
| Diagrama da arquitetura RAG | `docs/diagrams/` (já existe) |
| Heatmap chunking | Notebook 01 |
| Comparação de LLMs | Notebook 02 |
| Matriz de confusão classificação | Notebook 03 |
| Screenshots do frontend | Captura de tela após nova UI |

### 6.3 Passos no Overleaf

- [ ] Criar projeto novo com template SBC ou IEEE (buscar "SBC Overleaf template")
- [ ] Importar figuras exportadas dos notebooks como `.pdf` ou `.png` de alta resolução
- [ ] Usar `\input{}` para separar seções em arquivos diferentes (mais fácil de editar)

---

## Ordem de execução sugerida

```
1. Criar dataset de avaliação (data/eval/perguntas.json)  ← base de tudo
2. Script de avaliação de chunking + notebook 01
3. Script de avaliação de LLMs + notebook 02
4. LLM classificador + dataset anotado + notebook 03
5. Notebook 04 (visão geral)
6. Novo frontend React
7. Redigir artigo no Overleaf com figuras prontas
```

---

## Status geral

| Item | Status |
|------|--------|
| Pipeline RAG funcional | ✅ Concluído |
| Classificação por regras | ✅ Concluído |
| Singleton ServicoRAG + warmup | ✅ Concluído |
| Dataset de avaliação | 🔲 Pendente |
| Experimentos de chunking | 🔲 Pendente |
| Experimentos com LLMs | 🔲 Pendente |
| LLM classificador | 🔲 Pendente |
| Notebooks de gráficos | 🔲 Pendente |
| Novo frontend (React) | 🔲 Pendente |
| Artigo no Overleaf | 🔲 Pendente |
