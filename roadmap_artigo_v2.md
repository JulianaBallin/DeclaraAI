# Roadmap v2 — DeclaraAI: Artigo Acadêmico

> Atualizado com base em literatura recente (2024–2025) e feedback do professor.
>
> **Legenda:**
> - 🆕 = passo completamente novo, não existia no roadmap original
> - ➕ = passo que existia, mas foi expandido com itens novos
> - ✅ = sem alteração em relação ao original

---

## O que mudou em relação ao roadmap original

### Passos completamente novos (🆕)

| # | Item novo | Por que foi adicionado |
|---|-----------|------------------------|
| 2 | Experimentos de Estratégia de Recuperação | Busca híbrida BM25 + vetorial + reranking — ausente no original |
| 4 | Comparação de Modelos de Embedding | Embedding nunca era comparado — pode impactar mais que o LLM |
| 6 | Avaliação com RAGAS | Padrão da indústria para avaliação RAG — revisores vão exigir |
| 9 | Seção de Privacidade / LGPD | Diferencial do projeto (execução local) não estava sendo aproveitado |

### Passos existentes que foram expandidos (➕)

| # | Item original | O que foi adicionado |
|---|---------------|----------------------|
| 1 | Experimentos de Chunking | +3 famílias de chunking (sentença, semântico, contextual); métricas RAGAS |
| 3 | Experimentos com LLMs | +Vanilla LLM sem RAG como baseline obrigatório (ablation study) |
| 5 | Classificação de documentos | Migração de híbrido → LLM-first; regras viram fallback; dataset anotado; taxa de fallback como métrica |
| 7 | Notebooks | +notebook 01b de estratégias de recuperação |
| 10 | Artigo Overleaf | +subseção ablation study; +subseção busca híbrida; +tabela de referências |

---

## Status geral

| Item | Status |
|------|--------|
| Pipeline RAG funcional | ✅ Concluído |
| Classificação por regras | ✅ Concluído |
| Singleton ServicoRAG + warmup | ✅ Concluído |
| Dataset de avaliação | 🔲 Pendente |
| 🆕 RAGAS instalado e configurado | 🔲 Pendente |
| Experimentos de chunking — expandido | 🔲 Pendente |
| 🆕 Experimentos de estratégia de recuperação | 🔲 Pendente |
| Experimentos com LLMs + ablation study | 🔲 Pendente |
| 🆕 Comparação de embedding models | 🔲 Pendente |
| LLM classificador (migração híbrido → LLM-first) | 🔲 Pendente |
| Notebooks de gráficos | 🔲 Pendente |
| Novo frontend React | 🔲 Pendente |
| 🆕 Seção Privacidade/LGPD redigida | 🔲 Pendente |
| Artigo no Overleaf | 🔲 Pendente |

---

## Lacunas críticas identificadas vs. roadmap original

Estes seis itens estavam ausentes e revisores de artigo vão exigir:

1. **RAGAS ausente** — padrão da indústria para avaliação RAG (Es et al., EACL 2024).
2. **Apenas chunking fixo** — necessário comparar também chunking por sentença, semântico e contextual.
3. **Sem busca híbrida** — BM25 + vetorial + reranking é o estado da arte em documentos técnicos.
4. **Sem ablation study** — sem comparar vanilla LLM vs RAG, o artigo não prova que o pipeline agrega valor.
5. **Privacidade/LGPD não discutida** — diferencial do projeto (execução local) não está aproveitado como contribuição.
6. **Classificação híbrida** — arquitetura atual (regras primárias + LLM fallback) impede comparação experimental limpa; precisa migrar para LLM-first com regras como fallback de segurança.

---

## 1. ➕ Experimentos de Chunking (expandido)

### Por que entra no artigo

O roadmap original testava só variações dentro de uma única família de chunking: mudava o tamanho (200, 400, 600 tokens) e o overlap (0, 40, 80 tokens). Isso não é suficiente para um artigo porque trata o chunking fixo como se fosse a única opção existente.

A literatura de 2025 exige comparação entre **famílias** diferentes de chunking. O paper de referência (Bennani et al., arXiv 2601.14123) conduziu um experimento sistemático comparando método, tamanho, overlap e tamanho de contexto, e mostrou que chunking por sentença supera o fixo em quase todos os cenários. Se você só testar variações de tamanho sem comparar as famílias, um revisor que leu essa literatura vai sinalizar a lacuna.

### O que foi adicionado nesta seção

As três famílias novas abaixo não existiam no roadmap original:

**🆕 Chunking por sentença** — em vez de cortar a cada N tokens independentemente do conteúdo, corta nos pontos finais e vírgulas onde as ideias terminam naturalmente. Preserva frases completas e evita cortar uma ideia no meio. Implementado com NLTK ou spaCy. A literatura mostra que esse método supera o fixo em quase todos os cenários testados.

**🆕 Chunking semântico** — calcula o embedding de cada frase e só corta quando detecta uma mudança significativa de assunto (distância vetorial alta entre frases consecutivas). Mais custoso computacionalmente, mas produz chunks temáticos coerentes. Implementado com o `SemanticChunker` do LangChain.

**🆕 Contextual Retrieval** — antes de indexar cada chunk, envia esse chunk ao LLM com o documento completo e pede que ele gere um resumo de onde aquele trecho está no documento ("este trecho faz parte de uma declaração de IR e descreve despesas médicas dedutíveis"). Esse contexto é adicionado ao início do chunk antes de indexar. A ideia é que o chunk carregue informação suficiente para ser entendido isoladamente, sem depender dos chunks vizinhos. Técnica publicada pela Anthropic em 2024.

**🆕 Late chunking** — ao contrário das outras abordagens, primeiro calcula o embedding do documento inteiro (capturando contexto global), e só depois segmenta. Preserva relações de longo alcance que se perdem quando você chunka antes de embeddar. Referência: arXiv 2504.19754.

### 1.1 Estratégias a testar

| Estratégia | Descrição | Status no projeto | Referência |
|------------|-----------|-------------------|------------|
| Fixo por tokens | Baseline — chunk_size 200/400/600/800, overlap 0/40/80/120 | Já existe | Roadmap original |
| 🆕 Por sentença | Split em limites semânticos naturais (NLTK/spaCy) | A criar | Bennani et al., 2025 |
| 🆕 Semântico | Split por mudança de embedding (SemanticChunker) | A criar | Amiri & Bocklitz, 2025 |
| 🆕 Contextual Retrieval | Adiciona resumo de contexto a cada chunk antes de indexar | A criar | Anthropic, 2024 |
| 🆕 Late chunking | Embed documento inteiro, segmentar depois | A criar | arXiv 2504.19754 |

### 1.2 Métricas de avaliação

As métricas do roadmap original (Precisão@K, MRR, tempo) foram mantidas. As quatro métricas do RAGAS foram adicionadas — ver Seção 6 para explicação detalhada de cada uma.

- **Faithfulness** (RAGAS) — a resposta gerada está apoiada no contexto, ou o modelo inventou algo?
- **Answer Relevancy** (RAGAS) — a resposta endereça a pergunta feita?
- **Context Precision** (RAGAS) — os chunks mais relevantes chegam no topo da lista?
- **Context Recall** (RAGAS) — tudo o que era necessário para responder foi recuperado?
- **Precisão@K** — dos K chunks recuperados, quantos são realmente relevantes?
- **MRR (Mean Reciprocal Rank)** — posição média do primeiro chunk relevante.
- **Tempo de indexação e de busca** — custo computacional por configuração.

### 1.3 Como executar

```bash
pip install ragas rank_bm25 nltk sentence-transformers --break-system-packages
```

Para cada estratégia: limpar ChromaDB, re-indexar com a estratégia em questão, rodar todas as perguntas do dataset de avaliação, calcular as métricas e salvar em CSV.

**Arquivos a criar/editar:**
- [ ] `data/eval/perguntas.json` — 50–80 perguntas IRPF + respostas de referência anotadas manualmente
- [ ] `scripts/avaliar_chunking.py` — itera as 5 estratégias, salva métricas RAGAS + Precisão@K
- [ ] `data/eval/resultados_chunking.csv` — saída dos experimentos
- [ ] `notebooks/01_experimentos_chunking.ipynb` — heatmaps, boxplots, gráficos de barras para o artigo

---

## 2. 🆕 Experimentos de Estratégia de Recuperação

> Esta seção inteira não existia no roadmap original.

### Por que entra no artigo

O projeto usa exclusivamente busca vetorial (ChromaDB com cosine similarity). Isso funciona bem para perguntas abertas e semânticas, mas tem uma fraqueza importante para o domínio fiscal.

Documentos de IRPF têm terminologia exata e muito específica: "NF-e", "NFC-e", "DARF", "holerite", "CNPJ", "CPF", "carnê-leão". Se o usuário digita "NF-e" e o chunk relevante contém "nota fiscal eletrônica", a busca vetorial pode não conectar os dois porque as representações numéricas são diferentes. Uma busca por palavras-chave (BM25) conecta imediatamente porque trabalha com os tokens literais do texto.

A solução do estado da arte é combinar os dois: busca vetorial para semântica + BM25 para termos exatos + um reranker para reordenar os resultados combinados por relevância real. Um paper recente (arXiv 2604.01733) testou exatamente isso em documentos financeiros — que têm o mesmo perfil de terminologia exata que documentos fiscais — e encontrou Recall@5 de 0.816 com a combinação híbrida + reranking, contra 0.587 com busca vetorial pura. Isso é uma diferença de 39% que vale uma subseção inteira no artigo.

**Como funciona o Reciprocal Rank Fusion (RRF):** cada método de busca retorna uma lista rankeada de chunks. O RRF combina essas listas somando pontuações inversas às posições: um chunk na posição 1 de qualquer lista recebe mais pontos que um chunk na posição 10. O resultado é uma lista unificada que aproveita os pontos fortes de cada método.

**Como funciona o reranker:** é um modelo separado (cross-encoder) que recebe a pergunta original + cada chunk individualmente e calcula uma pontuação de relevância real. É mais lento que embedding similarity, mas muito mais preciso porque lê a pergunta e o chunk juntos em vez de comparar vetores isolados.

### 2.1 Configurações a comparar

| Configuração | Implementação | O que muda |
|--------------|---------------|------------|
| Vetorial puro | ChromaDB atual | Baseline — já existe |
| BM25 puro | `rank_bm25` library | Só palavras-chave, sem semântica |
| Híbrido RRF | ChromaDB + BM25 + Reciprocal Rank Fusion | Combina os dois rankings |
| Híbrido + Reranking | Híbrido + cross-encoder ms-marco-MiniLM-L-6-v2 | Reordena por relevância real |

### 2.2 Como executar

```python
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

def reciprocal_rank_fusion(results_list, k=60):
    scores = {}
    for results in results_list:
        for rank, doc_id in enumerate(results):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (rank + k)
    return sorted(scores, key=scores.get, reverse=True)

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
```

**Arquivos a criar:**
- [ ] `backend/app/rag/retrieval/hybrid_retriever.py` — combina ChromaDB + BM25 via RRF
- [ ] `backend/app/rag/retrieval/reranker.py` — cross-encoder sobre os resultados híbridos
- [ ] `scripts/avaliar_retrieval.py` — itera as 4 configurações com as mesmas perguntas
- [ ] `data/eval/resultados_retrieval.csv` — saída
- [ ] `notebooks/01b_retrieval_strategies.ipynb` — gráficos de barras e tabela comparativa

---

## 3. ➕ Experimentos com Diferentes LLMs (com ablation study)

### Por que entra no artigo

Esta seção existia no roadmap original, mas faltava um elemento obrigatório: o **ablation study**.

O problema é o seguinte: se você compara 5 modelos de LLM e todos com RAG ativo, você prova qual modelo é melhor — mas não prova que o RAG em si é necessário. Para isso você precisa comparar um modelo com RAG contra o mesmo modelo sem RAG, respondendo às mesmas perguntas. Isso se chama ablation study e é exigido em praticamente todo paper que propõe um pipeline de recuperação.

Sem essa comparação, um revisor pode argumentar que o LLM simplesmente já sabia as respostas pelo seu treinamento, e o pipeline de recuperação não está contribuindo. O ablation study fecha esse argumento com dados concretos.

### O que foi adicionado nesta seção

A linha "Vanilla LLM (sem RAG)" na tabela de modelos. O script de avaliação precisa ter um modo `no_rag=True` que manda a pergunta diretamente ao modelo sem buscar contexto nenhum. Os resultados dessa condição viram a coluna de baseline na tabela do artigo.

### 3.1 Modelos + baseline obrigatório

| Modelo | Tamanho | Notas |
|--------|---------|-------|
| 🆕 **Vanilla LLM (sem RAG)** | — | **Baseline obrigatório** — ablation study |
| `mistral` | 4.1 GB | Baseline RAG atual do projeto |
| `llama3.2:3b` | 2.0 GB | Benchmark externo: melhor taxa de sucesso em JSON |
| `phi4-mini` | 2.5 GB | Excelente em saída estruturada e classificação |
| `gemma3:4b` | 3.3 GB | Forte em raciocínio |
| `qwen2.5:7b` | 4.7 GB | Melhor suporte multilingual — favorito para português |

### 3.2 Métricas

- Todos os 4 scores RAGAS: faithfulness, answer relevancy, context precision, context recall
- **Taxa de alucinação** — porcentagem de respostas onde Faithfulness < 0.5 (o modelo inventou informação)
- Latência: TTFT (tempo até primeiro token) e tempo total de geração
- Curva de Pareto: tamanho do modelo (GB) vs. score de qualidade

**Arquivos a criar/editar:**
- [ ] `scripts/avaliar_llm.py` — adicionar modo `no_rag=True` para ablation
- [ ] `data/eval/resultados_llm.csv`
- [ ] `notebooks/02_comparacao_llm.ipynb`

---

## 4. 🆕 Comparação de Modelos de Embedding

> Esta seção inteira não existia no roadmap original.

### Por que entra no artigo

O modelo de embedding — o componente que transforma texto em vetores antes de indexar no ChromaDB — nunca é comparado no projeto atual. Ele está fixo em algum modelo padrão e nunca foi questionado.

O problema é que o embedding pode ser o gargalo de qualidade do RAG. Um paper de 2025 (Amiri & Bocklitz, arXiv 2506.17277) testou 48 modelos de embedding em um domínio técnico específico e encontrou variações enormes de desempenho. Para português fiscal especificamente, modelos treinados majoritariamente em inglês (como o `all-MiniLM-L6-v2`) podem ter dificuldade com termos e estruturas da língua portuguesa.

Testar 3 modelos de embedding é um experimento rápido — usa o mesmo dataset de perguntas já criado — e adiciona uma tabela de comparação valiosa ao artigo, especialmente porque a combinação "comparação de embeddings em domínio fiscal em português" ainda não foi publicada.

### 4.1 Modelos a testar

| Modelo | Dimensões | Como usar | Por que testar |
|--------|-----------|-----------|----------------|
| `all-MiniLM-L6-v2` | 384 | sentence-transformers | Baseline provável do projeto atual |
| `nomic-embed-text` | 768 | `ollama pull nomic-embed-text` | Sem custo extra, disponível localmente |
| `multilingual-e5-large` | 1024 | sentence-transformers | Treinado para múltiplos idiomas incluindo português |

**Arquivos a criar:**
- [ ] `scripts/avaliar_embeddings.py` — para cada modelo: re-indexa, roda perguntas, salva RAGAS
- [ ] `data/eval/resultados_embeddings.csv`

---

## 5. ➕ Migração da Classificação: Híbrido → LLM-first

> Ponto levantado pelo professor. A arquitetura atual é híbrida (regras + heurísticas com fallback). A mudança proposta é inverter a lógica: o LLM classifica por padrão, e as regras atuais viram fallback de segurança — acionadas apenas quando o LLM falhar ou retornar JSON inválido.

### Por que migrar (e por que importa para o artigo)

A classificação atual funciona assim: regras e heurísticas tentam identificar o tipo do documento olhando palavras-chave, estrutura e padrões de texto. Quando não consegue, cai num fallback. Esse modelo tem dois problemas concretos.

**Fragilidade das regras:** um documento de saúde que usa "atendimento médico" em vez de "consulta médica" pode não ser capturado pela regra certa. Documentos digitalizados com OCR imperfeito, notas fiscais de layouts variados, holerites de empresas com formatos diferentes — tudo isso quebra regras. Cada exceção exige manutenção manual no código.

**Comparação turva para o artigo:** com o modelo híbrido atual, a comparação experimental ficaria "regras + LLM vs. LLM puro", o que não é uma comparação limpa. Para o artigo o argumento precisa ser direto: sistema baseado em regras (estado anterior) vs. sistema baseado em LLM (contribuição proposta). Isso exige que a arquitetura nova seja LLM-first de verdade, não um híbrido onde as regras ainda têm papel primário.

### Nova arquitetura de classificação

```
Documento → Extração de texto → LLM classificador (primário)
                                        ↓ falha ou JSON inválido
                                 Fallback por regras (segurança)
                                        ↓
                                 Resultado final com flag de origem
```

O resultado final deve registrar se veio do LLM ou do fallback. Isso permite medir a **taxa de fallback acionado** como métrica de robustez do classificador LLM — quanto menor, mais confiável ele é.

### 5.1 O que implementar

- Novo serviço `llm_classification_service.py` que envia o texto extraído ao LLM com prompt estruturado e recebe JSON com os campos abaixo.
- O serviço de regras atual (`classification_service.py`) é mantido intacto, mas rebaixado para fallback.
- Um campo `origem` no resultado (`"llm"` ou `"fallback_regras"`) para rastrear qual caminho foi usado.
- Usar modelo leve para classificação — `phi4-mini` ou `llama3.2:3b`. Classificação é mais simples que geração livre e não precisa do modelo maior.

### 5.2 Formato de saída esperado (JSON estruturado)

```json
{
  "tipo_documento": "NF-e",
  "categoria_irpf": "despesa_saude",
  "dedutivel": true,
  "motivo": "Nota fiscal de consulta médica — dedutível sem limite",
  "confianca": 0.95,
  "origem": "llm"
}
```

### 5.3 Categorias a cobrir

`NF-e`, `NFC-e`, `NFS-e`, `recibo`, `holerite`, `extrato_bancário`, `informe_rendimentos`, `DARF`, `carnê_leão`, `declaração_plano_saúde`, `laudo_médico`, `recibo_escolar`, `comprovante_doação`, `contrato_aluguel`, `desconhecido`

### 5.4 Dataset anotado (obrigatório para o artigo)

Para reportar a comparação com dados concretos, é necessário um dataset anotado manualmente onde cada documento tem a classificação correta definida por humano. O experimento então roda as duas abordagens no mesmo dataset e compara os resultados.

- 50–100 documentos por categoria, cobrindo variações de layout e qualidade de OCR.
- Cada documento anotado com: `tipo_documento` correto, `categoria_irpf` correta, `dedutivel` correto.
- Separar um subconjunto com casos difíceis: documentos ambíguos, OCR ruim, termos não convencionais.

### 5.5 Métricas para o artigo

| Métrica | O que mede |
|---------|-----------|
| Acurácia geral | % de documentos classificados corretamente no tipo |
| F1 por classe | Precisão e recall por categoria (importante: classes desbalanceadas) |
| Matriz de confusão | Onde cada abordagem erra — quais categorias se confundem |
| Taxa de fallback | % de vezes que o LLM falhou e as regras foram acionadas |
| Tempo de classificação | Latência média: regras vs. LLM |

A comparação central do artigo: **regras puras (estado anterior) vs. LLM-first com fallback (proposta)**.

**Arquivos a criar/editar:**
- [ ] `backend/app/services/llm_classification_service.py` — novo serviço LLM-first
- [ ] `backend/app/services/classification_service.py` — refatorar para ser chamado como fallback
- [ ] `backend/app/rag/prompts/classificacao.py` — prompt de classificação com instruções e categorias
- [ ] `data/eval/documentos_anotados.json` — dataset anotado manualmente (50–100 docs)
- [ ] `scripts/avaliar_classificacao.py` — roda regras puras vs. LLM-first no mesmo dataset
- [ ] `notebooks/03_classificacao_documentos.ipynb` — matriz de confusão, F1 por classe, taxa de fallback

---

## 6. 🆕 Avaliação com RAGAS

> Esta seção inteira não existia no roadmap original.

### Por que entra no artigo

O roadmap propunha métricas como Precisão@K e MRR, que medem exclusivamente o retrieval — se os chunks certos foram buscados. Elas não medem se a resposta final gerada pelo LLM é boa, correta ou inventada.

O RAGAS (Retrieval-Augmented Generation Assessment) é o framework de referência da comunidade para avaliar sistemas RAG de ponta a ponta. Foi publicado em 2023 (Es et al.) e apresentado no EACL 2024. Processa mais de 5 milhões de avaliações por mês em produção em empresas como AWS, Microsoft e Databricks. Se você submeter um artigo sobre RAG usando só Precisão@K e MRR sem mencionar RAGAS, o revisor vai perguntar por que você não o usou.

### O que o RAGAS mede (explicado sem jargão)

**Faithfulness** — pergunta: a resposta gerada está apoiada no contexto que foi recuperado, ou o modelo inventou algo que não estava lá? É a métrica de alucinação. Um sistema que gera respostas plausíveis mas não fundamentadas no documento do usuário pode causar dano real em contexto fiscal.

**Answer Relevancy** — pergunta: a resposta realmente responde o que foi perguntado? Uma resposta pode ser factualmente correta e apoiada no contexto, mas não endereçar a pergunta de verdade. Essa métrica captura isso.

**Context Precision** — pergunta: os chunks mais relevantes estão chegando no topo da lista, ou estão sendo enterrados por chunks menos relevantes? Mede a qualidade do ranking, não só se os chunks certos foram recuperados.

**Context Recall** — pergunta: tudo o que era necessário para responder à pergunta foi recuperado? Mede se informação importante ficou para trás na base de dados.

### A vantagem principal para este projeto

O RAGAS pode usar o próprio Ollama local como "LLM juiz" para calcular as métricas. Não é necessário ter uma conta na OpenAI ou pagar por API externa — o modelo local avalia os próprios resultados. Isso mantém o princípio de execução local do projeto intacto.

### 6.1 Configuração

```python
# Usando Ollama local como LLM juiz — sem custo de API
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from langchain_community.llms import Ollama

llm_judge = Ollama(model="mistral")

results = evaluate(
    dataset=eval_dataset,
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    llm=llm_judge,
)
```

**Arquivos a criar:**
- [ ] `scripts/avaliar_ragas.py` — wrapper do RAGAS configurado com Ollama
- [ ] `data/eval/resultados_ragas.csv` — scores RAGAS por experimento
- [ ] `requirements-dev.txt` — adicionar `ragas`, `deepeval`

---

## 7. ➕ Notebooks de Gráficos para o Artigo

### O que foi adicionado

O notebook `01b_retrieval_strategies.ipynb` é novo — não existia no roadmap original. Ele gera os gráficos comparando as 4 estratégias de recuperação (vetorial, BM25, híbrido, híbrido+reranking) adicionadas na Seção 2.

Os outros notebooks estavam no original e foram mantidos com pequenos ajustes para incluir os scores RAGAS nos eixos.

- [ ] `notebooks/01_experimentos_chunking.ipynb` — heatmap estratégia × RAGAS scores, tempo de indexação
- [ ] 🆕 `notebooks/01b_retrieval_strategies.ipynb` — barras comparando vetorial vs BM25 vs Híbrido vs Reranking
- [ ] `notebooks/02_comparacao_llm.ipynb` — Pareto tamanho vs. qualidade, boxplot latência, tabela ablation
- [ ] `notebooks/03_classificacao_documentos.ipynb` — matriz de confusão, F1 por classe
- [ ] `notebooks/04_visao_geral_sistema.ipynb` — diagrama do pipeline, distribuição de chunks

---

## 8. ✅ Novo Frontend (React + Vite + shadcn/ui)

Sem alterações em relação ao roadmap original.

Páginas a implementar: Chat RAG, Upload de documentos, Base de conhecimento, Histórico, Status do sistema.

```bash
npm create vite@latest declaraai-ui -- --template react
cd declaraai-ui && npm install
npx shadcn@latest init
npx shadcn@latest add button card input textarea badge
```

---

## 9. 🆕 Seção de Privacidade / LGPD no Artigo

> Esta seção inteira não existia no roadmap original.

### Por que entra no artigo

O fato de tudo rodar localmente aparecia no projeto como um detalhe técnico (Ollama, ChromaDB), mas nunca foi posicionado como uma contribuição de design deliberada.

A maioria dos sistemas RAG para documentos pessoais e fiscais que existem hoje manda os dados para APIs externas — OpenAI, Anthropic, Google. Para o contexto de declaração de IRPF isso é um problema concreto: os documentos contêm CPF, renda anual, dados bancários, informações de saúde usadas como dedução médica, dados de dependentes. Tudo isso é dado sensível protegido pela LGPD (Lei 13.709/2018, Art. 5º, II).

O DeclaraAI resolve esse problema por arquitetura: Ollama roda o modelo no próprio computador do usuário, o ChromaDB armazena os vetores localmente, nenhum documento e nenhuma pergunta sai da máquina. Isso não é um detalhe — é uma escolha de design que poucos sistemas concorrentes fazem. Posicionar explicitamente como "privacy-by-design" é um diferencial publicável e relevante para o público brasileiro, onde LGPD é uma preocupação crescente.

### 9.1 Conteúdo a redigir no artigo

- Subseção "Considerações de Privacidade e LGPD" dentro da seção de Arquitetura.
- Explicar que dados fiscais são dados sensíveis conforme LGPD Art. 5º, II, e que o tratamento inadequado gera riscos legais e de confiança para o usuário.
- Tabela comparativa formal: Cloud LLM vs. Local LLM nos eixos custo por consulta, latência, privacidade dos dados, dependência de fornecedor externo e funcionamento offline.
- Argumento central: Ollama + ChromaDB local = zero data leaving the machine. O usuário pode usar o sistema sem conexão à internet e sem nenhum dado sendo transmitido a terceiros.
- Posicionamento como contribuição: "privacy-by-design RAG for sensitive fiscal documents in the Brazilian context".

---

## 10. ➕ Artigo no Overleaf

### O que foi adicionado em relação ao original

Duas subseções novas nos Experimentos e Resultados (ablation study e busca híbrida) e a tabela de referências bibliográficas obrigatórias. A estrutura geral foi mantida.

### 10.1 Estrutura sugerida (8–10 páginas, SBC ou IEEE)

- [ ] Resumo / Abstract
- [ ] 1. Introdução — problema do contribuinte leigo, IRPF brasileiro, objetivo
- [ ] 2. Trabalhos Relacionados — RAG, assistentes fiscais, benchmarks de chunking
- [ ] 3. Arquitetura do Sistema — pipeline, componentes, escolha por execução local (LGPD)
- [ ] 4. Metodologia de Avaliação — dataset de perguntas, métricas RAGAS, modelos comparados
- [ ] 5. Experimentos e Resultados
  - 5.1 🆕 Ablation study: RAG vs. Vanilla LLM
  - 5.2 Impacto da estratégia de chunking (5 famílias)
  - 5.3 🆕 Comparação de estratégias de recuperação (busca híbrida + reranking)
  - 5.4 Comparação de LLMs e modelos de embedding
  - 5.5 Classificação de documentos: regras puras vs. LLM-first (migração de arquitetura)
- [ ] 6. Interface e Usabilidade — screenshots do frontend React
- [ ] 7. Conclusão e Trabalhos Futuros
- [ ] Referências

### 10.2 🆕 Referências-chave para citar

Estas referências não estavam no roadmap original. São obrigatórias para apoiar as escolhas metodológicas.

| Referência | Por que citar |
|------------|---------------|
| Lewis et al. (2020) — RAG original | Fundação teórica do paradigma — citar na Introdução |
| Es et al. (2023) — RAGAS, EACL 2024 | Framework de avaliação usado — citar na Metodologia |
| Bennani et al. (2025) — arXiv 2601.14123 | Justifica a comparação sistemática de chunking |
| arXiv 2604.01733 (2025) | Justifica busca híbrida em documentos financeiros/fiscais |
| Amiri & Bocklitz (2025) — arXiv 2506.17277 | Justifica comparação de embedding models |
| Singh et al. (2024) — ChunkRAG arXiv 2410.19572 | LLM-driven chunk filtering — trabalho relacionado |

---

## Ordem de execução sugerida

```
1.  Dataset de avaliação (data/eval/perguntas.json)           ← base de tudo
2.  Instalar RAGAS + configurar com Ollama local              ← 🆕
3.  Ablation study: vanilla LLM vs RAG                        ← 🆕 obrigatório
4.  Experimentos de chunking (5 estratégias) + notebook 01    ← ➕ expandido
5.  Experimentos de retrieval (híbrido) + notebook 01b        ← 🆕
6.  Comparação de LLMs (5 modelos) + notebook 02
7.  Comparação de embedding models                            ← 🆕
8.  LLM classificador + dataset anotado + notebook 03
9.  Notebook 04 (visão geral do sistema)
10. Novo frontend React
11. Redigir artigo no Overleaf com figuras prontas
```
