# DEFINE — INSS_BENEFICIOS

## Metadados

- **Feature:** INSS_BENEFICIOS
- **Status:** ✅ Complete (Designed)
- **Fase:** 1 (Define)
- **Entrada:** `.claude/sdd/features/BRAINSTORM_INSS_BENEFICIOS.md` (Ready for Define)
- **Criado:** 2026-09-04
- **Idioma:** PT-BR
- **Clarity score:** 14/15 (HIGH)
- **Branch:** a criar — `feature/inss-beneficios`
- **Design:** `.claude/sdd/features/DESIGN_INSS_BENEFICIOS.md` (2026-09-04)
- **Próximo passo:** `/build .claude/sdd/features/DESIGN_INSS_BENEFICIOS.md`

> Nota: assets do plugin SDD ausentes (`kb/_index.yaml`, `DEFINE_TEMPLATE.md`, `spec-linter` não
> instalados) — documento segue a lista de seções obrigatórias do skill `sdd-define`, mesmo padrão
> de `DEFINE_MVP_WALKING_SKELETON.md` e `DEFINE_CI_ASSURANCE_GATES.md`.

---

## 1. Problem statement

O módulo M03 (Previdência & INSS) — o domínio "carro-chefe" do produto (`CONTEXTO.md §1`) —
ainda não tem nenhum dado real ingerido: os 3 datasets P0 já catalogados em
`docs/sources/SOURCE-INDEX.csv` (Benefícios Emitidos, Mantidos, Indeferidos) nunca passaram pelo
pipeline RAW→Bronze→Silver→Gold→provenance provado pela fatia #1, e não há card/API para eles.
O padrão de pipeline existe e já foi validado 2x (`MVP_WALKING_SKELETON`, `CI_ASSURANCE_GATES`),
mas nunca foi exercitado contra (a) um formato de origem diferente (ZIP), (b) uma dimensão nova
(espécie de benefício) e (c) uma granularidade diferente (mensal, não anual) — a API atual está
hardcoded a `(metric_id × UF × ano)` e não suporta isso ainda.

---

## 2. Target users

| Persona | Descrição | Pain point |
|---|---|---|
| **Público do portal / cidadão, gestor, pesquisador** (primária) | Consumidor da Landing pública | Hoje não existe nenhum número de INSS no produto, apesar de ser o domínio mais citado no `CONTEXTO.md` como exemplo de pergunta ("impacto do envelhecimento sobre benefícios do INSS..."). |
| **Time de implementação / agentes de código** (secundária) | Quem estende o padrão de pipeline para um domínio novo | Precisa de um requisito claro sobre o que muda (3 datasets, ZIP, grão mensal+espécie) vs. o que reaproveita 100% do padrão já revisado. |
| **Futuro simulador previdenciário (SIM-004)** (secundária, não-humana) | Consumidor de dados, ainda não construído | Precisa que o Gold desta fatia já nasça no grão/schema que ele vai exigir, sem retrabalho — sem existir ainda para validar isso diretamente. |

---

## 3. Goals (MoSCoW)

### MUST
- **G1.** Descobrir os 3 recursos reais no dados.gov.br (Emitidos/ZIP, Mantidos/CSV, Indeferidos/CSV) + o dicionário de espécies de benefício (se existir como recurso baixável — `SPEC-011`: "dictionaries when available") e registrar em `dataset_registry` (`br2036_domain='inss'`, `br2036_module='M03'`).
- **G2.** 3 conectores sobre `connectors/base.py`: 1 trata ZIP (extrai + processa arquivo(s) interno(s)), 2 tratam CSV direto. RAW imutável (GCS, SHA-256 no nome do objeto), sem reescrita de objeto existente.
- **G3.** Bronze→Silver→Gold para os 3 datasets, grão **UF × espécie × mês**, **3 tabelas Gold separadas** (`gold_inss_beneficios_emitidos/_mantidos/_indeferidos` — não fundidas, semânticas distintas).
- **G4.** Provenance (`metric_provenance`, `SPEC-007`): 1 linha por linha de métrica em cada uma das 3 Gold.
- **G5.** 3 contratos de dados (schema + `NOT NULL` em chaves + `value`/`count >= 0`), um YAML por dataset.
- **G6.** Gate `integration` do `ci.yml` (já existente, `CI_ASSURANCE_GATES`) cobre pelo menos 1 dos 3 datasets via fixture determinística — **zero infraestrutura de CI nova**.
- **G7.** API estende o grão para `metric_id × UF × espécie × mês` — via generalização do `BigQueryRepo`/`/v1/metrics/{metric_id}` existente, ou uma rota dedicada, decisão final de `/design` — sem quebrar o contrato atual da fatia #1 (dívida, grão anual×UF).
- **G8.** 1 módulo M03 na Landing pública com os 3 números do mês de referência mais recente, classe `observed` (ADR-028) em cada um, link "fonte" para o `source_url` real de cada dataset, **nenhum valor hard-coded** (ADR-012).
- **G9.** Ritual de CI todo verde reaproveitando `ci-gate` (`SPEC-031`/`ADR-054`); `/verify-spec` PASS por requisito.

### SHOULD
- **G10.** Módulo M03 exibe **total nacional** (soma das UFs) por espécie/mês, não só uma UF-piloto como a fatia #1 (`default_state_ibge_code="35"`) — mais fiel ao domínio "carro-chefe"; degrada para UF-piloto se a agregação nacional exigir redesenho maior de schema que o orçamento da fatia não comporta (decisão de `/design`).
- **G11.** `backlog/BACKLOG-MESTRE.md` ganha `STORY-010.03 — benefícios indeferidos` (falta hoje; só há 010.01 emitidos, 010.02 mantidos).

### COULD
- **G12.** Teste e2e leve confirmando os 3 números renderizados no módulo M03.
- **G13.** Nota/ADR curto formalizando "3 Gold separadas por dataset semanticamente distinto" como padrão reutilizável para o próximo domínio multi-dataset.

---

## 4. Success criteria (mensuráveis)

| # | Critério | Medição |
|---|---|---|
| S1 | Dados reais carregados | Os 3 datasets têm ≥ 1 mês de referência real na Gold; 0 nulos em PK (`state_ibge_code`, `species_code`, `reference_date`); 0 valores negativos. |
| S2 | Cobertura de provenance | 100% das linhas Gold têm linha correspondente em `metric_provenance`, nas 3 tabelas. |
| S3 | Gate de integração real | `integration` do `ci.yml` roda contra pelo menos 1 fixture de um dos 3 datasets, determinístico, **< 5 min**, contra BigQuery real (mesmo padrão do `CI_ASSURANCE_GATES`). |
| S4 | Módulo sem número fixo | Os 3 valores do módulo M03 vêm da API em tempo de request (não hard-coded); os 3 links "fonte" resolvem para o `source_url` real correspondente. |
| S5 | Verificação independente | `/verify-spec` (sessão nova, read-only) = **OVERALL PASS**, todos os não-negociáveis do `CLAUDE.md` OK. |
| S6 | CI bloqueante | `ci-gate` verde em todo PR desta fatia; nenhum gate enfraquecido ou burlado. |
| S7 | Lineage ponta a ponta | Query de linhagem (`registry → RAW → Bronze → Silver → Gold → metric_provenance`) fecha para ≥ 1 combinação UF×espécie×mês em cada um dos 3 datasets. |

---

## 5. Acceptance tests

- **AT1 — descoberta e registro.** *Given* os 3 recursos reais no dados.gov.br, *When* a descoberta roda, *Then* 3(+1) linhas existem em `dataset_registry` com `source_url`/`resource_url`/`license`/`br2036_module='M03'` preenchidos.
- **AT2 — conector ZIP.** *Given* o recurso "Benefícios Emitidos" (ZIP), *When* o conector roda, *Then* o(s) arquivo(s) interno(s) são extraídos e gravados em RAW imutável com SHA-256 do conteúdo.
- **AT3 — conectores CSV.** *Given* os recursos "Mantidos" e "Indeferidos" (CSV), *When* os conectores rodam, *Then* cada um grava em RAW imutável, mesmo padrão de checkpoint/hash do `divida_estados.py`.
- **AT4 — grão correto na Gold.** *Given* um mês de referência com dado real, *When* a Silver/Gold roda para os 3 datasets, *Then* cada linha Gold tem `state_ibge_code`, `species_code`, `reference_date` (mês) e `value`/`count`, em 3 tabelas separadas.
- **AT5 — contrato pega violação.** *Given* um PR que quebra o schema esperado de um dos 3 contratos (ex.: remove `species_code`), *When* o gate `integration`/`contracts` roda, *Then* falha e bloqueia o merge.
- **AT6 — provenance completa.** *Given* as 3 Gold carregadas, *When* consulto `metric_provenance`, *Then* toda linha Gold tem provenance correspondente (S2).
- **AT7 — API no grão novo.** *Given* a extensão do endpoint (G7), *When* chamo `/v1/metrics/{metric_id}` com um `metric_id` de INSS, *Then* recebo `value`/`count` no mês+espécie corretos + objeto `provenance` completo (mesmo contrato de resposta da fatia #1, campos extras se necessário).
- **AT8 — módulo M03 sem hardcode.** *Given* a Landing pública, *When* o módulo M03 renderiza, *Then* os 3 números vêm de 3 chamadas de API (ou 1 chamada composta), cada um com classe `observed` e link "fonte" funcional.
- **AT9 — CI ritual completo.** *Given* qualquer PR desta fatia, *When* o CI roda, *Then* `ci-gate` resolve (verde ou vermelho, nunca pendente) e bloqueia merge se qualquer gate falhar.
- **AT10 — lineage fecha.** *Given* uma combinação UF×espécie×mês real, *When* executo a query de linhagem, *Then* ela resolve `registry → GCS RAW (uri) → Bronze (_row_hash) → Silver → Gold → metric_provenance` sem quebra, para os 3 datasets (S7).

---

## 6. Out of scope

| Item | Motivo | Destino |
|---|---|---|
| Grão municipal (município × espécie × mês) | ~5.570 chaves territoriais × espécies × meses — 2 ordens de magnitude a mais de volume; UF já satisfaz o mínimo público de `SPEC-011` ("aggregated/desensitized"). | Fatia futura, sobre o padrão UF já provado 2x. |
| Construção do simulador previdenciário (SIM-004) | Item de roadmap separado (`docs/discovery/07-MVP-BOUNDARIES.md`: "+ 1 simulador previdenciário" é linha própria). | Épico/fatia própria. |
| PR/artefato dedicado a "insumo simulador" | Sem SIM-004 real para validar; o Gold desta fatia (G3) já nasce no grão que o simulador vai precisar. | Quando o SIM-004 entrar em backlog. |
| Demografia integrada (cross-ref IBGE, taxas per-capita) | `PRD-005` lista no V1 do módulo, mas não é um dos 3 datasets P0 desta fatia; exigiria dataset IBGE + join adicional. | Incremento futuro do M03. |
| Receita/despesa do RGPS | Fonte de dado distinta (Tesouro/SICONFI), não catalogada em `SOURCE-INDEX.csv` para esta fatia. | Fatia própria, provável interseção com M02. |
| Projeção RGPS | Saída do simulador (SIM-004), não dado a ingerir. | Junto com o simulador. |
| Série histórica no módulo M03 | Mesma decisão da fatia #1: valor mais recente + provenance, não série. | `PRD-001`/`PRD-005` V1, incremento futuro. |
| Breakdown por idade/sexo do beneficiário | Fora do grão UF×espécie×mês; campo potencialmente PII-adjacente nos arquivos reais. | Reavaliar se necessidade de produto justificar. |
| Autenticação/RBAC nos novos endpoints | Dados públicos agregados, mesma política da fatia #1 (`ADR-044`). | N/A — decisão permanente do portal público. |
| INSS Agent / RAG / Copilot | Sem comportamento de agente nesta fatia; `agent-eval: n/a` no `gates.yaml` já cobre. | Fase de agentes, backlog próprio. |
| Tabela Gold única fundindo os 3 datasets | Emitido/mantido/indeferido são semânticas distintas; fundir cedo confunde a métrica. | N/A — decisão permanente. |

---

## 7. Constraints

- **C1.** WIF only, sem chave estática (`ADR-040`).
- **C2.** Não enfraquecer gates existentes (`SPEC-031`: "warning-only replacements are not acceptable for critical gates").
- **C3.** Saída pública sempre agregada/desensibilizada (`SPEC-011`) — nunca granularidade individual do beneficiário.
- **C4.** Reusa `ci-gate`/`integration` já existentes — **zero infraestrutura de CI nova** (`CI_ASSURANCE_GATES` já entregou o mecanismo).
- **C5.** 3 tabelas Gold separadas, não fundidas (decisão do Brainstorm, `BRAINSTORM_INSS_BENEFICIOS.md §6`).
- **C6.** Grão fixo **UF × espécie × mês** nesta fatia — não município (mesma decisão do Brainstorm).
- **C7.** Sem PR/artefato dedicado a "insumo simulador" — dobrado no schema do Gold (G3/G7).
- **C8.** Todo merge em `main` é via PR (branch protection ativa desde 2026-09-04, `CLAUDE.md`).
- **C9.** O contrato de resposta da fatia #1 (`/v1/metrics/{metric_id}` grão anual×UF, dívida) **não pode quebrar** — a extensão da API (G7) é aditiva.

---

## 8. Assumptions / risk register

| ID | Afirmação | Impacto se falsa | Validada |
|---|---|---|---|
| A1 | O recurso "Benefícios Emitidos" vem de fato como ZIP com estrutura previsível (1 ou poucos arquivos internos, schema tabular) | Conector precisa lidar com estrutura inesperada (múltiplos arquivos, formatos mistos); mais tempo de descoberta no `/design` | ☐ |
| A2 | Existe um dicionário/glossário de espécies de benefício baixável separadamente | Mapeamento espécie→descrição precisa vir hardcoded a partir de documentação textual/PDF, não de um recurso estruturado | ☐ |
| A3 | A extensão do endpoint para grão mensal+espécie (G7) é viável generalizando o `BigQueryRepo` existente, sem quebrar o contrato da fatia #1 | Precisa de rota dedicada nova em vez de generalização — mais superfície de API | ☐ |
| A4 | O total nacional (G10, SHOULD) pode ser calculado via `SUM()` na query em tempo de request, sem linha agregada pré-computada na Gold | Gold precisa de uma linha "BR" agregada por espécie/mês — schema adicional | ☐ |
| A5 | O volume mensal × UF × espécie cabe nos padrões de custo BigQuery já aceitos pelo projeto | Revisita o achado residual #3 do `CI_ASSURANCE_GATES` (cap de bytes por query, R-012), agora com urgência maior | ☐ |
| A6 | Os dados de Mantidos/Indeferidos (janela do Plano de Dados Abertos jun/2023–jun/2025) são um recorte fechado, não atualizado continuamente | Pipeline precisa de lógica de refresh incremental em vez de carga única — mais escopo | ☐ |

---

## 9. Technical context

| Aspecto | Definição |
|---|---|
| **Onde vive** | `ingestion/src/ingestion/connectors/` (+3 conectores), `ingestion/contracts/` (+3 YAML), `ingestion/sql/` ou equivalente (Silver/Gold das 3 tabelas), `api/src/api/` (extensão do repo/endpoint ou rota nova), `web/` (módulo M03), `ingestion/tests/integration/` (+fixture de ao menos 1 dataset). |
| **Impacto IaC** | Mínimo — reaproveita datasets BQ (`bronze`/`silver`/`gold`) e buckets já existentes; nenhum recurso GCP novo esperado (a confirmar no `/design`). |
| **Domínios de KB** | `PRD-005` (Previdência & INSS), `SPEC-003` (Connectors), `SPEC-004` (RAW/Bronze/Silver/Gold), `SPEC-005` (Data Contracts), `SPEC-007` (Provenance), `SPEC-011` (INSS Digital Twin), `SPEC-026` (API/OpenAPI), `SPEC-031`/`ADR-054` (CI Gates — já realizado); `ADR-011` (chave territorial IBGE), `ADR-012` (LLM nunca computa métrica oficial), `ADR-028` (observed/estimated/simulated); `RISK-CONTROL-TEST-MATRIX` (atenção a risco de dado pessoal-adjacente); `docs/discovery/07-MVP-BOUNDARIES.md`; `backlog/BACKLOG-MESTRE.md` `EPIC-010`. |

---

## 10. Data contract (aplicável — 3 datasets de origem)

### Source inventory
- **Benefícios Emitidos** — `dados.gov.br`, ZIP, INSS, P0. Schema/encoding/arquivos internos: **a descobrir** (tarefa 1 do `/design`, mesmo padrão da fatia #1).
- **Benefícios Mantidos** — `dados.gov.br`, CSV, "Plano de Dados Abertos Jun/2023 a Jun/2025", INSS, P0. Schema: a descobrir.
- **Benefícios Indeferidos** — `dados.gov.br`, CSV, mesma janela PDA, INSS, P0. Schema: a descobrir.
- **Dicionário de espécies** (se existir) — a confirmar (A2).

### Volumes
- Desconhecido até a descoberta real (A1/A2). Estimativa de ordem de grandeza: agregados nacionais mensais por espécie e UF — plausivelmente milhares a dezenas de milhares de linhas por dataset após agregação em UF×espécie×mês (não milhões, já que não é microdado individual).

### Freshness SLA
- Mantidos/Indeferidos: janela fechada do PDA (A6) — SLA N/A se recorte único; se houver atualização, a definir no `/design`.
- Emitidos: a confirmar cadência de publicação na descoberta.

### Schema contract
- Um contrato YAML por dataset (G5): schema esperado (colunas de origem → `state_ibge_code`, `species_code`, `reference_date`, `value`/`count`), `NOT NULL` em chaves, `value`/`count >= 0`. Segue o formato de `ingestion/contracts/divida_consolidada_estados.yaml`.

### Completeness metrics
- Para cada dataset: todas as UF presentes em `uf_ibge` para o `MAX(reference_date)`; zero nulo em PK; cobertura de provenance 100% (S2).

### Lineage requirements
- A cadeia `dataset_registry → GCS RAW (uri) → Bronze (_row_hash) → Silver → Gold → metric_provenance` deve fechar para ≥ 1 combinação UF×espécie×mês em cada um dos 3 datasets (AT10/S7).

---

## 11. Clarity score breakdown

| Elemento | Nota | Máx | Observação |
|---|---|---|---|
| Problem | 3 | 3 | Lacuna concreta e específica: M03 sem dado real; API hardcoded ao grão anual×UF, incompatível com mensal+espécie. |
| Users | 2 | 3 | Público do portal + time de implementação + "consumidor futuro" (simulador) — o terceiro é não-humano/hipotético, reduz 1 ponto. |
| Goals | 3 | 3 | 9 MUST, 2 SHOULD, 2 COULD; todos mensuráveis e rastreáveis ao Brainstorm. |
| Success | 3 | 3 | S1–S7 com números/thresholds (< 5 min, 100% provenance, 0 nulos, ≥ 1 combinação). |
| Scope | 3 | 3 | Out-of-scope extenso e explícito (10 itens, cada um com destino declarado). |
| **Total** | **14** | **15** | **HIGH — prosseguir para `/design`.** |

---

## 12. Open questions

| ID | Questão | Resolver em |
|---|---|---|
| OQ1 | Extensão do endpoint (G7/A3): generalizar `BigQueryRepo`/`main.py`, ou rota dedicada `/v1/metrics/inss/{...}`? | `/design` |
| OQ2 | Total nacional (G10/A4): `SUM()` em tempo de request, ou linha "BR" agregada pré-computada na Gold? | `/design` |
| OQ3 | Estrutura real do ZIP de Emitidos (quantos arquivos, schema, delimitador, encoding) — A1. | `/design`, tarefa 1 (descoberta do recurso) |
| OQ4 | Dicionário de espécies: existe como recurso baixável, ou só documentado em texto/PDF — A2. | `/design`, tarefa 1 |
| OQ5 | Janela temporal de Mantidos/Indeferidos: recorte fechado ou atualização contínua — A6. | `/design`, tarefa 1 |
| OQ6 | Cap de bytes por query no gate `integration` (achado residual do `CI_ASSURANCE_GATES`, agora com 3 datasets a mais) — revisitar? | `/design`, nota de risco |

---

## 13. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-04 | 1.0 | Criação a partir de `BRAINSTORM_INSS_BENEFICIOS.md`. Clarity 14/15. Status → Ready for Design. | /define (Claude Sonnet 5) |
| 2026-09-04 | 1.1 | Fase 2 concluída. Descoberta real revogou parcialmente R3 (dicionário de espécies — não existe, dado já se autodescreve); D1–D8 no DESIGN. Status → ✅ Complete (Designed). | /design (Claude Sonnet 5) |
