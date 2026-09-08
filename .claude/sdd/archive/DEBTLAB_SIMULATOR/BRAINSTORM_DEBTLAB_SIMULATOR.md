# BRAINSTORM — DEBTLAB_SIMULATOR

- **Feature:** DEBTLAB_SIMULATOR
- **Status:** ✅ Shipped

> Shipped and archived 2026-09-08.

- **Fase:** 0 (Brainstorm)
- **Criado:** 2026-09-07
- **Idioma:** PT-BR (alinhado a `docs/discovery/`)
- **Próximo passo:** `/define .claude/sdd/features/BRAINSTORM_DEBTLAB_SIMULATOR.md`

> Nota: assets do plugin SDD ausentes (`kb/_index.yaml`, `BRAINSTORM_TEMPLATE.md` não instalados) —
> documento segue a lista de seções do skill `sdd-brainstorm`, mesmo padrão dos brainstorms
> anteriores.

---

## 1. Ideia

Primeiro simulador determinístico do projeto (`SIM-002 — DebtLab`, `SPEC-010`, `PRD-004`) —
nenhuma das 6 features shipadas até aqui tocou o padrão "núcleo determinístico fora do LLM"
(`ADR-013`/`ADR-042`), só ingestão de dado observado. Escolhido entre os 24 simuladores do
catálogo (`docs/simulators/SIMULATORS-CATALOG.md`) por ser o que melhor aproveita dado real já
carregado: dívida consolidada por UF (`MVP_WALKING_SKELETON`) e resultado primário
(`FISCAL_RECEITA_DESPESA`) já estão em Gold.

**Escopo cresceu durante a descoberta, por decisão explícita do usuário.** A primeira proposta
(Cláudio) era simplificar o V1 para produzir só a dívida projetada em R$ absoluto, sem a razão
dívida/PIB, porque **PIB real não existe no projeto ainda** (Macro Twin, `EPIC-008`, nunca
construído). O usuário rejeitou a simplificação ("incluir tudo que falta para entregar dados
reais") — decisão: esta fatia passa a incluir também a ingestão de **PIB real** (parte de
`EPIC-008`/`STORY-008.01`), para que a razão dívida/PIB seja genuína, não um workaround. Na
sequência, o usuário também pediu Monte Carlo (P10/P50/P90, `SPEC-016`/`ADR-016`) já no V1, em vez
de deixar para um simulador futuro (`SIM-019 — Monte Carlo Global`).

Resultado: esta fatia combina 3 capacidades reais numa entrega só — (1) ingestão de PIB real
(padrão RAW→Bronze→Silver→Gold já provado 3x), (2) engine determinístico DebtLab, (3) camada Monte
Carlo por cima do engine.

---

## 2. Contexto técnico

| Aspecto | Observação |
|---|---|
| **Dado real disponível para alimentar o simulador** | `divida_consolidada` (27 linhas, 2022, por UF — `gold_debt_state_current`), `fiscal_primario` (355 meses, 1997–2026, nacional — `gold_fiscal_uniao`). Ambos já em produção, endpoints públicos funcionando. |
| **PIB real — não existe, precisa ser ingerido** | `EPIC-008 — Macro Twin` (`STORY-008.01 — PIB`) nunca foi construído. Nenhum conector, nenhuma tabela Bronze/Silver/Gold de PIB hoje. Fonte exata (BCB SGS vs. IBGE Contas Nacionais/SIDRA) e periodicidade (trimestral vs. série mensal acumulada) **não foram inspecionadas de verdade nesta sessão** — fica para a "descoberta real" do `/design`, mesmo padrão usado em `FISCAL_RECEITA_DESPESA` (inspecionar o dado real antes de desenhar o pipeline, nunca supor formato). |
| **Ground truth para validar a razão dívida/PIB** | BCB publica oficialmente "Dívida Bruta do Governo Geral (% PIB)" — série de referência para conferir manualmente o ponto de partida do simulador, mesmo padrão de conferência manual já usado em `FISCAL_RECEITA_DESPESA` (jul/2026 bateu exatamente contra o arquivo-fonte). |
| **AlloyDB (`ADR-004`) — decidido em ADR, nunca provisionado** | `infra/terraform/` não tem nenhum recurso AlloyDB (confirmado por grep nesta sessão). O projeto segue `ADR-002` (serverless-first, custo baixo para o MVP) — provisionar um cluster AlloyDB (custo fixo mesmo parado) só para guardar cenários de simulação, sem approval workflow/checkpoints reais ainda para justificar, contradiria o driver de custo do próprio `ADR-002`. **Decisão do usuário:** V1 persiste cenários/resultados numa tabela operacional no BigQuery (`br2036_control`, já provisionado), não em AlloyDB. `ADR-004` continua válido para quando approval workflow/checkpoints de agente virarem reais. |
| **Fórmula de dinâmica da dívida** | Equação padrão de sustentabilidade fiscal: `dívida_t = dívida_(t-1) × (1 + juros) − primário_t`, dividida pelo PIB do ano para a razão. `SPEC-010` já define os inputs (base debt/GDP, juros, crescimento, primário, horizonte, `scenario_id`) e exige saída classificada `SIMULATED`, versionada, sem caminho de LLM substituindo o engine. |
| **Monte Carlo** | `SPEC-016`/`ADR-016`: distribuições explícitas, saída P10/P25/P50/P75/P90, seed fixável para reprodutibilidade, nunca apresentar percentil como fato observado. Usuário confirmou parametrização por **média ± desvio-padrão** por premissa (juros, primário) — distribuição normal, N iterações, mesmo padrão que `SIM-019` formalizaria separadamente, mas aqui aplicado só ao DebtLab. |
| **Sem approval workflow novo** | `PRD-004 §5` já lista "fora de escopo V1: recomendação normativa automática; publicação de meta oficial" — saída sempre rotulada `SIMULATED`, nunca "publicada" como oficial. Não precisa do approval workflow (`ADR-019`/`ADR-020`) que RBAC/ABAC (próxima fatia da sequência combinada de 4) ainda vai trazer. |
| **Horizonte de projeção** | 10 anos — padrão de análise fiscal de médio prazo, confirmado com o usuário. |
| **Precedente de engine fora do LLM** | Nenhum — esta é a primeira vez que o projeto constrói um "núcleo determinístico" (`ADR-013`) de verdade. `ingestion/` hoje só tem pipelines de ingestão/transformação SQL, nenhum motor de simulação Python. Vai precisar de um módulo novo (`ingestion/src/ingestion/simulators/` ou equivalente — decisão de estrutura de arquivo é do `/design`). |
| **Numeração livre** | Próximo SPEC: `SPEC-035` (depois de `SPEC-034`). Próximo ADR: `ADR-059` (depois de `ADR-058`). PIB pode reaproveitar `SPEC-009-MACRO-TWIN.md` (já existe, cobre PIB/inflação/juros/câmbio/consumo/investimento/trade/forecast — esta fatia só realiza a fatia PIB dele) em vez de criar um SPEC novo. |

---

## 3. Discovery

| # | Pergunta | Resposta | Impacto no desenho |
|---|---|---|---|
| 1 | Qual simulador construir primeiro, dos 24 do catálogo? | **DebtLab (`SIM-002`)** — dado real de dívida e primário já carregado; Previdência (`SIM-004`) exigiria premissas demográficas/salariais sem nenhum dado real de base. | Escopo fixado em `SPEC-010`/`PRD-004`. |
| 2 | Como resolver a falta de PIB real (necessário pra razão dívida/PIB)? | **Ingerir PIB real** nesta mesma fatia, não simplificar pra R$ absoluto nem usar PIB como parâmetro digitado pelo usuário. | Puxa parte de `EPIC-008` (Macro Twin) pra dentro desta feature — fatia combinada, não só simulador. |
| 3 | Separar em 2 features (PIB depois DebtLab) ou 1 combinada? | **1 fatia combinada** — usuário confirmou explicitamente. | Manifesto de arquivos vai ter tanto conector de dado quanto engine de simulação. |
| 4 | Existe referência oficial pra validar a razão calculada? | **Sim** — BCB publica "Dívida Bruta do Governo Geral (% PIB)". | Vira parte da estratégia de teste/verificação do `/design`, mesmo padrão de conferência manual das fatias anteriores. |
| 5 | Incluir Monte Carlo (P10/P50/P90) no V1, ou deixar pra um simulador futuro (`SIM-019`)? | **Incluir já no V1** — usuário rejeitou a simplificação puramente determinística. | Engine ganha uma segunda camada (amostragem probabilística) além da trajetória determinística; `SPEC-016`/`ADR-016` entram no escopo. |
| 6 | Como o usuário parametriza a incerteza de cada premissa pro Monte Carlo? | **Média ± desvio-padrão** (distribuição normal), por recomendação aceita. | Contrato de input do cenário: cada premissa tem valor central + desvio, não só um número. |
| 7 | Onde persistir cenários/resultados (AlloyDB, decidido em `ADR-004`, nunca provisionado)? | **Tabela operacional no BigQuery** (`br2036_control`) para o V1 — evita provisionar AlloyDB (custo fixo, contra `ADR-002`) sem approval workflow real que o justifique ainda. | Sem infra nova no Terraform nesta fatia; `ADR-004` permanece válido pro futuro (nota explícita, não superseded). |
| 8 | Horizonte de projeção? | **10 anos.** | Define o tamanho da série de saída por cenário/iteração. |

---

## 4. Inventário de amostras

| Tipo | Disponível? | Uso previsto |
|---|---|---|
| Dívida consolidada real (base do cenário) | Sim — `gold_debt_state_current`, 27 linhas, 2022, por UF; endpoint `/v1/metrics/divida_consolidada` já em produção. | Valor inicial (`t=0`) da trajetória — nacional é a soma por UF, ou usar direto o agregado se existir; confirmar no `/design`. |
| Resultado primário real (série histórica) | Sim — `gold_fiscal_uniao`, `metric_id=fiscal_primario`, 355 meses (1997–2026); endpoint `/v1/metrics/fiscal_primario/national`. | Ancora o "primário" real dos últimos anos; usuário define premissa de primário futuro no cenário (constante, ou média histórica como sugestão de default). |
| PIB real | **Não** — precisa de ingestão nova. | Descoberta real de fonte/formato é tarefa do `/design`, não deste documento. |
| Ground truth para dívida/PIB | Sim, referência externa conhecida (BCB "Dívida Bruta do Governo Geral % PIB") — inspeção real da série específica ainda não feita nesta sessão. | Conferência manual do ponto de partida do simulador contra o número oficial, no `/design` ou no `/build`. |
| Precedente de engine determinístico no repo | Não — primeira vez. | `/design` precisa desenhar do zero a estrutura de módulo (sem KB específico de "simulador" no projeto ainda). |

---

## 5. Abordagens exploradas

### Abordagem A — Fatia combinada: ingestão de PIB real + engine DebtLab + Monte Carlo, persistência em BigQuery ⭐ Escolhida
- **O quê:** 1 conector novo de PIB (RAW→Bronze→Silver→Gold, mesmo padrão de `fiscal_uniao.py`/`inss_*.py`), 1 engine Python determinístico (`dívida_t = dívida_(t-1)×(1+juros) − primário_t`, dividido pelo PIB do ano), 1 camada Monte Carlo por cima (amostragem normal, N iterações, P10/P50/P90), cenários/resultados persistidos numa tabela operacional em `br2036_control` (BigQuery).
- **Prós:** entrega dado real de ponta a ponta (nenhum workaround/PIB fabricado); prova o padrão de simulador completo (determinístico + probabilístico) de uma vez; zero infra nova (reusa BigQuery já provisionado).
- **Contras:** escopo bem maior que um "simulador simples" — 3 capacidades novas numa fatia só (ingestão + engine + Monte Carlo); mais superfície de risco/achado real possível no build, como já aconteceu nas fatias anteriores quando o escopo cresceu (ex.: achado crítico do INSS, achado D10 do fiscal).
- **Confiança:** 0.75 — o padrão de ingestão é bem provado (3x); o engine determinístico e o Monte Carlo são território novo para o projeto, incerteza técnica real (não simulada) sobre a estrutura de módulo ideal, only resolvida de verdade no `/design`.

### Abordagem B — V1 simplificado: só dívida em R$ absoluto, sem PIB, sem Monte Carlo
- **O quê:** engine determinístico usando só dívida+primário reais, saída em R$ (não razão), premissas de juros como único parâmetro de cenário, sem faixas de incerteza.
- **Por que não escolhida:** usuário rejeitou explicitamente — "incluir tudo que falta para entregar dados reais". A saída em R$ absoluto sem razão PIB seria uma entrega mais fraca que o que o `SPEC-010` pede de verdade.
- **Confiança:** 0.90 (mais simples, menos risco) — mas não é a direção que o usuário quer.

### Abordagem C — Separar em 2 features sequenciais (PIB primeiro, DebtLab depois consumindo o dado pronto)
- **O quê:** 1º ciclo SDD completo só pra ingestão de PIB (fatia de dado pura, mesmo molde das 3 anteriores), 2º ciclo SDD só pro engine+Monte Carlo consumindo o PIB já em Gold.
- **Por que não escolhida:** usuário confirmou explicitamente preferir 1 fatia combinada, provavelmente por causa do prazo do concurso CGU (inscrições fecham 11/09/2026) — 2 ciclos completos (cada um com Brainstorm→Define→Design→Build→Verify→Ship) levaria mais tempo de calendário que 1 ciclo com escopo maior.
- **Confiança:** 0.70 — tecnicamente mais seguro (menor blast radius por PR), mas não é a escolha do usuário.

---

## 6. Itens removidos / adiados (YAGNI)

| Item | Por que fora desta fatia | Vai para |
|---|---|---|
| Approval workflow / publicação oficial de cenário | `PRD-004 §5` já exclui isso do V1 explicitamente; sem RBAC/ABAC ainda (próxima fatia da sequência de 4), não há "quem" aprovaria. | `ADR-019`/`ADR-020`, quando RBAC/ABAC (item 4 da sequência combinada) existir. |
| AlloyDB provisionado | Custo fixo sem approval workflow/checkpoint real que justifique agora; contra o driver de custo do `ADR-002`. | Reavaliar quando agentes/checkpoints (`ADR-021`) virarem reais. |
| Outros simuladores do catálogo (Fiscal `SIM-003`, State Fiscal Twin `SIM-012`, etc.) | Fora de escopo — esta fatia é só o DebtLab. | Fatias futuras de simulador, se o padrão provado aqui funcionar bem. |
| Painel/UI completo na Landing pro simulador | Landing (`LANDING_PAGE_ASTRO`) já shipou; qualquer UI de simulador é aditiva a uma fatia futura de "Policy Lab"/portal, não parte desta entrega de engine+API. | Fatia futura de UI/Policy Lab, se o usuário pedir. |
| PIB trimestral + mensal + todas as variantes do Macro Twin (inflação, juros, câmbio, consumo, investimento, trade, forecast — `STORY-008.02` a `.08`) | Só PIB (`STORY-008.01`) é necessário pra alimentar o DebtLab; as outras variáveis do Macro Twin ficam pra quando tiverem consumidor real. | `EPIC-008`, fatias futuras conforme demanda. |
| Full Monte Carlo Global (`SIM-019`, correlações entre múltiplos simuladores) | Esta fatia aplica Monte Carlo só dentro do DebtLab (2 premissas, sem correlação entre simuladores diferentes) — não é o simulador `SIM-019` completo. | `SIM-019`, quando houver mais de 1 simulador pra correlacionar. |

---

## 7. Requisitos-rascunho (para o `/define`)

- **R1.** Novo conector `ingestion/src/ingestion/connectors/pib_brasil.py` (ou nome equivalente) — ingestão real de PIB (fonte a confirmar no `/design`: BCB SGS ou IBGE), pipeline RAW→Bronze→Silver→Gold, mesmo padrão de contrato/provenance das 3 fatias anteriores.
- **R2.** `gold_pib_brasil` (ou tabela equivalente) com `metric_id` novo, endpoint aditivo reaproveitando o padrão `/v1/metrics/{metric_id}/national` já existente (sem quebrar `main.py`/`bigquery_repo.py`).
- **R3.** Engine determinístico DebtLab (`SPEC-010`) — módulo Python novo, sem dependência de LLM, calcula `dívida_t = dívida_(t-1)×(1+juros) − primário_t`, dividido pelo PIB do ano de referência; parâmetros e versão do modelo persistidos.
- **R4.** Camada Monte Carlo (`SPEC-016`) sobre o engine — cada premissa (juros, primário) recebe média±desvio-padrão, N iterações (valor a definir no `/design`), saída com P10/P25/P50/P75/P90 por ano do horizonte; seed fixável para reprodutibilidade.
- **R5.** Horizonte de projeção: 10 anos.
- **R6.** Persistência de cenários/resultados numa tabela operacional em `br2036_control` (BigQuery) — schema com `scenario_id`, premissas, timestamp, versão do engine, resultados (trajetória determinística + percentis).
- **R7.** Endpoint(s) de API novo(s) para criar cenário e consultar resultado — `POST /v1/simulations/debtlab` (ou equivalente) e `GET /v1/simulations/debtlab/{scenario_id}`, exato contrato a definir no `/design`.
- **R8.** Toda saída do simulador rotulada `SIMULATED` (`ADR-028`) de forma visualmente/estruturalmente distinta de dado observado — sem publicação automática como métrica oficial.
- **R9.** Nenhum caminho de LLM pode substituir o cálculo do engine (`SPEC-010`) — se houver texto explicativo gerado por IA sobre o resultado, ele cita o número do engine, nunca recalcula.
- **R10.** Testes unitários do engine contra a fórmula de dinâmica (casos conhecidos/sintéticos) + conferência manual da razão dívida/PIB do ano mais recente contra a série oficial do BCB, mesmo padrão de verificação manual já usado em `FISCAL_RECEITA_DESPESA`.
- **R11.** `docs/adrs/ADR-059-*.md` (número a confirmar no `/design`) formalizando a decisão de persistir em BigQuery em vez de AlloyDB para o V1, referenciando `ADR-004` sem superá-lo (nota, não substituição).

---

## 8. Decisões autônomas registradas

| Decisão | Motivo |
|---|---|
| Nome da feature: `DEBTLAB_SIMULATOR`, não `MACRO_TWIN_PIB` | O simulador é a entrega central pedida pelo usuário; a ingestão de PIB é meio, não fim — nome reflete o valor de produto, não o detalhe técnico interno. |
| Reaproveitar `SPEC-009-MACRO-TWIN.md` existente para a parte de PIB, em vez de criar um SPEC novo só pra isso | `SPEC-009` já existe e já cobre PIB como uma de suas variáveis — esta fatia realiza só a fatia PIB dele, não precisa de um documento paralelo. |
| BigQuery para persistência de cenários no V1, não AlloyDB | Achado real desta sessão: AlloyDB nunca foi provisionado, contradiria o driver de custo do `ADR-002` sem um approval workflow real que justifique o investimento agora. Decisão confirmada explicitamente pelo usuário. |
| Sem approval workflow novo nesta fatia | `PRD-004 §5` já exclui publicação oficial de cenário do escopo V1 — approval workflow sem RBAC/ABAC (que ainda não existe) não teria "quem" aprovar. |

---

## 9. Questões abertas (resolver no `/define` ou `/design`)

1. **Fonte exata de PIB real** (BCB SGS vs. IBGE Contas Nacionais/SIDRA) e periodicidade (trimestral, mensal acumulado, anual) — descoberta real obrigatória no `/design`, mesmo padrão usado em `FISCAL_RECEITA_DESPESA`, nunca suposição.
2. **Dívida nacional vs. por UF como base do cenário** — `divida_consolidada` hoje é por UF (27 linhas); o `SIM-002` pede uma trajetória (implicitamente nacional, dado que compara com PIB nacional). Precisa decidir: somar as 27 UFs, ou já existe/deveria existir um agregado nacional de dívida bruta?
3. **N de iterações do Monte Carlo** — trade-off custo computacional/tempo de resposta da API vs. precisão dos percentis; valor concreto (ex.: 1.000, 10.000) fica pro `/design`.
4. **Contrato exato do(s) endpoint(s) de simulação** — síncrono (cliente espera o resultado) ou assíncrono (job + polling, dado que Monte Carlo com N iterações pode não ser instantâneo)? `ADR-025` (SSE para progresso de agente) pode ser relevante aqui mesmo sem agente — avaliar no `/design`.
5. **Schema da tabela operacional em `br2036_control`** — nome exato, particionamento (por `scenario_id`? por `created_at`?), retenção (cenários de teste vs. reais).

---

## 10. Domínios de KB para a Fase Define

- **PRDs:** `PRD-004` (Fiscal & DebtLab, escopo V1 já lista "simulador DebtLab" e exclui publicação oficial).
- **SPECs:** `SPEC-010` (DebtLab), `SPEC-016` (Monte Carlo), `SPEC-009` (Macro Twin, parte PIB), `SPEC-004` (camadas RAW→Gold, pro conector novo), `SPEC-007` (Provenance).
- **ADRs:** `ADR-013` (núcleo determinístico/borda probabilística), `ADR-042` (simuladores fora do LLM), `ADR-028` (observado/estimado/simulado), `ADR-016` (Monte Carlo/percentis), `ADR-004` (AlloyDB — referenciado, não superado), `ADR-002` (serverless-first — motivo de não provisionar AlloyDB agora), `ADR-012` (LLM nunca computa métrica oficial).
- **Riscos:** `docs/risks/RISK-REGISTER.md`, `RISK-CONTROL-TEST-MATRIX.md` — checar controles já mapeados para simuladores/Monte Carlo (provavelmente ainda sem teste real, primeira vez que a capability existe).
- **Backlog:** `EPIC-008` (Macro Twin, story PIB), `EPIC-009` (Fiscal & DebtLab, stories juros/dívida).
- **Precedente direto:** `ingestion/src/ingestion/connectors/fiscal_uniao.py` + `pipeline_wide_series.py` (padrão de ingestão de série ampla mais recente), `ingestion/src/ingestion/contract.py`/`provenance.py`/`bigquery_io.py` (infra de pipeline reaproveitável), `api/src/api/main.py`/`bigquery_repo.py` (padrão de endpoint `/national` a estender).

---

## 11. Quality gate (Fase 0)

- [x] Mínimo de 3 perguntas de discovery feitas e respondidas (8 feitas)
- [x] Pergunta de amostras feita — dado real de dívida/primário confirmado disponível; PIB confirmado como gap real, não suposto
- [x] Pelo menos 2 abordagens exploradas com trade-offs (A, B, C)
- [x] Usuário confirmou explicitamente a abordagem escolhida (A) em múltiplos checkpoints
- [x] YAGNI aplicado — seção de itens removidos preenchida (6 itens), mesmo com o escopo geral tendo crescido por pedido do usuário
- [x] Mínimo de 2 validações incrementais concluídas (checkpoint de escopo combinado; checkpoint de desenho consolidado com horizonte/persistência)
- [x] Domínios de KB identificados para o Define
- [x] Requisitos-rascunho prontos para o `/define` (R1–R11)

---

## 12. Handoff

Pronto para `/define .claude/sdd/features/BRAINSTORM_DEBTLAB_SIMULATOR.md`.
