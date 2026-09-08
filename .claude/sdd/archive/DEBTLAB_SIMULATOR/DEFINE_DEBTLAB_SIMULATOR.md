# DEFINE — DEBTLAB_SIMULATOR

## Metadados

- **Feature:** DEBTLAB_SIMULATOR
- **Status:** ✅ Shipped

> Shipped and archived 2026-09-08.
- **Fase:** 1 (Define)
- **Entrada:** `.claude/sdd/features/BRAINSTORM_DEBTLAB_SIMULATOR.md` (Ready for Define)
- **Criado:** 2026-09-07
- **Idioma:** PT-BR
- **Clarity score:** 13/15 (HIGH)
- **Branch:** a criar — `feature/debtlab-simulator`
- **Próximo passo:** `/design .claude/sdd/features/DEFINE_DEBTLAB_SIMULATOR.md`

> Nota: assets do plugin SDD ausentes — documento segue a lista de seções obrigatórias do skill
> `sdd-define`, mesmo padrão das fatias anteriores.

---

## 1. Problem statement

O projeto tem 6 features shipadas, todas de **ingestão de dado observado** — nenhuma ainda prova o
padrão "núcleo determinístico, borda probabilística" (`ADR-013`/`ADR-042`) que é um diferencial
central do produto. O `DebtLab` (`SIM-002`, `SPEC-010`, `PRD-004`) é o simulador com menor gap de
dado real (dívida e resultado primário já estão em Gold), mas produzir a razão dívida/PIB — o que
o `SPEC-010` de fato pede — exige PIB real, que não existe no projeto ainda (`EPIC-008` nunca
construído). Decisão explícita do usuário no `/brainstorm`: não simplificar para uma versão sem
PIB real — esta fatia ingere PIB de verdade, constrói o engine determinístico e adiciona uma
camada Monte Carlo (`SPEC-016`), tudo numa entrega combinada.

---

## 2. Target users

| Persona | Descrição | Pain point |
|---|---|---|
| **Analista fiscal / pesquisador** (primária, `PRD-004`) | Quer projetar a trajetória da dívida sob diferentes premissas de juros/primário | Hoje só vê o dado observado (dívida 2022, primário mensal) — sem forma de simular cenários futuros |
| **Avaliador do concurso CGU** (secundária) | Julga o reuso de dados abertos por sofisticação analítica, não só visualização | Sem um simulador real, o projeto mostra só ingestão/exibição de dado, não "inteligência" aplicada sobre ele |

---

## 3. Goals (MoSCoW)

### MUST
- **G1.** Ingerir PIB real (fonte a confirmar no `/design` — BCB SGS ou IBGE Contas
  Nacionais/SIDRA) via pipeline RAW→Bronze→Silver→Gold, mesmo contrato/provenance das 3 fatias
  anteriores.
- **G2.** Engine determinístico DebtLab (`SPEC-010`): `dívida_t = dívida_(t-1) × (1 + juros) −
  primário_t`, dividido pelo PIB do ano de referência, horizonte de 10 anos, fora do LLM,
  parâmetros e versão do modelo persistidos.
- **G3.** Camada Monte Carlo (`SPEC-016`) sobre o engine: cada premissa (juros, primário) recebe
  média ± desvio-padrão, N iterações, saída P10/P25/P50/P75/P90 por ano, seed fixável para
  reprodutibilidade.
- **G4.** Toda saída do simulador rotulada `SIMULATED` (`ADR-028`), visual/estruturalmente
  distinguível de dado observado — sem publicação automática como métrica oficial.
- **G5.** Persistência de cenários/resultados em tabela operacional no BigQuery
  (`br2036_control`) — não em AlloyDB (achado real: nunca provisionado, custo fixo contradiz
  `ADR-002` sem approval workflow real que o justifique).
- **G6.** Endpoint(s) de API para criar um cenário (premissas) e consultar seu resultado
  (trajetória determinística + percentis).
- **G7.** Nenhum caminho de LLM pode substituir o cálculo do engine (`SPEC-010`/`ADR-012`) — texto
  explicativo gerado por IA, se existir, cita o resultado do engine, nunca recalcula.
- **G8.** Testes unitários da fórmula de dinâmica + conferência manual da razão dívida/PIB do ano
  mais recente contra a série oficial do BCB ("Dívida Bruta do Governo Geral % PIB"), mesmo
  padrão de verificação manual já usado em `FISCAL_RECEITA_DESPESA`.

### SHOULD
- **G9.** `ADR-059` (número a confirmar) formalizando a decisão de persistir cenários em BigQuery
  em vez de AlloyDB para o V1 — referencia `ADR-004` sem superá-lo.
- **G10.** Base nacional de dívida para o cenário — decidir no `/design` se agrega as 27 UFs de
  `divida_consolidada` ou usa outro agregado, já que o `SIM-002` compara com PIB nacional.

### COULD
- **G11.** Endpoint assíncrono (job + polling) para a criação de cenário, se o tempo de resposta
  do Monte Carlo (N iterações) não couber num request síncrono de Cloud Run — decisão técnica do
  `/design`.

---

## 4. Success criteria (mensuráveis)

| # | Critério | Medição |
|---|---|---|
| S1 | PIB real carregado e servido | ≥1 período real de PIB em Gold; endpoint funcionando; valor conferido manualmente contra a fonte oficial. |
| S2 | Engine determinístico reproduzível | Mesmo input (dívida base, premissas, horizonte) produz sempre a mesma trajetória de 10 anos — testado. |
| S3 | Monte Carlo reproduzível | Mesmo `seed` produz os mesmos P10/P25/P50/P75/P90 em execuções repetidas. |
| S4 | Razão dívida/PIB confere | Razão calculada para o ano real mais recente bate (tolerância definida no `/design`) contra a série oficial do BCB. |
| S5 | Sem fabricação/publicação indevida | 100% das saídas rotuladas `SIMULATED`; nenhum endpoint "publica" cenário como oficial. |
| S6 | `/verify-spec` PASS | Verificação independente (sessão nova, read-only) = OVERALL PASS, incluindo checagem de que o engine não foi substituído por cálculo de LLM. |
| S7 | `ci-gate` verde | Todo PR desta fatia passa pelo `ci-gate` sem gate enfraquecido. |

---

## 5. Acceptance tests

- **AT1 — engine determinístico correto.** *Given* dívida base, primário, juros e PIB conhecidos,
  *When* o engine roda, *Then* o resultado bate exatamente a fórmula documentada (teste unitário
  com valores sintéticos calculados à mão).
- **AT2 — persistência funciona.** *Given* um cenário criado (`scenario_id`), *When* consulto o
  resultado depois, *Then* recebo exatamente os mesmos valores (nenhuma recomputação silenciosa).
- **AT3 — Monte Carlo reproduzível.** *Given* o mesmo `seed` e as mesmas premissas, *When* rodo a
  simulação duas vezes, *Then* os percentis são idênticos.
- **AT4 — razão dívida/PIB confere contra referência oficial.** *Given* o ano real mais recente
  disponível, *When* calculo a razão dívida/PIB, *Then* o valor bate (dentro de tolerância) contra
  a série pública do BCB.
- **AT5 — rótulo SIMULATED sempre presente.** *Given* qualquer resultado do simulador, *When*
  inspeciono a resposta da API, *Then* ela inclui `data_class=SIMULATED` e a versão do engine.
- **AT6 — sem publicação oficial.** *Given* a API completa desta fatia, *When* procuro por uma
  ação de "publicar cenário como oficial", *Then* ela não existe (fora de escopo, `PRD-004 §5`).
- **AT7 — PIB real sem fabricação.** *Given* o dado de PIB ingerido, *When* comparo contra a fonte
  oficial, *Then* os valores batem exatamente (mesmo padrão de conferência manual das fatias
  anteriores) — nenhum valor estimado/interpolado apresentado como observado.
- **AT8 — ritual de CI completo.** *Given* qualquer PR desta fatia, *When* o CI roda, *Then*
  `ci-gate` resolve e bloqueia merge se qualquer gate falhar.

---

## 6. Out of scope

| Item | Motivo | Destino |
|---|---|---|
| Approval workflow / publicação oficial de cenário | `PRD-004 §5` já exclui do V1; sem RBAC/ABAC ainda, não há "quem" aprovaria. | `ADR-019`/`ADR-020`, quando RBAC/ABAC (próxima fatia da sequência) existir. |
| AlloyDB provisionado | Custo fixo sem approval workflow/checkpoint real que justifique agora (`ADR-002`). | Reavaliar quando agentes/checkpoints (`ADR-021`) virarem reais. |
| Outros simuladores do catálogo (Fiscal `SIM-003`, State Fiscal Twin `SIM-012`, etc.) | Esta fatia é só o DebtLab. | Fatias futuras de simulador. |
| UI/painel completo na Landing para o simulador | `LANDING_PAGE_ASTRO` já shipou; UI de simulador é aditiva a uma fatia futura (Policy Lab/portal). | Fatia futura de UI, se pedida. |
| Outras variáveis do Macro Twin (inflação, juros, câmbio, consumo, investimento, trade, forecast) | Só PIB é necessário para alimentar o DebtLab. | `EPIC-008`, conforme demanda futura. |
| Monte Carlo Global (`SIM-019`, correlação entre múltiplos simuladores) | Esta fatia aplica Monte Carlo só dentro do DebtLab, sem correlação entre simuladores diferentes. | `SIM-019`, quando houver mais de 1 simulador. |

---

## 7. Constraints

- **C1.** O engine roda inteiramente fora do LLM (`ADR-042`); nenhum caminho de LLM recalcula o
  resultado (`SPEC-010`/`ADR-012`).
- **C2.** Toda saída do simulador é visual/estruturalmente distinguível como `SIMULATED`
  (`ADR-028`).
- **C3.** Sem provisionamento de AlloyDB nesta fatia — persistência de cenário em BigQuery
  (`br2036_control`).
- **C4.** Todo merge em `main` é via PR (branch protection).
- **C5.** Reusa `ci-gate`/gates já existentes — ajustar se necessário para os novos testes, sem
  enfraquecer o gate.
- **C6.** Sem approval workflow novo nesta fatia (`PRD-004 §5`).

---

## 8. Assumptions / risk register

| ID | Afirmação | Impacto se falsa | Validada |
|---|---|---|---|
| A1 | A fonte de PIB real (BCB SGS ou IBGE) tem granularidade/disponibilidade suficiente para alimentar um cenário anual de 10 anos, sem gap de série | Pode exigir interpolação ou uma fonte alternativa — mais escopo de `/design` | ☐ |
| A2 | A dívida nacional pode ser derivada agregando as 27 UFs de `divida_consolidada` sem distorção relevante frente à razão dívida/PIB nacional | Pode ser necessário buscar/ingerir um agregado nacional separado, em vez de somar | ☐ |
| A3 | O N de iterações do Monte Carlo roda dentro de um tempo de resposta aceitável em Cloud Run síncrono, sem exigir infraestrutura assíncrona nova | Pode exigir endpoint assíncrono (job + polling) — mais escopo de `/design` (`G11`) | ☐ |

---

## 9. Technical context

| Aspecto | Definição |
|---|---|
| **Onde vive** | `ingestion/src/ingestion/connectors/` (novo conector de PIB), `ingestion/src/ingestion/simulators/` ou equivalente (novo módulo de engine — nome exato decidido no `/design`), `api/src/api/` (novos endpoints de simulação), `docs/adrs/` (+1 ADR). |
| **Impacto IaC** | Nenhum esperado em Terraform — reusa BigQuery já provisionado; sem AlloyDB nesta fatia. |
| **Domínios de KB** | `PRD-004`, `SPEC-010`, `SPEC-016`, `SPEC-009` (parte PIB), `SPEC-004`, `SPEC-007`; `ADR-013`, `ADR-042`, `ADR-028`, `ADR-016`, `ADR-004` (referenciado), `ADR-002`, `ADR-012`. |

---

## 10. Data contract (PIB — parte de ingestão)

| Aspecto | Definição |
|---|---|
| **Fonte** | A confirmar no `/design` por inspeção real (BCB SGS vs. IBGE Contas Nacionais/SIDRA) — mesmo padrão de "nunca supor formato" usado em `FISCAL_RECEITA_DESPESA`. |
| **Volume** | Pequeno — série anual ou trimestral, dezenas a poucas centenas de linhas (mesma ordem de grandeza da série de dívida/fiscal). |
| **Freshness** | Não é streaming — atualização periódica conforme a fonte oficial publica (anual/trimestral). |
| **Completude** | 100% dos períodos publicados oficialmente pela fonte escolhida. |
| **Schema (rascunho, confirmar no `/design`)** | `reference_year` (ou `reference_date`), `pib_valor` (R$ correntes), `metodologia`/`fonte`, seguindo o mesmo padrão de contrato (`ingestion/contracts/*.yaml`) das 3 fatias anteriores. |

---

## 11. Clarity score breakdown

| Elemento | Nota | Máx | Observação |
|---|---|---|---|
| Problem | 3 | 3 | Gap concreto e real (PIB ausente), descoberto nesta sessão, não hipotético. |
| Users | 2 | 3 | Persona primária bem definida (`PRD-004`); avaliador CGU é papel, não pessoa identificada — mesmo padrão conservador das fatias anteriores. |
| Goals | 3 | 3 | 8 MUST, 2 SHOULD, 1 COULD; todos mensuráveis e rastreáveis ao Brainstorm. |
| Success | 3 | 3 | S1–S7 com critérios verificáveis. |
| Scope | 2 | 3 | Out-of-scope bem povoado (6 itens), mas 3 assumptions reais (A1–A3) ainda não validadas — a fonte exata de PIB e a base nacional de dívida carregam incerteza técnica genuína, só resolvida no `/design`. |
| **Total** | **13** | **15** | **HIGH — prosseguir para `/design`.** |

---

## 12. Open questions

| ID | Questão | Resolver em |
|---|---|---|
| OQ1 | Fonte exata de PIB real (BCB SGS vs. IBGE) e periodicidade | `/design`, descoberta real |
| OQ2 | Dívida nacional: somar as 27 UFs ou usar outro agregado? | `/design` |
| OQ3 | N de iterações do Monte Carlo (trade-off custo/precisão) | `/design` |
| OQ4 | Endpoint síncrono ou assíncrono (job+polling) para a simulação | `/design`, depende de A3 |
| OQ5 | Schema exato da tabela operacional em `br2036_control` (particionamento, retenção) | `/design` |
| OQ6 | Número exato do novo ADR (`ADR-059` provável, confirmar contra `docs/adrs/` no momento da execução) | `/design` |

---

## 13. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-07 | 1.0 | Criação a partir de `BRAINSTORM_DEBTLAB_SIMULATOR.md`. Clarity 13/15. Status → Ready for Design. | /define (Claude Sonnet 5) |
