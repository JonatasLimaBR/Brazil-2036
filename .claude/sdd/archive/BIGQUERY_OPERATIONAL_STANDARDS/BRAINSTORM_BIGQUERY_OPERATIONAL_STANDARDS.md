# BRAINSTORM — BIGQUERY_OPERATIONAL_STANDARDS

- **Feature:** BIGQUERY_OPERATIONAL_STANDARDS
- **Status:** ✅ Shipped

- **Fase:** 0 (Brainstorm)
- **Criado:** 2026-09-06
- **Idioma:** PT-BR (alinhado a `docs/discovery/`)
- **Próximo passo:** `/define .claude/sdd/features/BRAINSTORM_BIGQUERY_OPERATIONAL_STANDARDS.md`

> Nota: assets do plugin SDD ausentes (`kb/_index.yaml`, `BRAINSTORM_TEMPLATE.md` não instalados) —
> documento segue a lista de seções do skill `sdd-brainstorm`, mesmo padrão dos brainstorms
> anteriores.

---

## 1. Ideia

Diferente das 3 fatias anteriores (cada uma um dataset/domínio novo), esta feature é **transversal
à plataforma**: formaliza por escrito as práticas de FinOps/DataOps para BigQuery que hoje são
praticadas de forma **ad-hoc e implícita** — repetidas em cada ADR de fatia (`ADR-052`, `ADR-055`,
`ADR-056`) mas nunca reunidas num único documento de referência — e fecha um gap de código real
já rastreado desde `CI_ASSURANCE_GATES`: **nenhuma query de produção tem cap de custo**
(`maximum_bytes_billed`).

Pedido explícito do usuário ao final da fatia #3 (`FISCAL_RECEITA_DESPESA`): *"vc esta usando as
melhores praticas de finops dataops mlops llmops agentops... ex particionamento de tabelas etc
etc. se nao pode criar prds adrs specs sobre estes assusntos"*. Resposta honesta dada na hora:
particionamento/clustering **já é praticado consistentemente** (3 fatias, sempre `PARTITION BY
reference_date` + `CLUSTER BY` chave de negócio); cap de custo **não existe** (gap real,
`R-012`); MLOps/LLMOps/AgentOps **não se aplicam ainda** (sem modelo/agente em produção —
`EPIC-020`/`EPIC-026`/`EPIC-043` são backlog futuro, criar SPEC pra eles agora seria inventar
requisito). Esta fatia fecha a parte que É real e endereçável hoje: FinOps/DataOps de BigQuery.

---

## 2. Contexto técnico

| Aspecto | Observação |
|---|---|
| **Particionamento/clustering — já praticado, nunca formalizado** | `sql/silver/debt_state.sql`/`gold_debt_state_current.sql`: `PARTITION BY reference_date CLUSTER BY state_ibge_code`. `sql/{silver,gold}/inss_beneficios_*.sql`: idem + `CLUSTER BY ..., especie_codigo`. `sql/{silver,gold}/fiscal_uniao.sql`: idem + `CLUSTER BY metric_id`. Convenção 100% consistente nas 3 fatias, mas só existe como repetição implícita — nenhum SPEC diz "toda tabela nova DEVE seguir isso". |
| **Cap de custo — gap real, já rastreado** | `ingestion/src/ingestion/bigquery_io.py::run_sql()` chama `client.query(sql)` sem `job_config` algum — nenhum `maximum_bytes_billed`. Mesmo gap em `api/src/api/bigquery_repo.py::build_bigquery_run_query()`. Rastreado como achado residual desde `CI_ASSURANCE_GATES` (`SHIPPED §7`: "cap de bytes por query no gate `integration`... aceito, custo ínfimo — mas um cap real precisa tocar código de produção, `bigquery_io.run_sql`"). Nunca endereçado nas 2 fatias seguintes. |
| **Retenção/lifecycle — parcialmente decidido, nunca por escrito** | `infra/terraform/storage.tf`: bucket RAW tem `lifecycle_rule` (deleta versões `ARCHIVED` com +365 dias e mais de 5 versões mais novas) — mas isso só limpa versões antigas de objeto sobrescrito, não é uma política de retenção do dado em si (RAW é imutável por princípio arquitetural, `ADR-0XX`/CONTEXTO). **Nenhuma política de retenção existe para Bronze/Silver/Gold em produção** — só os datasets `citest_*` de CI têm `default_table_expiration_ms` (1h). Nunca decidido por escrito: RAW guarda para sempre? Bronze/Silver têm TTL, já que são recomputáveis a partir de RAW? |
| **`R-012` no Risk Register** | `docs/risks/RISK-REGISTER.md`: "Custo GCP sem controle", severidade média. `RISK-CONTROL-TEST-MATRIX.md`: controle = "budgets + billing export", teste = "cost_guardrail_test" — mais amplo que só o cap de bytes por query (inclui orçamento de projeto e exportação de billing, que é `EPIC-042` STORY-042.01, produto separado). Esta fatia fecha só a parte de controle **por query**, não o orçamento de projeto inteiro. |
| **Precedente de formato** | `SPEC-031-CI-GATES.md` é o modelo mais próximo: um SPEC transversal, não ligado a 1 domínio de produto, formalizando uma prática operacional (gates de CI) que já existia de forma dispersa. Esta fatia segue o mesmo molde para práticas operacionais de BigQuery. |
| **Numeração livre** | `SPEC-034` (próximo após `SPEC-033-MVP-WALKING-SKELETON.md`), `ADR-057` (próximo após `ADR-056`). |

---

## 3. Discovery

| # | Pergunta | Resposta | Impacto no desenho |
|---|---|---|---|
| 1 | Objetivo: só documentar (SPEC/ADR) ou também fechar o gap de código (cap de bytes)? | **Ambos** — SPEC/ADR + implementar o cap agora. | Fatia tem entrega de código real (`bigquery_io.py`, `bigquery_repo.py`), não é só papel. |
| 2 | Valor do cap de `maximum_bytes_billed`? | **1 GB por query** — generoso o bastante pra nunca bloquear uma query real hoje (todas as tabelas do projeto são pequenas), mas pega um erro grosseiro (JOIN sem filtro de partição varrendo tabela inteira) antes de virar custo real. | Valor fixo razoável para o `/define`; `/design` pode revisar contra tamanho real das tabelas se necessário. |
| 3 | Escopo do cap: só ingestão, ou ingestão + API? | **Ingestão + API** — cobre todo ponto de contato com BigQuery no projeto. | 2 pontos de código a mudar: `ingestion/src/ingestion/bigquery_io.py` e `api/src/api/bigquery_repo.py`. |
| 4 | Escopo do SPEC: só cap, ou também particionamento/retenção? | **Cap + particionamento/clustering como norma + retenção/lifecycle** — escopo maior, mais completo. | 1 SPEC consolidado (não 3 documentos pequenos), cobrindo as 3 preocupações operacionais relacionadas de BigQuery. |
| 5 | 1 SPEC consolidado ou 2 separados (FinOps vs. DataOps)? | **1 SPEC consolidado** (decisão de Claude, aceita pelo usuário) — mesmo molde do `SPEC-031-CI-GATES.md` (documento transversal, não ligado a 1 domínio de produto). | Evita ceremônia de múltiplos documentos quase vazios para um escopo pequeno; `SPEC-034` cobre as 3 frentes. |

---

## 4. Inventário de amostras

| Tipo | Disponível? | Uso previsto |
|---|---|---|
| Convenção de particionamento real | Sim — 3 pares Silver/Gold já escritos (`debt_state`, `inss_beneficios_*`, `fiscal_uniao`), todos com `PARTITION BY`/`CLUSTER BY` real. | Base para a seção "convenção obrigatória" do SPEC — extrair o padrão comum, não inventar um novo. |
| Gap de código real | Sim — `bigquery_io.py::run_sql()` e `bigquery_repo.py::build_bigquery_run_query()` lidos, confirmado: nenhum `job_config`/cap hoje. | Ponto exato de mudança de código para o `/design`. |
| Política de retenção parcial real | Sim — `infra/terraform/storage.tf` tem 1 `lifecycle_rule` real (365 dias, versões `ARCHIVED`) só para o bucket RAW; nada para BigQuery em produção. | Base real para a seção de retenção — não é greenfield, já existe 1 precedente parcial a estender/formalizar. |
| Tamanho real das tabelas de produção | Parcial — sabido por esta sessão: INSS Indeferidos ~15.142 linhas (maior Bronze/Gold do projeto); Gold da dívida 27 linhas/ano; Gold fiscal 1.065 linhas. Nenhuma tabela do projeto hoje se aproxima de 1 GB. | Justifica o cap de 1 GB como "generoso, não bloqueante" sem precisar de nova consulta ao BigQuery. |

---

## 5. Abordagens exploradas

### Abordagem A — 1 SPEC consolidado (`SPEC-034`) + 1 ADR (`ADR-057`) para o cap de custo ⭐ Escolhida
- **O quê:** `SPEC-034-BIGQUERY-OPERATIONAL-STANDARDS.md` cobre 3 seções: (1) cap de custo por
  query (`maximum_bytes_billed`, valor e escopo), (2) convenção obrigatória de
  particionamento/clustering para toda tabela nova, (3) política de retenção/lifecycle por camada
  (RAW/Bronze/Silver/Gold). `ADR-057` formaliza especificamente a decisão de código do cap
  (por que 1 GB, por que ingestão+API, alternativas rejeitadas).
- **Prós:** 1 documento de referência único para "como operamos BigQuery neste projeto", igual ao
  papel que `SPEC-031` já cumpre para CI; menos ceremônia que 3 documentos pequenos.
- **Contras:** mistura 3 preocupações (custo, performance/particionamento, retenção) num só
  documento — aceitável porque as 3 são genuinamente relacionadas (todas são "como uma tabela
  BigQuery deve ser operada"), diferente de misturar coisas não relacionadas.
- **Confiança:** 0.85 — molde já provado (`SPEC-031`), conteúdo já existe em código real (não
  greenfield), só falta consolidar.

### Abordagem B — 2 SPECs separados (FinOps vs. DataOps)
- **O quê:** `SPEC-034-FINOPS-COST-GUARDRAILS.md` (só cap de custo) + `SPEC-035-DATA-PLATFORM-STANDARDS.md` (particionamento + retenção).
- **Por que não escolhida:** overhead de 2 ciclos de revisão para um escopo que cabe
  confortavelmente num documento; os 3 assuntos sempre aparecem juntos na prática (a decisão de
  particionar uma tabela É uma decisão de custo).
- **Confiança:** 0.60.

### Abordagem C — Estender `SPEC-004-RAW-BRONZE-SILVER-GOLD.md` em vez de criar um SPEC novo
- **O quê:** adicionar seções de custo/particionamento/retenção dentro do SPEC de arquitetura de
  camadas já existente.
- **Por que não escolhida:** `SPEC-004` documenta **o que** as camadas são e como o dado flui
  entre elas; misturar com **como operamos** (custo, performance, lifecycle) conflacionaria dois
  tipos de contrato diferentes — o mesmo motivo pelo qual `SPEC-031` (CI Gates) é separado de
  `SPEC-030` (Harness) mesmo sendo temas próximos.
- **Confiança:** 0.55.

---

## 6. Itens removidos / adiados (YAGNI)

| Item | Por que fora desta fatia | Vai para |
|---|---|---|
| Dashboards de custo (billing export, cost/source, cost/module, cost/model) | É `EPIC-042` inteiro — feature de produto (Command Center de custo), não uma norma de engenharia. Pedido do usuário era sobre práticas de construção, não sobre um dashboard novo. | `EPIC-042 — FinOps`, fatia própria. |
| Enforcement automático via lint de CI ("toda SQL nova DEVE ter `PARTITION BY`") | Sem ferramenta de lint SQL no projeto hoje (`sqlfluff` mencionado em skills mas não integrado ao `ci.yml`); construir isso é escopo de CI novo, não de norma. | Fatia futura, se o volume de SQL justificar automação. |
| Orçamento de projeto inteiro / alertas de billing (`R-012` completo) | O controle documentado em `RISK-CONTROL-TEST-MATRIX` é mais amplo (orçamento GCP + billing export) que só o cap por query; endereçar o orçamento todo é escopo de infraestrutura (Terraform, `budget.tf` já existe parcialmente) fora desta fatia. | Avaliar `infra/terraform/` numa fatia de FinOps de infraestrutura, se necessário. |
| Automação de delete além do já existente | O bucket RAW já tem 1 `lifecycle_rule`; criar automação de delete para Bronze/Silver/Gold é enforcement de uma política — a política em si (quanto tempo reter) ainda nem existe por escrito. Documentar primeiro, automatizar depois se o custo real justificar. | Fatia futura, se o custo de armazenamento crescer. |
| SPEC/ADR de MLOps/LLMOps/AgentOps | Não há modelo de ML nem agente rodando em produção neste repositório — documentar processo para código que não existe seria inventar requisito (`CLAUDE.md`: "nunca inventar requisitos"). | `EPIC-020` (Forecast), `EPIC-026` (Agents), `EPIC-043` (MLOps/DataOps/LLMOps) — quando esses códigos existirem de verdade. |

---

## 7. Requisitos-rascunho (para o `/define`)

- **R1.** `SPEC-034-BIGQUERY-OPERATIONAL-STANDARDS.md` — seção de cap de custo: `maximum_bytes_billed = 1 GB` (valor revisável), aplicado a toda query de ingestão e de API.
- **R2.** `SPEC-034` — seção de particionamento/clustering: convenção obrigatória (`PARTITION BY` no campo de data de referência, `CLUSTER BY` na(s) chave(s) de negócio) para toda tabela Silver/Gold nova, extraída do padrão já usado nas 3 fatias existentes.
- **R3.** `SPEC-034` — seção de retenção/lifecycle: política por camada (RAW imutável/permanente por princípio arquitetural; Bronze/Silver recomputáveis a partir de RAW — TTL a decidir no `/design`; datasets de CI já têm TTL de 1h, sem mudança).
- **R4.** `ADR-057` — formaliza a decisão de código do cap de custo (valor, escopo, alternativas rejeitadas).
- **R5.** `ingestion/src/ingestion/bigquery_io.py::run_sql()` — ganha `job_config` com `maximum_bytes_billed`, aditivo (todos os callers existentes continuam funcionando sem mudança de assinatura obrigatória).
- **R6.** `api/src/api/bigquery_repo.py::build_bigquery_run_query()` — idem.
- **R7.** Testes de regressão confirmando que uma query dentro do cap funciona normalmente (todas as queries reais do projeto) e que uma query que estimadamente excederia o cap falha de forma clara (não silenciosa).
- **R8.** `docs/risks/RISK-CONTROL-TEST-MATRIX.md` — atualizar `R-012` para referenciar o controle real implementado (cap por query), distinguindo do controle mais amplo (orçamento de projeto) ainda não endereçado.

---

## 8. Decisões autônomas registradas

| Decisão | Motivo |
|---|---|
| 1 SPEC consolidado, não 2 separados | Mesmo molde de `SPEC-031` (documento operacional transversal); os 3 assuntos (custo, particionamento, retenção) são genuinamente relacionados. |
| Cap de 1 GB, não 100 MB | Decisão do usuário — generoso o bastante para nunca bloquear as queries reais e pequenas do projeto hoje. |
| MLOps/LLMOps/AgentOps fora de escopo | Sem modelo/agente em produção — criar SPEC para eles seria inventar requisito, regra inegociável do `CLAUDE.md`. |
| Dashboards de custo (`EPIC-042`) fora de escopo | É uma feature de produto (UI), não uma norma de engenharia — pedido original do usuário era sobre práticas de construção. |

---

## 9. Questões abertas (resolver no `/define` ou `/design`)

1. **TTL exato de Bronze/Silver em produção** (se houver) — Bronze/Silver são recomputáveis a
   partir de RAW a qualquer momento (basta reprocessar), então um TTL de meses/anos pode ser
   seguro; mas isso muda o comportamento de queries históricas (ex.: auditoria). Decisão de
   `/design`, com trade-off explícito.
2. **`maximum_bytes_billed` cobre `LOAD DATA` (DDL) ou só `SELECT`?** — `bronze.load()`/
   `load_partition()` usam `LOAD DATA OVERWRITE` via `run_sql()`; confirmar no `/design` se o cap
   se aplica/faz sentido para jobs de carga (billing de `LOAD DATA` funciona diferente de
   `SELECT` no BigQuery) ou só para leituras/transformações.
3. **Exceção para queries administrativas** (ex.: `INFORMATION_SCHEMA.COLUMNS`, `COUNT(*)`) — essas
   já são baratas por natureza; confirmar que o cap de 1 GB não as afeta na prática (deveria ser
   trivial, mas vale confirmar).

---

## 10. Domínios de KB para a Fase Define

- **SPECs:** `SPEC-004` (camadas, para não conflitar escopo), `SPEC-031` (molde de documento operacional transversal).
- **ADRs:** `ADR-052`/`ADR-055`/`ADR-056` (cada um já documenta particionamento ad-hoc para sua fatia — esta fatia consolida o padrão comum).
- **Riscos:** `docs/risks/RISK-REGISTER.md` (`R-012`), `RISK-CONTROL-TEST-MATRIX.md`.
- **Backlog:** `EPIC-042` (FinOps, para marcar o que fica fora), `EPIC-006` (Data Platform, domínio mais próximo desta fatia).
- **Precedente direto:** os 3 pares Silver/Gold já escritos (`ingestion/sql/{silver,gold}/`), `ingestion/src/ingestion/bigquery_io.py`, `api/src/api/bigquery_repo.py`, `infra/terraform/storage.tf`.

---

## 11. Quality gate (Fase 0)

- [x] Mínimo de 3 perguntas de discovery feitas e respondidas (5 feitas)
- [x] Pergunta de amostras feita — amostras reais encontradas no código (SQL, `bigquery_io.py`, `storage.tf`), não fabricadas
- [x] Pelo menos 2 abordagens exploradas com trade-offs (A, B, C)
- [x] Usuário confirmou explicitamente a abordagem escolhida (A) e o desenho emergente
- [x] YAGNI aplicado — seção de itens removidos preenchida (5 itens)
- [x] Mínimo de 2 validações incrementais concluídas (checkpoint de escopo/valor do cap; checkpoint de desenho final)
- [x] Domínios de KB identificados para o Define
- [x] Requisitos-rascunho prontos para o `/define` (R1–R8)

---

## 12. Handoff

Pronto para `/define .claude/sdd/features/BRAINSTORM_BIGQUERY_OPERATIONAL_STANDARDS.md`.
