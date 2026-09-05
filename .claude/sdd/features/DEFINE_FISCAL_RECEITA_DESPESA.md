# DEFINE — FISCAL_RECEITA_DESPESA

## Metadados

- **Feature:** FISCAL_RECEITA_DESPESA
- **Status:** ✅ Complete (Built)
- **Fase:** 1 (Define)
- **Entrada:** `.claude/sdd/features/BRAINSTORM_FISCAL_RECEITA_DESPESA.md` (Ready for Define)
- **Criado:** 2026-09-05
- **Idioma:** PT-BR
- **Clarity score:** 14/15 (HIGH)
- **Branch:** a criar — `feature/fiscal-receita-despesa`
- **Próximo passo:** `/design .claude/sdd/features/DEFINE_FISCAL_RECEITA_DESPESA.md`

> Nota: assets do plugin SDD ausentes (`kb/_index.yaml`, `DEFINE_TEMPLATE.md`, `spec-linter` não
> instalados) — documento segue a lista de seções obrigatórias do skill `sdd-define`, mesmo padrão
> de `DEFINE_MVP_WALKING_SKELETON.md` e `DEFINE_INSS_BENEFICIOS.md`.

---

## 1. Problem statement

O módulo M02 (Fiscal & DebtLab) ainda não tem receita nem despesa ingeridas: `EPIC-009` lista
`STORY-009.01` (receita), `STORY-009.02` (despesa) e `STORY-009.03` (primário) como stories em
aberto, e `docs/sources/SOURCE-INDEX.csv` só cataloga as organizações (Tesouro Nacional, SICONFI)
sem um recurso específico de receita/despesa identificado. O padrão de pipeline
(RAW→Bronze→Silver→Gold→provenance→API→Landing) já foi provado 2x
(`MVP_WALKING_SKELETON` com a dívida, `INSS_BENEFICIOS` com 3 datasets de formatos/grão novos),
mas nunca foi exercitado (a) com uma fonte cuja organização ainda não tem recurso catalogado,
nem (b) compondo 2 métricas relacionadas em uma 3ª métrica derivada (resultado primário) sem
ingestão adicional.

---

## 2. Target users

| Persona | Descrição | Pain point |
|---|---|---|
| **Público do portal / cidadão, gestor, pesquisador** (primária) | Consumidor da Landing pública | Hoje o módulo M02 (Fiscal) não existe — só a dívida (M01) e o INSS (M03) têm números reais, apesar de `PRD-004` listar receita/despesa/primário como parte central do painel fiscal. |
| **Time de implementação / agentes de código** (secundária) | Quem estende o padrão de pipeline para uma 3ª fonte | Precisa de um requisito claro sobre o que reaproveita 100% do mecanismo já provado (connector, contrato, `pipeline_incremental`/`backfill`, `/national` endpoint genérico) vs. o que exige descoberta e decisão novas (fonte real, resultado primário). |
| **Futuro simulador DebtLab (`STORY-009.06`)** (secundária, não-humana) | Consumidor de dados, ainda não construído | Precisa que o Gold desta fatia já nasça num grão que o simulador vai poder consumir, sem retrabalho — sem existir ainda para validar isso diretamente. |

---

## 3. Goals (MoSCoW)

### MUST
- **G1.** Descobrir o(s) recurso(s) real(is) de receita e despesa (Tesouro Transparente RREO/RGF, ou SICONFI — decisão de `/design`, tarefa 1) e registrar em `dataset_registry` (`br2036_domain='fiscal'`, `br2036_module='M02'`).
- **G2.** 1-2 conectores sobre `connectors/base.py` (número exato depende de a fonte publicar receita e despesa juntas ou separadas — `OQ2`). RAW imutável, SHA-256 no nome do objeto, sem reescrita de objeto existente.
- **G3.** Bronze→Silver→Gold para os 2 datasets, grão **total agregado por período** (não por categoria/função/órgão), **2 tabelas Gold separadas** (`gold_fiscal_receita`/`gold_fiscal_despesa` — não fundidas, semânticas opostas: uma soma, outra subtrai do resultado).
- **G4.** Provenance (`metric_provenance`, `SPEC-007`): 1 linha por linha de métrica em cada uma das 2 Gold.
- **G5.** 2 contratos de dados (schema + `NOT NULL` em chaves + `value >= 0`), um YAML por dataset.
- **G6.** Gate `integration` do `ci.yml` (já existente) cobre pelo menos 1 dos 2 datasets via fixture determinística — **zero infraestrutura de CI nova**.
- **G7.** `Config.metric_tables` ganha `fiscal_receita`/`fiscal_despesa` apontando para as 2 tabelas Gold novas, reaproveitando o endpoint `GET /v1/metrics/{metric_id}/national` já genérico — sem mudar `main.py`/`bigquery_repo.py`, a confirmar no `/design` (achado técnico do Brainstorm §2).
- **G8.** 1 módulo M02 na Landing pública com receita e despesa do período de referência mais recente, classe `observed` (ADR-028) em cada um, link "fonte" para o `source_url` real, **nenhum valor hard-coded** (ADR-012).
- **G9.** Ritual de CI todo verde reaproveitando `ci-gate` (`SPEC-031`/`ADR-054`); `/verify-spec` PASS por requisito.

### SHOULD
- **G10.** Resultado primário (`STORY-009.03` = receita − despesa) exibido no módulo M02 como uma 3ª visão — condicionado a receita e despesa terem o mesmo grão de período real (`A1`); se não bater, degrada para mostrar só os 2 valores base, sem o derivado.

### COULD
- **G11.** Teste e2e leve confirmando os números novos (receita, despesa, e primário se aplicável) renderizados no módulo M02, mesmo padrão do teste do módulo M03.
- **G12.** Nota curta (revision history desta feature, ou ADR se a decisão for arquitetural o bastante) registrando se o reuso do endpoint `/national` para uma 3ª/4ª métrica se confirmou "grátis" como o achado técnico do Brainstorm previu, ou exigiu ajuste.

---

## 4. Success criteria (mensuráveis)

| # | Critério | Medição |
|---|---|---|
| S1 | Dados reais carregados | Os 2 datasets (receita, despesa) têm ≥ 1 período de referência real na Gold; 0 nulos em PK; 0 valores negativos. |
| S2 | Cobertura de provenance | 100% das linhas Gold têm linha correspondente em `metric_provenance`, nas 2 tabelas. |
| S3 | Gate de integração real | `integration` do `ci.yml` roda contra pelo menos 1 fixture de um dos 2 datasets, determinístico, **< 5 min**, contra BigQuery real. |
| S4 | Módulo sem número fixo | Os valores do módulo M02 vêm da API em tempo de request (não hard-coded); os links "fonte" resolvem para o `source_url` real. |
| S5 | Verificação independente | `/verify-spec` (sessão nova, read-only) = **OVERALL PASS**, todos os não-negociáveis do `CLAUDE.md` OK. |
| S6 | CI bloqueante | `ci-gate` verde em todo PR desta fatia; nenhum gate enfraquecido ou burlado. |
| S7 | Lineage ponta a ponta | Query de linhagem (`registry → RAW → Bronze → Silver → Gold → metric_provenance`) fecha para ≥ 1 período real em cada um dos 2 datasets. |

---

## 5. Acceptance tests

- **AT1 — descoberta e registro.** *Given* o(s) recurso(s) real(is) de receita/despesa, *When* a descoberta roda, *Then* 2(+) linhas existem em `dataset_registry` com `source_url`/`license`/`br2036_module='M02'` preenchidos.
- **AT2 — conector(es) real(is).** *Given* o(s) recurso(s) descoberto(s), *When* o(s) conector(es) roda(m), *Then* cada um grava em RAW imutável, mesmo padrão de checkpoint/hash das 2 fatias anteriores.
- **AT3 — grão correto na Gold.** *Given* um período de referência com dado real, *When* a Silver/Gold roda para os 2 datasets, *Then* cada linha Gold tem `reference_date` e `value`, em 2 tabelas separadas.
- **AT4 — contrato pega violação.** *Given* um PR que quebra o schema esperado de um dos 2 contratos, *When* o gate `integration`/contratos roda, *Then* falha e bloqueia o merge.
- **AT5 — provenance completa.** *Given* as 2 Gold carregadas, *When* consulto `metric_provenance`, *Then* toda linha Gold tem provenance correspondente (S2).
- **AT6 — API sem mudança de código.** *Given* `Config.metric_tables` estendido (G7), *When* chamo `GET /v1/metrics/fiscal_receita/national` e `GET /v1/metrics/fiscal_despesa/national`, *Then* recebo `value`+`provenance` corretos sem que `main.py`/`bigquery_repo.py` tenham mudado além do necessário para o teste do achado técnico (confirma ou refuta a suposição `A2`).
- **AT7 — módulo M02 sem hardcode.** *Given* a Landing pública, *When* o módulo M02 renderiza, *Then* os valores vêm de chamadas de API, cada um com classe `observed` e link "fonte" funcional.
- **AT8 — resultado primário degrada com segurança.** *Given* receita e despesa no mesmo grão de período (ou não), *When* o módulo M02 tenta calcular o primário, *Then* mostra o valor derivado se os grãos baterem, ou omite/degrada com segurança se não baterem (G10, sem crash).
- **AT9 — CI ritual completo.** *Given* qualquer PR desta fatia, *When* o CI roda, *Then* `ci-gate` resolve (verde ou vermelho, nunca pendente) e bloqueia merge se qualquer gate falhar.
- **AT10 — lineage fecha.** *Given* um período real, *When* executo a query de linhagem, *Then* ela resolve `registry → GCS RAW → Bronze → Silver → Gold → metric_provenance` sem quebra, para os 2 datasets (S7).
- **AT11 — não regride as fatias anteriores.** *Given* as rotas de dívida (`/v1/metrics/divida_consolidada`) e INSS (`/v1/metrics/{inss_id}/national`), *When* esta fatia é mergeada, *Then* ambas continuam respondendo exatamente como antes (mesmo padrão de `test_debt_route_unaffected_by_national_route`).

---

## 6. Out of scope

| Item | Motivo | Destino |
|---|---|---|
| Juros (`STORY-009.04`) | Fonte de dado provavelmente distinta (Selic/BCB), não catalogada junto de receita/despesa em `SOURCE-INDEX.csv`. | Fatia própria, sobre o padrão agora provado 3x. |
| Debt simulator (`STORY-009.06`) / stress test (`STORY-009.07`) | Dependem de um simulador ainda não construído; um "insumo dedicado" seria desenhado às cegas sem ele. | Épico/fatia própria, quando o simulador DebtLab entrar em backlog. |
| PR/artefato dedicado a "insumo simulador" | Mesma razão do INSS: sem simulador real para validar. | Quando `STORY-009.06` entrar em backlog. |
| Quebra por categoria (receita tributária/contribuições; despesa por função/órgão) | Explode o schema sem necessidade comprovada de produto; total agregado já prova a cadeia. | Incremento futuro, se o produto pedir. |
| Quebra territorial (UF/município) | Só decidível após a descoberta real da fonte (`OQ1`); se a fonte for nacional (União), nem se aplica. | Fatia futura, se a fonte permitir e o produto pedir. |
| Série histórica no módulo M02 | Mesma decisão das 2 fatias anteriores: valor mais recente + provenance, não série. | `PRD-004` V1, incremento futuro. |
| Autenticação/RBAC nos novos endpoints | Dados públicos agregados, mesma política das 2 fatias anteriores (`ADR-044`). | N/A — decisão permanente do portal público. |
| Agente/RAG/Copilot fiscal | Sem comportamento de agente nesta fatia; `agent-eval: n/a` no `gates.yaml` já cobre. | Fase de agentes, backlog próprio. |
| Tabela Gold única fundindo receita e despesa | Semânticas opostas (soma vs. subtrai do resultado); fundir cedo confunde a métrica. | N/A — decisão permanente. |

---

## 7. Constraints

- **C1.** WIF only, sem chave estática (`ADR-040`).
- **C2.** Não enfraquecer gates existentes (`SPEC-031`).
- **C3.** Saída pública sempre agregada/desensibilizada — nunca granularidade individual.
- **C4.** Reusa `ci-gate`/`integration` já existentes — **zero infraestrutura de CI nova**.
- **C5.** 2 tabelas Gold separadas, não fundidas (decisão do Brainstorm, `BRAINSTORM_FISCAL_RECEITA_DESPESA.md §5/§6`).
- **C6.** Grão fixo **total agregado por período** nesta fatia — não categoria/função/órgão (mesma decisão do Brainstorm).
- **C7.** Sem PR/artefato dedicado a "insumo simulador".
- **C8.** Todo merge em `main` é via PR (branch protection ativa desde 2026-09-04, `CLAUDE.md`).
- **C9.** Os contratos de resposta das 2 fatias anteriores (dívida: `/v1/metrics/{metric_id}` grão anual×UF; INSS: `/v1/metrics/{metric_id}/national`) **não podem quebrar** — a extensão desta fatia é aditiva (`Config.metric_tables` + novas entradas).

---

## 8. Assumptions / risk register

| ID | Afirmação | Impacto se falsa | Validada |
|---|---|---|---|
| A1 | A fonte real publica receita e despesa no mesmo grão de período (comparáveis, para o resultado primário) | `G10`/`STORY-009.03` cai; módulo M02 mostra só os 2 valores base, sem o derivado | ☐ |
| A2 | O endpoint `GET /v1/metrics/{metric_id}/national` + `Config.metric_tables` já genéricos (achado técnico do Brainstorm) funcionam sem mudança de código para receita/despesa | Precisa de ajuste em `bigquery_repo.py`/`main.py` — mais escopo de API do que o previsto | ☐ |
| A3 | A fonte real não tem instabilidade de schema tão severa quanto o Emitidos do INSS (4+ mudanças em <3 anos) | Histórico completo fica limitado a 1 período real, mesmo padrão de fechamento de escopo já aceito no INSS | ☐ |
| A4 | O volume (agregado nacional/mensal) cabe nos padrões de custo BigQuery já aceitos pelo projeto | Revisita o achado residual do `CI_ASSURANCE_GATES` (cap de bytes por query, `R-012`) | ☐ |
| A5 | Receita e despesa vêm no mesmo recurso/arquivo (1 conector basta) | Precisa de 2 conectores em vez de 1 — mais escopo de `/design`/`/build` | ☐ |

---

## 9. Technical context

| Aspecto | Definição |
|---|---|
| **Onde vive** | `ingestion/src/ingestion/connectors/` (+1-2 conectores), `ingestion/contracts/` (+2 YAML), `ingestion/sql/` (Silver/Gold das 2 tabelas), `api/src/api/config.py` (extensão de `metric_tables`, e possível lógica de resultado primário), `web/` (módulo M02), `ingestion/tests/integration/` (+fixture de ao menos 1 dataset). |
| **Impacto IaC** | Mínimo — reaproveita datasets BQ (`bronze`/`silver`/`gold`) e buckets já existentes; nenhum recurso GCP novo esperado (a confirmar no `/design`). |
| **Domínios de KB** | `PRD-004` (Fiscal & DebtLab), `SPEC-003` (Connectors), `SPEC-004` (RAW/Bronze/Silver/Gold), `SPEC-005` (Data Contracts), `SPEC-007` (Provenance), `SPEC-026` (API/OpenAPI), `SPEC-031`/`ADR-054` (CI Gates — já realizado); `ADR-012` (LLM nunca computa métrica oficial), `ADR-028` (observed/estimated/simulated), `ADR-055` (escrita por partição/backfill resumível — reaproveitar diretamente); `RISK-CONTROL-TEST-MATRIX`; `backlog/BACKLOG-MESTRE.md` `EPIC-009`. |

---

## 10. Data contract (aplicável — 2 datasets de origem)

### Source inventory
- **Receita** — organização e recurso exato a descobrir (Tesouro Transparente RREO/RGF, ou SICONFI). `SOURCE-INDEX.csv` linha 10/11, P0.
- **Despesa** — mesma origem candidata; pode vir no mesmo recurso que receita (`A5`) ou separado.

### Volumes
- Desconhecido até a descoberta real. Estimativa de ordem de grandeza: agregado nacional (ou por UF, se SICONFI) por período — plausivelmente dezenas a centenas de linhas por dataset após agregação (não microdado individual).

### Freshness SLA
- A confirmar na descoberta real (`/design`, tarefa 1) — cadência de publicação da fonte escolhida.

### Schema contract
- Um contrato YAML por dataset (G5): schema esperado (colunas de origem → `reference_date`, `value`), `NOT NULL` em chaves, `value >= 0`. Segue o formato de `ingestion/contracts/divida_consolidada_estados.yaml`.

### Completeness metrics
- Para cada dataset: zero nulo em PK para o `MAX(reference_date)`; cobertura de provenance 100% (S2).

### Lineage requirements
- A cadeia `dataset_registry → GCS RAW (uri) → Bronze (_row_hash) → Silver → Gold → metric_provenance` deve fechar para ≥ 1 período real em cada um dos 2 datasets (AT10/S7).

---

## 11. Clarity score breakdown

| Elemento | Nota | Máx | Observação |
|---|---|---|---|
| Problem | 3 | 3 | Lacuna concreta: M02 sem dado real; `EPIC-009` com 3 stories em aberto; fonte real ainda não catalogada com recurso específico. |
| Users | 2 | 3 | Público do portal + time de implementação + "consumidor futuro" (simulador DebtLab) — o terceiro é não-humano/hipotético, reduz 1 ponto (mesma nota do DEFINE do INSS pelo mesmo motivo). |
| Goals | 3 | 3 | 9 MUST, 1 SHOULD, 2 COULD; todos mensuráveis e rastreáveis ao Brainstorm. |
| Success | 3 | 3 | S1–S7 com números/thresholds (< 5 min, 100% provenance, 0 nulos, ≥ 1 período). |
| Scope | 3 | 3 | Out-of-scope extenso e explícito (9 itens, cada um com destino declarado). |
| **Total** | **14** | **15** | **HIGH — prosseguir para `/design`.** |

---

## 12. Open questions

| ID | Questão | Resolver em |
|---|---|---|
| OQ1 | Fonte real e formato do recurso — Tesouro Transparente (RREO/RGF da União) ou SICONFI (estados/municípios)? Qual granularidade temporal? | `/design`, tarefa 1 (descoberta) |
| OQ2 | 1 ou 2 conectores — receita e despesa no mesmo recurso ou separados (`A5`)? | `/design`, tarefa 1 |
| OQ3 | Resultado primário (G10/`A1`): client-side no módulo web (2 chamadas de API) ou rota dedicada nova? | `/design` |
| OQ4 | Nomenclatura exata do `metric_id` (`fiscal_receita`/`fiscal_despesa`, ou nomes mais específicos à fonte real, ex. `receita_uniao`) | `/design`, após a descoberta nomear os conceitos reais |
| OQ5 | Cap de bytes por query no gate `integration` (achado residual do `CI_ASSURANCE_GATES`, agora com uma 4ª fonte) — revisitar? | `/design`, nota de risco |

---

## 13. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-05 | 1.0 | Criação a partir de `BRAINSTORM_FISCAL_RECEITA_DESPESA.md`. Clarity 14/15. Status → Ready for Design. | /define (Claude Sonnet 5) |
