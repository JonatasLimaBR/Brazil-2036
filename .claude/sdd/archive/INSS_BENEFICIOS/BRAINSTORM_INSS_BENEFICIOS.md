# BRAINSTORM — INSS_BENEFICIOS

- **Feature:** INSS_BENEFICIOS
- **Status:** ✅ Shipped
- **Fase:** 0 (Brainstorm)
- **Criado:** 2026-09-04
- **Idioma:** PT-BR (alinhado a `docs/discovery/`)
- **Próximo passo:** `/define .claude/sdd/features/BRAINSTORM_INSS_BENEFICIOS.md`

> Nota: assets do plugin SDD ausentes (`kb/_index.yaml`, `BRAINSTORM_TEMPLATE.md` não instalados) —
> documento segue a lista de seções do skill `sdd-brainstorm`, mesmo padrão do
> `BRAINSTORM_MVP_WALKING_SKELETON.md`.

---

## 1. Ideia

**Fatia #2**: levar o padrão de pipeline provado pelo `MVP_WALKING_SKELETON` (dados.gov.br →
GCS RAW imutável → Bronze → Silver → Gold → `metric_provenance` → API → card) para o domínio
**Previdência & INSS (M03)** — o módulo "carro-chefe" do produto (`CONTEXTO.md §1`).

Escopo confirmado com o usuário: **os 3 datasets P0 de INSS já catalogados**
(`docs/sources/SOURCE-INDEX.csv`) — Benefícios Emitidos, Mantidos e Indeferidos — não só
"Emitidos" como o nome informal da fatia sugeria. Isso fecha o lado de **ingestão** do M03
(`PRD-005` escopo V1) numa só fatia, deixando território/demografia/receita-despesa/simulador
para incrementos futuros.

Diferente da fatia #1, aqui o padrão de pipeline **já existe e já foi revisado 2x**
(`/verify-spec` PASS no MVP; `ci-gate` provado ao vivo no `CI_ASSURANCE_GATES`) — o trabalho de
fase 0 não é inventar o esqueleto, é decidir como estender 3 datasets novos, um formato novo
(ZIP), uma dimensão nova (espécie de benefício) e uma granularidade nova (mensal, não anual)
sobre esse esqueleto sem reabrir decisões já fechadas.

---

## 2. Contexto técnico

| Aspecto | Observação |
|---|---|
| Padrão a reaproveitar | `ingestion/src/ingestion/connectors/base.py` (interface de connector), `divida_estados.py` (implementação de referência), `ingestion/contracts/divida_consolidada_estados.yaml` (formato de contrato), `ingestion/tests/integration/test_pipeline_bigquery.py` (gate `integration` do `ci.yml` já cobre qualquer dataset novo sem infraestrutura de CI adicional). |
| **Achado técnico (não assumir reuso grátis)** | `api/src/api/main.py` + `bigquery_repo.py`: o endpoint `/v1/metrics/{metric_id}` já é genérico por `metric_id`, mas `BigQueryRepo.latest_metric` está hardcoded ao grão `(metric_id × state_ibge_code × MAX(reference_year))` — **anual, uma UF por vez** (`default_state_ibge_code = "35"`, não um total nacional). INSS precisa de grão **mensal** e de uma dimensão nova (**espécie do benefício**) que a query atual não tem. Estender o repo/endpoint (ou decidir uma abordagem alternativa) é decisão de `/design`, não trabalho "de graça". |
| Domínios de KB relevantes | `PRD-005` (Previdência & INSS), `SPEC-011` (INSS Digital Twin — "ingest... plus dictionaries when available"), `SPEC-003/004/005/007` (mesmos do MVP), `SPEC-026` (API/OpenAPI), `SPEC-031`/ADR-054 (CI gates — já realizado, só mais um dataset passa pelo `integration`). `ADR-011` (chave territorial IBGE), `ADR-012` (LLM nunca computa métrica oficial), `ADR-028` (observed/estimated/simulated). |
| Matriz de risco | `docs/risks/RISK-CONTROL-TEST-MATRIX.md` — leitura obrigatória no `/define`. Atenção a dado pessoal: os arquivos reais de benefícios do INSS costumam ter campos de idade/sexo do beneficiário — decisão de grão (abaixo) evita tocar nisso. |
| Fonte de dados | `docs/sources/SOURCE-INDEX.csv` linhas 4–6: **Benefícios Emitidos** (ZIP), **Benefícios Mantidos** (CSV, PDA jun/2023–jun/2025), **Benefícios Indeferidos** (CSV, mesma janela) — todos `dados.gov.br`, prioridade P0, módulo INSS. Descoberta do recurso real (schema exato, encoding, arquivos dentro do ZIP) é tarefa 1 do `/design`, igual à fatia #1. |
| Backlog | `EPIC-010 — INSS Twin`: STORY-010.01 (benefícios emitidos), STORY-010.02 (mantidos) — falta uma story de indeferidos no backlog, a acrescentar no `/define`. |

---

## 3. Discovery

| # | Pergunta | Resposta | Impacto no desenho |
|---|---|---|---|
| 1 | Escopo: só "Emitidos" ou os 3 datasets P0 do PRD-005? | **Os 3 juntos** (Emitidos + Mantidos + Indeferidos). | Fatia maior que o nome informal sugeria; fecha o lado de ingestão do M03 inteiro numa fatia, não 3 fatias. 3 conectores/contratos/tabelas Gold, não 1. |
| 2 | O que "pronto" significa? | **As 3 opções**: espinha de dados + card público + insumo pro simulador previdenciário. | Estrutura em PRs de fase (como o MVP fez PR1/PR2), não um PR único gigante. Simulador em si (SIM-004) fica fora — só o *insumo* (schema simulator-ready). |
| 3 | Grão dos dados (UF vs município)? | **UF × espécie × mês** (decisão registrada por Claude, com racional — ver §8). | Reaproveita a chave territorial já provada (ADR-011, mesma tabela `uf_ibge`); volume tratável; município fica para fatia futura. |
| 4 | Amostras disponíveis? | **Nenhuma ainda.** | Descoberta do recurso real (schema, ZIP, encoding) é tarefa 1 do `/design`, igual à fatia #1. |
| 5 | PR3 (insumo simulador) separado ou dobrado em PR1? | **Dobrado em PR1** — decisão de Claude, aceita pelo usuário ("a melhor abordagem para o contexto"). | Sem PR/artefato extra: o Gold do PR1 já é desenhado no grão que o futuro SIM-004 vai consumir. YAGNI — sem simulador real ainda para validar um insumo dedicado. |

---

## 4. Inventário de amostras

| Tipo | Disponível? | Uso previsto |
|---|---|---|
| Arquivos de entrada | Não | Descoberta dos 3 recursos reais (URL, schema, formato ZIP, dicionário de espécies) é a tarefa 1 do `/design` — mesmo padrão da fatia #1. |
| Exemplo de saída esperada | Não | Construir à mão no `/define`/`/design`: 1 linha Gold alvo por dataset (UF × espécie × mês) + objeto de provenance. |
| Ground truth | Não | Um valor conhecido (UF+espécie+mês) de cada um dos 3 datasets serve de âncora de validação, a obter na descoberta do recurso. |
| Dicionário/glossário | Provável — `CONTEXTO.md` linha 178 cita "Glossários dos Arquivos de Benefícios" como recurso identificado no Portal; `SPEC-011` prevê "dictionaries when available". | Tabela de-para espécie de benefício → descrição, análoga à `uf_ibge` existente. Confirmar existência/URL na descoberta. |
| Código relacionado | Sim — o padrão inteiro do MVP_WALKING_SKELETON (connector, contrato, Bronze/Silver/Gold, provenance, API, card). | Template direto para os 3 datasets novos; não greenfield. |

---

## 5. Abordagens exploradas

### Abordagem A — Uma feature, PRs em fases (dados → apresentação) ⭐ Escolhida
- **O quê:** 1 ciclo SDD (`INSS_BENEFICIOS`) com 2 PRs sequenciais, espelhando o padrão PR1/PR2 do MVP:
  - **PR1 — espinha de dados:** 3 conectores (1 ZIP + 2 CSV, todos sobre `connectors/base.py`) + dicionário de espécies → RAW → Bronze → Silver → **3 tabelas Gold separadas** (`gold_inss_beneficios_emitidos/_mantidos/_indeferidos`, grão UF×espécie×mês, já simulator-ready) → provenance → 3 contratos de dados.
  - **PR2 — apresentação:** estende (ou decide não estender) o endpoint genérico `/v1/metrics/{metric_id}` para o grão mensal+espécie; **1 módulo M03 na Landing com os 3 números** (não 3 cards soltos), valor mais recente + provenance, sem série histórica.
- **Prós:** reaproveita 100% do padrão já revisado (connector, contrato, `ci-gate`/`integration` já cobrem qualquer dataset novo sem tocar CI); PRs pequenos e revisáveis (`CLAUDE.md`); 1 DEFINE/DESIGN só, sem ceremônia de 3 ciclos SDD.
- **Contras:** DEFINE maior que o do MVP (3 datasets a especificar); PR2 tem trabalho real de design na API (não é "grátis", achado técnico §2).
- **Confiança:** 0.85 — padrão comprovado 2x, sem precedente ainda para 3 datasets simultâneos nem para o achado do grão mensal/espécie na API.
- **Por que escolhida:** confirmada pelo usuário; é a extensão natural do padrão já validado por dois `/verify-spec` PASS consecutivos.

### Abordagem B — Três features SDD separadas (uma por dataset/preocupação)
- **O quê:** `/define` independente para espinha de dados, outro para o card, outro para o insumo do simulador.
- **Por que não escolhida:** overhead de 3x a cerimônia SDD para um trabalho com dependência linear forte (card e insumo do simulador não têm valor sem a espinha pronta) — "shippar independente" seria teórico, não real.
- **Confiança:** 0.60.

### Abordagem C — Só a espinha de dados agora (nome original da fatia)
- **O quê:** volta ao escopo do nome informal — só PR1, sem card nem consideração de simulador.
- **Por que não escolhida:** contradiz a confirmação explícita do usuário de incluir as 3 frentes; descartada por decisão do usuário, não por avaliação técnica.
- **Confiança:** N/A (rejeitada por decisão de escopo, não por trade-off técnico).

---

## 6. Itens removidos / adiados (YAGNI)

| Item | Por que fora desta fatia | Vai para |
|---|---|---|
| Grão municipal (município × espécie × mês) | ~5.570 chaves territoriais × espécies × meses — 2 ordens de magnitude a mais de volume que UF; o padrão UF já está provado e é o que o SPEC-011 exige como mínimo público ("aggregated/desensitized"). | Fatia futura, sobre o padrão UF já provado 2x. |
| PR3 dedicado a "insumo simulador" | Sem SIM-004 real para validar um artefato dedicado — risco de desenhar às cegas. O Gold do PR1, se bem desenhado, já serve. | Quando o SIM-004 (simulador previdenciário) entrar em backlog próprio. |
| Construção do simulador previdenciário (SIM-004) em si | Item de roadmap totalmente separado (`docs/discovery/07-MVP-BOUNDARIES.md`: "+ 1 simulador previdenciário" é linha própria, distinta de "+ INSS"). | Épico/fatia própria, fora do escopo SDD desta feature. |
| Demografia integrada (cross-ref IBGE para taxas per-capita) | `PRD-005` lista "demografia" no escopo V1 do módulo, mas não é um dos 3 datasets P0 já catalogados nesta fatia; exigiria um 4º dataset (IBGE população) e lógica de join adicional. | Incremento futuro do M03. |
| Receita/despesa do RGPS | Também listado no PRD-005, mas é fonte de dado distinta (Tesouro/SICONFI, não os 3 datasets INSS de benefícios) — não está em `SOURCE-INDEX.csv` associado a esta fatia. | Fatia própria (provavelmente cruza com M02 Fiscal). |
| Projeção RGPS | É a saída do simulador (SIM-004), não um dado a ingerir. | Junto com o simulador. |
| Série histórica no(s) card(s) | Mesma decisão do MVP: walking-skeleton = valor mais recente + provenance, não série. | PRD-005/PRD-001 V1, incremento futuro. |
| Breakdown por idade/sexo do beneficiário | Fora do grão UF×espécie×mês decidido; campo potencialmente PII-adjacente nos arquivos reais — evitar até haver necessidade de produto clara. | Reavaliar se/quando о grão precisar refinar. |
| Autenticação/RBAC nos novos endpoints | Dados públicos agregados, mesma política da fatia #1 (ADR-044, sem auth). | N/A — decisão permanente para portal público. |
| INSS Agent / RAG / Copilot | Sem comportamento de agente nesta fatia — `agent-eval: n/a` no `gates.yaml` já cobre (mesmo padrão do `CI_ASSURANCE_GATES`). `CONTEXTO.md` já lista limites do futuro INSS Agent ("nunca recebe cancel_benefit") — não é trabalho desta fatia. | Fase de agentes, backlog próprio. |
| 3 tabelas Gold fundidas numa só | Emitido ≠ mantido ≠ indeferido semanticamente; fundir cedo arrisca confundir a métrica. Decisão: 3 tabelas Gold separadas. | N/A — decisão permanente, não adiamento. |

---

## 7. Requisitos-rascunho (para o `/define`)

### PR1 — espinha de dados (3 datasets)
- **R1.** Descobrir os 3 recursos reais no dados.gov.br (Emitidos/ZIP, Mantidos/CSV, Indeferidos/CSV) + o glossário/dicionário de espécies, e registrar 3(+1) linhas em `dataset_registry` (`br2036_domain='inss'`, `br2036_module='M03'`).
- **R2.** 3 conectores sobre `connectors/base.py`: um trata o ZIP (extrai + processa arquivo(s) interno(s)), dois tratam CSV direto. RAW imutável, SHA-256, sem reescrita.
- **R3.** Dicionário de espécies de benefício → tabela de-para em `control` (mesmo espírito de `uf_ibge`).
- **R4.** Bronze: 3 tabelas (`inss_beneficios_{emitidos,mantidos,indeferidos}_raw`) + colunas técnicas padrão.
- **R5.** Silver: normaliza UF (reaproveita `uf_ibge`/ADR-011), espécie (via R3), período → `reference_date` mensal.
- **R6.** Gold: 3 tabelas (`gold_inss_beneficios_{emitidos,mantidos,indeferidos}`), grão UF×espécie×mês, schema desenhado para servir de insumo futuro ao SIM-004 (contagem + valor, quando aplicável).
- **R7.** Provenance: 1 linha por linha de métrica em cada Gold (`SPEC-007`).
- **R8.** 3 contratos de dados (schema + `NOT NULL` em chaves + `value >= 0` / `count >= 0`).
- **R9.** Prova de aceite: query mostrando Gold + `metric_provenance` coerentes para os 3 datasets num mês de referência; gate `integration` do `ci.yml` cobre pelo menos 1 dos 3 (fixture); `/verify-spec` PASS por requisito.

### PR2 — apresentação
- **R10.** Decidir e implementar a extensão de grão da API (`metric_id × UF × espécie × mês`) — ver achado técnico §2; ou abordagem alternativa se `/design` encontrar uma mais simples.
- **R11.** 1 módulo M03 na Landing com os 3 números (emitidos/mantidos/indeferidos do mês mais recente), cada um com classe `observed` (ADR-028) e link "fonte". Nenhum número hard-coded (ADR-012).
- **R12.** Testes: contrato de dados (3x), integração via `ci-gate` já existente, e2e leve confirmando os 3 números no módulo.
- **R13.** Ritual de CI todo verde (reaproveita `ci.yml`/`ci-gate` do `CI_ASSURANCE_GATES` — zero infraestrutura de CI nova); `/security-check`; `/verify-spec` PASS.

---

## 8. Decisões autônomas registradas

| Decisão | Motivo |
|---|---|
| Grão **UF × espécie × mês** (não município) | Reaproveita a chave territorial já provada; volume tratável; município fica para fatia futura sobre o padrão já validado 2x. |
| **3 tabelas Gold separadas**, não uma fundida | Emitido/mantido/indeferido são semânticas distintas; fundir cedo confunde a métrica. |
| **PR3 (insumo simulador) dobrado em PR1** | Sem SIM-004 real para validar um artefato dedicado — YAGNI; o Gold bem desenhado já serve quando o simulador existir. |
| Achado técnico da API registrado como requisito (R10), não assumido como reuso grátis | `BigQueryRepo.latest_metric` está hardcoded a `(metric_id × state × ano)`; estender para mês+espécie é trabalho real de `/design`, não just "trocar o metric_id". |

---

## 9. Questões abertas (resolver no `/define` ou `/design`, via ADR/SPEC quando alterarem arquitetura)

1. **Extensão da API/Gold para grão mensal+espécie** — estender `BigQueryRepo`/`main.py` genericamente, ou criar uma rota dedicada a métricas com dimensão extra? Decisão de `/design` (R10).
2. **Total nacional vs por-UF no módulo M03** — hoje `default_state_ibge_code="35"` mostra 1 UF; o módulo INSS precisa de total nacional (soma das UFs) ou também 1 UF-piloto como a fatia #1? Se nacional, como representar (linha agregada no Gold com um código especial, ou `SUM()` na query)?
3. **Formato ZIP do dataset Emitidos** — quantos arquivos dentro, schema de cada um, delimitador, encoding — só resolve na descoberta real (tarefa 1 do `/design`).
4. **Dicionário de espécies** — existe de fato um recurso baixável separado no Portal, ou os códigos de espécie vêm documentados só em texto/PDF? Afeta R3.
5. **Janela temporal dos dados de Mantidos/Indeferidos** — os nomes do dataset sugerem uma janela fixa ("Jun/2023 a Jun/2025"); confirmar se há atualização contínua ou se é um recorte fechado (afeta expectativa de "métrica corrente" vs "métrica histórica fechada").
6. **STORY-010.03 (indeferidos)** — falta no `backlog/BACKLOG-MESTRE.md` (só há 010.01 emitidos, 010.02 mantidos); acrescentar no `/define`.

---

## 10. Domínios de KB para a Fase Define

- **PRDs:** `PRD-005` (Previdência & INSS).
- **SPECs:** `SPEC-003` (Connectors), `SPEC-004` (RAW/Bronze/Silver/Gold), `SPEC-005` (Data Contracts), `SPEC-007` (Provenance), `SPEC-011` (INSS Digital Twin), `SPEC-026` (FastAPI/OpenAPI Client), `SPEC-031` (CI Gates, já realizado — `ADR-054`), `SPEC-033` (referência de padrão, MVP Walking Skeleton).
- **ADRs:** `ADR-011` (chave territorial IBGE), `ADR-012` (LLM nunca computa métrica oficial), `ADR-028` (observed/estimated/simulated), `ADR-054` (`ci-gate` como required check único).
- **Riscos:** `docs/risks/RISK-CONTROL-TEST-MATRIX.md`, `docs/risks/RISK-REGISTER.md` — atenção a risco de dado pessoal-adjacente nos arquivos reais de benefícios.
- **Backlog:** `EPIC-010` (INSS Twin) — STORY-010.01, STORY-010.02 (e 010.03 a criar).
- **Discovery:** `docs/discovery/07-MVP-BOUNDARIES.md` (INSS está no V1; simulador previdenciário é item separado).
- **Precedente direto:** `.claude/sdd/archive/MVP_WALKING_SKELETON/` e `.claude/sdd/archive/CI_ASSURANCE_GATES/` — padrão de pipeline e de CI já provados, a reaproveitar sem reabrir decisão.

---

## 11. Quality gate (Fase 0)

- [x] Mínimo de 3 perguntas de discovery feitas e respondidas (5 feitas)
- [x] Pergunta de amostras feita (inputs, outputs, ground truth, dicionário)
- [x] Pelo menos 2 abordagens exploradas com trade-offs (A, B, C)
- [x] Usuário confirmou explicitamente a abordagem escolhida (A)
- [x] YAGNI aplicado — seção de itens removidos preenchida (10 itens)
- [x] Mínimo de 2 validações incrementais concluídas (checkpoint PR1, checkpoint PR2)
- [x] Domínios de KB identificados para o Define
- [x] Requisitos-rascunho prontos para o `/define` (R1–R13)

---

## 12. Handoff

Pronto para `/define .claude/sdd/features/BRAINSTORM_INSS_BENEFICIOS.md`.
