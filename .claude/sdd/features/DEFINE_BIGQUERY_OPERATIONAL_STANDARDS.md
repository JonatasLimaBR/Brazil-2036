# DEFINE — BIGQUERY_OPERATIONAL_STANDARDS

## Metadados

- **Feature:** BIGQUERY_OPERATIONAL_STANDARDS
- **Status:** ✅ Complete (Built)
- **Fase:** 1 (Define)
- **Entrada:** `.claude/sdd/features/BRAINSTORM_BIGQUERY_OPERATIONAL_STANDARDS.md` (Ready for Define)
- **Criado:** 2026-09-06
- **Idioma:** PT-BR
- **Clarity score:** 13/15 (HIGH)
- **Branch:** a criar — `chore/bigquery-operational-standards`
- **Próximo passo:** `/design .claude/sdd/features/DEFINE_BIGQUERY_OPERATIONAL_STANDARDS.md`

> Nota: assets do plugin SDD ausentes — documento segue a lista de seções obrigatórias do skill
> `sdd-define`, mesmo padrão das 3 fatias anteriores.

---

## 1. Problem statement

Práticas de FinOps/DataOps para BigQuery são praticadas de forma **consistente mas nunca
formalizada**: particionamento/clustering se repete idêntico em 3 pares Silver/Gold (dívida,
INSS, fiscal) sem nenhum SPEC dizer que é obrigatório; e existe um **gap de código real**
rastreado desde `CI_ASSURANCE_GATES` e nunca fechado — nenhuma query de produção (ingestão ou
API) tem `maximum_bytes_billed`, deixando o projeto sem proteção contra uma query malformada
(ex.: `JOIN` sem filtro de partição) virar custo real.

---

## 2. Target users

| Persona | Descrição | Pain point |
|---|---|---|
| **Time de implementação / agentes de código** (primária) | Quem escreve a próxima tabela BigQuery do projeto | Sem um SPEC de referência, cada fatia nova reinventa (corretamente, até agora, mas por sorte/disciplina) a convenção de particionamento — nada impede que a próxima fatia esqueça. |
| **Responsável pelo orçamento GCP** (secundária) | Quem responde pelo `R-012` (custo GCP sem controle) no Risk Register | Hoje não há nenhuma barreira técnica contra uma query cara — só disciplina de code review. |
| **Futuro auditor/revisor de compliance** (secundária) | Quem precisa confirmar que dado é retido/descartado conforme política | Hoje não existe política de retenção por escrito para Bronze/Silver/Gold — só um `lifecycle_rule` parcial no bucket RAW (Terraform), não documentado como decisão de produto. |

---

## 3. Goals (MoSCoW)

### MUST
- **G1.** `SPEC-034-BIGQUERY-OPERATIONAL-STANDARDS.md` documenta a convenção obrigatória de
  particionamento/clustering para toda tabela Silver/Gold nova, extraída do padrão já usado
  (`PARTITION BY` no campo de data de referência, `CLUSTER BY` na(s) chave(s) de negócio).
- **G2.** `SPEC-034` documenta o cap de custo por query: `maximum_bytes_billed = 1 GB`
  (revisável), com racional (tabelas do projeto hoje são pequenas; o cap pega erro grosseiro, não
  limita uso legítimo).
- **G3.** `ADR-057` formaliza a decisão de código do cap: valor, escopo (ingestão + API),
  alternativas rejeitadas.
- **G4.** `ingestion/src/ingestion/bigquery_io.py::run_sql()` aplica `maximum_bytes_billed` em
  todo `client.query(...)`, de forma aditiva (nenhum caller existente muda de assinatura
  obrigatória).
- **G5.** `api/src/api/bigquery_repo.py::build_bigquery_run_query()` aplica o mesmo cap.
- **G6.** Teste de regressão confirmando que as queries reais do projeto (dívida, INSS, fiscal)
  continuam funcionando normalmente com o cap ativo — nenhuma delas deve chegar perto de 1 GB.
- **G7.** Teste confirmando que uma query que estimadamente excederia o cap falha de forma clara
  e identificável (não silenciosa, não um erro genérico).
- **G8.** `docs/risks/RISK-CONTROL-TEST-MATRIX.md` atualizado: `R-012` passa a referenciar o
  controle real implementado (cap por query), distinguindo do controle mais amplo (orçamento de
  projeto/billing export) que continua em aberto.

### SHOULD
- **G9.** `SPEC-034` documenta uma política de retenção/lifecycle por camada (RAW
  imutável/permanente; Bronze/Silver recomputáveis a partir de RAW — TTL a decidir no `/design`
  com trade-off explícito de auditoria histórica).

### COULD
- **G10.** Nota curta no `CLAUDE.md`/`INDEX.md` apontando o `SPEC-034` como referência para
  qualquer fatia futura que crie uma tabela BigQuery nova.

---

## 4. Success criteria (mensuráveis)

| # | Critério | Medição |
|---|---|---|
| S1 | Cap de custo ativo | 100% das chamadas `client.query()` em `ingestion/` e `api/` passam por um `job_config` com `maximum_bytes_billed` definido — confirmado por leitura de código, não por amostra. |
| S2 | Sem regressão | Todas as queries reais das 3 fatias existentes (dívida, INSS, fiscal) continuam retornando resultado idêntico ao de antes do cap — `pytest` das 3 fatias verde. |
| S3 | Falha clara acima do cap | Uma query sintética que excede 1 GB estimado falha com um erro identificável no teste, não trava nem retorna resultado parcial silencioso. |
| S4 | Convenção documentada | `SPEC-034` existe, com pelo menos particionamento/clustering (G1) e cap de custo (G2) cobertos; qualquer leitor consegue extrair a regra sem precisar ler os 3 ADRs de fatia. |
| S5 | `R-012` atualizado | `RISK-CONTROL-TEST-MATRIX.md` reflete o controle real implementado, sem alegar cobertura que não existe (orçamento de projeto continua "não implementado", declarado explicitamente). |
| S6 | `/verify-spec` PASS | Verificação independente (sessão nova, read-only) = OVERALL PASS. |
| S7 | `ci-gate` verde | Todo PR desta fatia passa pelo `ci-gate` sem gate enfraquecido. |

---

## 5. Acceptance tests

- **AT1 — cap aplicado na ingestão.** *Given* qualquer chamada a `bigquery_io.run_sql()`, *When*
  inspeciono o `job_config` passado ao client real, *Then* `maximum_bytes_billed` está definido
  com o valor documentado no `SPEC-034`.
- **AT2 — cap aplicado na API.** *Given* qualquer chamada via `build_bigquery_run_query()`,
  *When* inspeciono o `job_config`, *Then* idem AT1.
- **AT3 — sem regressão nas 3 fatias.** *Given* o cap ativo, *When* rodo os testes de
  `ingestion/`/`api/` (unit + o gate `integration` contra BigQuery real), *Then* todos passam como
  antes.
- **AT4 — falha clara acima do cap.** *Given* uma query sintética de teste que excede o cap
  (ex.: aponta pra uma tabela de teste grande, ou usa um cap artificialmente baixo no teste),
  *When* executo via o mesmo caminho de código, *Then* recebo um erro do tipo esperado do
  BigQuery (`google.api_core.exceptions` correspondente), não um travamento ou silêncio.
- **AT5 — SPEC cobre particionamento.** *Given* o `SPEC-034` publicado, *When* comparo contra os
  3 pares Silver/Gold já existentes, *Then* a convenção documentada bate exatamente com o padrão
  real usado (não uma regra inventada).
- **AT6 — SPEC cobre retenção (SHOULD).** *Given* o `SPEC-034` publicado, *When* leio a seção de
  retenção, *Then* ela declara explicitamente a política por camada (mesmo que a decisão seja
  "sem TTL por enquanto, revisar quando o custo justificar" — desde que seja uma decisão
  documentada, não um silêncio).
- **AT7 — `R-012` não infla cobertura.** *Given* `RISK-CONTROL-TEST-MATRIX.md` atualizado, *When*
  leio a linha de `R-012`, *Then* ela distingue claramente "cap por query: implementado" de
  "orçamento de projeto/billing export: não implementado nesta fatia".
- **AT8 — CI ritual completo.** *Given* qualquer PR desta fatia, *When* o CI roda, *Then*
  `ci-gate` resolve e bloqueia merge se qualquer gate falhar.

---

## 6. Out of scope

| Item | Motivo | Destino |
|---|---|---|
| Dashboards de custo (billing export, cost/source, cost/module, cost/model) | É `EPIC-042` inteiro — feature de produto (Command Center de custo), não norma de engenharia. | `EPIC-042 — FinOps`, fatia própria. |
| Enforcement automático via lint de CI | Sem ferramenta de lint SQL integrada ao `ci.yml` hoje; construir isso é escopo de CI novo. | Fatia futura, se o volume de SQL justificar. |
| Orçamento de projeto inteiro / alertas de billing GCP | Mais amplo que o cap por query; é infraestrutura (Terraform `budget.tf`), não código de aplicação. | Fatia futura de FinOps de infraestrutura. |
| Automação de delete além do já existente (`storage.tf`) | A política de retenção em si ainda não existe por escrito — documentar primeiro. | Fatia futura, se o custo de armazenamento justificar. |
| SPEC/ADR de MLOps/LLMOps/AgentOps | Sem modelo de ML nem agente em produção — documentar processo pra código inexistente seria inventar requisito. | `EPIC-020`/`EPIC-026`/`EPIC-043`, quando esses códigos existirem. |
| Mudar o valor do cap por dataset/query individualmente | Escopo desta fatia é um cap global simples; caps diferenciados por dataset são complexidade sem necessidade comprovada ainda. | Reavaliar se algum dataset futuro legitimamente precisar de mais de 1 GB por query. |

---

## 7. Constraints

- **C1.** Mudança de código aditiva — nenhum caller existente de `run_sql()`/
  `build_bigquery_run_query()` pode quebrar ou mudar de assinatura obrigatória.
- **C2.** Não enfraquecer gates existentes (`SPEC-031`).
- **C3.** `SPEC-034` deve refletir a convenção **real** já em uso, não inventar uma nova — extraída
  dos 3 pares Silver/Gold existentes.
- **C4.** Todo merge em `main` é via PR (branch protection).
- **C5.** Sem infraestrutura de CI nova — reaproveita `ci-gate`/gates existentes.

---

## 8. Assumptions / risk register

| ID | Afirmação | Impacto se falsa | Validada |
|---|---|---|---|
| A1 | 1 GB é generoso o bastante para nunca bloquear uma query real e legítima do projeto hoje | Alguma query real do projeto passaria de 1 GB e quebraria em produção — precisaria de um cap maior ou exceção por dataset | ☐ |
| A2 | `maximum_bytes_billed` funciona da mesma forma para `SELECT` e para `LOAD DATA` (usado por `bronze.load()`/`load_partition()`) via `client.query()` | Se o comportamento for diferente para DDL de carga, o cap pode não se aplicar onde mais importa, ou pode quebrar cargas legítimas — precisa investigação real no `/design` | ☐ |
| A3 | Bronze/Silver são seguramente recomputáveis a partir de RAW a qualquer momento, então um TTL futuro não perde informação de verdade | Se algum processo depender de Bronze/Silver históricos além do que RAW permite reconstruir, um TTL futuro perderia dado — mitigado por esta fatia só *documentar* a política, não implementar TTL agora (G9 é SHOULD, não MUST) | ☐ |

---

## 9. Technical context

| Aspecto | Definição |
|---|---|
| **Onde vive** | `docs/specs/SPEC-034-BIGQUERY-OPERATIONAL-STANDARDS.md` (novo), `docs/adrs/ADR-057-*.md` (novo), `ingestion/src/ingestion/bigquery_io.py` (modificar), `api/src/api/bigquery_repo.py` (modificar), `ingestion/tests/`/`api/tests/` (+testes), `docs/risks/RISK-CONTROL-TEST-MATRIX.md` (modificar), `INDEX.md` (modificar). |
| **Impacto IaC** | Nenhum esperado — mudança é só nível de aplicação (`job_config` na chamada BigQuery), não infraestrutura Terraform. |
| **Domínios de KB** | `SPEC-004` (camadas, para não conflitar escopo), `SPEC-031` (molde de documento operacional transversal); `ADR-052`/`ADR-055`/`ADR-056` (particionamento ad-hoc por fatia, a consolidar); `RISK-REGISTER.md`/`RISK-CONTROL-TEST-MATRIX.md` (`R-012`). |

---

## 10. Data contract (não aplicável)

Esta fatia não introduz uma fonte de dado nova — é uma norma operacional transversal sobre como o
BigQuery já é usado pelas 3 fatias existentes. Não há schema/contrato de dado novo; o "contrato"
desta fatia é de código (assinatura aditiva de `run_sql()`/`build_bigquery_run_query()`, coberta
pelas Constraints C1 e pelos Acceptance Tests AT1–AT4).

---

## 11. Clarity score breakdown

| Elemento | Nota | Máx | Observação |
|---|---|---|---|
| Problem | 3 | 3 | Gap real e concreto: prática consistente mas não documentada + gap de código rastreado desde `CI_ASSURANCE_GATES`. |
| Users | 2 | 3 | Time de implementação + responsável de orçamento + auditor futuro — os 2 últimos são papéis, não pessoas identificadas no projeto ainda (reduz 1 ponto, mesmo padrão das fatias anteriores). |
| Goals | 3 | 3 | 8 MUST, 1 SHOULD, 1 COULD; todos mensuráveis e rastreáveis ao Brainstorm. |
| Success | 3 | 3 | S1–S7 com critérios verificáveis (100% das chamadas, testes verdes, documento existe e bate com o real). |
| Scope | 2 | 3 | Out-of-scope bem povoado (6 itens), mas o valor exato do cap (1 GB) e o TTL de retenção (G9, SHOULD) ainda têm uma pergunta aberta cada (A1, A3) — não 100% fechado, reduz 1 ponto. |
| **Total** | **13** | **15** | **HIGH — prosseguir para `/design`.** |

---

## 12. Open questions

| ID | Questão | Resolver em |
|---|---|---|
| OQ1 | `maximum_bytes_billed` se aplica a `LOAD DATA` (usado por `bronze.load()`) da mesma forma que a `SELECT`? | `/design`, tarefa 1 (investigação real da API do BigQuery) |
| OQ2 | TTL exato de Bronze/Silver (se algum) — meses? anos? nunca? | `/design`, com trade-off explícito de auditoria histórica vs. custo de armazenamento |
| OQ3 | Queries administrativas (`INFORMATION_SCHEMA.COLUMNS`, `COUNT(*)`) são afetadas na prática pelo cap de 1 GB? | `/design`, confirmar que são triviais e não relevantes |

---

## 13. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-06 | 1.0 | Criação a partir de `BRAINSTORM_BIGQUERY_OPERATIONAL_STANDARDS.md`. Clarity 13/15. Status → Ready for Design. | /define (Claude Sonnet 5) |
