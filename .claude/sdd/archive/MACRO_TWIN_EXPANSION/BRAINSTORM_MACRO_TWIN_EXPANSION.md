# BRAINSTORM — MACRO_TWIN_EXPANSION

- **Feature:** MACRO_TWIN_EXPANSION
- **Status:** ✅ Shipped

- **Fase:** 0 (Brainstorm)
- **Criado:** 2026-09-08
- **Idioma:** PT-BR (alinhado a `docs/discovery/`)
- **Próximo passo:** `/define .claude/sdd/features/BRAINSTORM_MACRO_TWIN_EXPANSION.md`

> Nota: assets do plugin SDD ausentes — documento segue a lista de seções do skill
> `sdd-brainstorm`, mesmo padrão dos brainstorms anteriores.

---

## 1. Ideia

Quarta fatia de dados do projeto (item 2 da sequência de 4 já combinada com o usuário após o
`DEBTLAB_SIMULATOR`: simulador → **fatia de dados #4** → RAG básico → RBAC/ABAC + portal
autenticado). Continua o `EPIC-008 — Macro Twin` (`PRD-003`/`SPEC-009`): PIB (`STORY-008.01`) já
foi ingerido como parte do `DEBTLAB_SIMULATOR`; esta fatia adiciona 3 séries reais que faltam —
**inflação (IPCA)**, **juros (SELIC)** e **câmbio (USD/BRL)** — todas confirmadas disponíveis na
mesma API pública do BCB SGS já integrada, mesmo grão mensal do PIB.

**Escolha entre 2 candidatos, decidida pelo usuário:** continuar o Macro Twin (reaproveita 100% do
padrão de conector/pipeline já provado 2x no `DEBTLAB_SIMULATOR`) em vez de começar
`Trabalho & Renda` (`EPIC-011`, CAGED/RAIS — domínio totalmente novo, sem PRD/SPEC, exigiria
descoberta real do zero). Risco técnico baixo, alto reaproveitamento de infraestrutura.

**Escopo cresceu por decisão do usuário:** além da ingestão pura, esta fatia conecta o dado novo
de volta ao `DEBTLAB_SIMULATOR` — um novo endpoint de leitura sugere premissas de cenário
(`juros`/`crescimento`) derivadas de médias móveis reais (SELIC, crescimento do PIB), sem alterar
o contrato do `POST /v1/simulations/debtlab` já shipado.

---

## 2. Contexto técnico

| Aspecto | Observação |
|---|---|
| **3 séries reais confirmadas por chamada direta à API do BCB nesta sessão** | IPCA (série 433, "Variação mensal", valores recentes 0,07–0,58%/mês); SELIC acumulada no mês (série 4390, não a 432 que é a meta diária do Copom — grão errado para este caso, 4390 tem o mesmo grão mensal do PIB, valores recentes 0,21–1,22%/mês); Câmbio USD/BRL médio de período mensal (série 3695, não a série 1 que é diária, valores recentes R$5,08–5,18). |
| **Padrão de conector/pipeline já provado 2x** | `ingestion/src/ingestion/connectors/bcb_sgs.py::BcbSgsConnector` — genérico, parametrizado por `series_code`/`metric_id`, já usado para PIB e Dívida Bruta do Governo Geral no `DEBTLAB_SIMULATOR`. Reaproveitado como está, sem mudança de código no conector. |
| **Achado real do `DEBTLAB_SIMULATOR` que já resolve a estrutura desta fatia** | Cada série BCB precisa do seu próprio conjunto Bronze/Silver/Gold — combinar múltiplas séries num "1 resource" fabricaria provenance errada ou arriscaria colisão de `CREATE OR REPLACE` (Achado #1 do `BUILD_REPORT_DEBTLAB_SIMULATOR`). Esta fatia já nasce sabendo disso — 3 conjuntos de tabelas independentes, não um pipeline combinado. |
| **`SPEC-009` já cobre este escopo, com uma parte fora de escopo aqui** | "Expose canonical series for GDP, inflation, interest, FX, consumption, investment, credit and trade" — esta fatia cobre inflation/interest/FX; consumption/investment/credit/trade ficam para fatias futuras, conforme demanda. `SPEC-009` também exige um "Forecast endpoint" com `model_id`/`version`/intervalo — **fora de escopo aqui**: essa é a entrega do `EPIC-020 — Forecast Platform`, uma fatia própria futura, não parte desta. |
| **Conexão de volta ao DebtLab** | `POST /v1/simulations/debtlab` (já shipado) exige `juros_nominal`/`crescimento_nominal_pib`/`primario_pct_pib` como input explícito do usuário, sem sugestão. Com IPCA/SELIC reais agora disponíveis, um endpoint novo pode sugerir médias/desvios reais — mas sem mudar o contrato do `POST` já testado e em produção (decisão do usuário: endpoint `GET` separado, não default automático). |
| **Câmbio não entra na fórmula do DebtLab** | A equação de `debtlab.py::project_deterministic()` usa só `juros`, `crescimento`, `primário` — câmbio fica como dado do Macro Twin em si (`/v1/metrics/cambio_usd_brl/national`), sem consumidor no simulador ainda. |
| **Numeração livre** | Próximo ADR: `ADR-060` (depois de `ADR-059`), se o `/design` decidir que uma decisão nova precisa de formalização (ex.: o padrão de "sugestão derivada de média móvel real, nunca fabricada"). Nenhum SPEC novo necessário — `SPEC-009` já cobre. |

---

## 3. Discovery

| # | Pergunta | Resposta | Impacto no desenho |
|---|---|---|---|
| 1 | Qual direção priorizar: continuar Macro Twin ou começar Trabalho & Renda? | **Macro Twin** — reaproveita o padrão já provado, risco técnico baixo. | Escopo fixado em `EPIC-008`/`SPEC-009`, não `EPIC-011`. |
| 2 | Quantas séries incluir nesta fatia: 1 por vez ou as 3 juntas? | **As 3 juntas** (IPCA + SELIC + câmbio) — o padrão já está provado 2x, replicar 3x de uma vez tem risco baixo e evita 3 ciclos SDD separados para algo repetitivo. | Manifesto de arquivos triplica a estrutura do `pib_mensal`/`divida_bruta_pib` (3 conectores, 3 contratos, 3 pares Silver/Gold, 3 configs). |
| 3 | Essas séries têm consumidor real imediato ou é só ingestão? | **Consumidor real** — conectar ao `DebtLab`. | Escopo ganha um endpoint novo de leitura, não só ingestão pura. |
| 4 | Como conectar ao DebtLab sem quebrar o `POST` já shipado? | **Endpoint `GET` novo separado** (`/v1/simulations/debtlab/suggested-assumptions`) — o `POST` continua exigindo os campos explicitamente, o chamador decide se usa a sugestão. | Não migra nem versiona o contrato do `POST`; endpoint aditivo, mesmo padrão de aditividade já usado em toda a API do projeto. |

---

## 4. Inventário de amostras

| Tipo | Disponível? | Uso previsto |
|---|---|---|
| IPCA real (série 433) | Sim — confirmado por chamada direta, 3 pontos recentes reais. | Base da ingestão `ipca_mensal`. |
| SELIC acumulada mensal real (série 4390) | Sim — confirmado por chamada direta; série 432 (meta diária) descartada por grão incompatível. | Base da ingestão `selic_mensal` + insumo do endpoint de sugestão. |
| Câmbio USD/BRL mensal real (série 3695) | Sim — confirmado por chamada direta; série 1 (diária) descartada por grão incompatível. | Base da ingestão `cambio_usd_brl`. |
| PIB real já em Gold | Sim — `gold_pib_mensal`, 438 linhas (`DEBTLAB_SIMULATOR`). | Insumo do endpoint de sugestão (crescimento real mês a mês). |
| Precedente de conector/pipeline | Sim — `BcbSgsConnector` + `pipeline_wide_series.py`, provado 2x. | Reaproveitado sem mudança de código nesta fatia (só novas instâncias/configs). |

---

## 5. Abordagens exploradas

### Abordagem A — 3 séries novas (IPCA/SELIC/câmbio), cada uma com seu próprio conjunto de tabelas, + endpoint `GET` de sugestão para o DebtLab ⭐ Escolhida

- **O quê:** 3 instâncias de `BcbSgsConnector` (séries 433/4390/3695), 3 pares Bronze/Silver/Gold
  independentes (mesmo molde de `pib_mensal`/`divida_bruta_pib`), servidos via
  `/v1/metrics/{metric_id}/national` genérico (zero código novo de leitura). Endpoint novo
  `GET /v1/simulations/debtlab/suggested-assumptions` computa média±desvio-padrão móvel de 12
  meses de SELIC e crescimento do PIB via SQL sobre o Gold real, sem fabricar nada.
- **Prós:** reaproveita 100% do padrão já provado; conecta o dado novo a um consumidor real
  (DebtLab) sem quebrar o contrato já shipado; expande a cobertura do Macro Twin de forma
  incremental e verificável.
- **Contras:** 3x o número de arquivos repetitivos (contratos/SQL/config quase idênticos, só
  série/nome mudando) — aceitável dado o precedente já estabelecido de "SQL near-duplicado por
  métrica, não templating cross-metric" (mesma filosofia do INSS).
- **Confiança:** 0.9 — padrão já provado 2x, fontes já confirmadas reais, único território
  genuinamente novo é o endpoint de sugestão (cálculo de janela móvel via SQL, não difícil).

### Abordagem B — Só ingestão, sem conectar ao DebtLab

- **O quê:** as 3 séries entram em Gold, servidas via `/national`, sem nenhum endpoint novo de
  sugestão.
- **Por que não escolhida:** usuário pediu explicitamente para conectar ao DebtLab — deixar as
  séries "soltas" sem consumidor real deixaria valor na mesa que o próprio usuário já identificou.
- **Confiança:** 0.95 (mais simples) — mas não é o que o usuário quer.

### Abordagem C — Trabalho & Renda (CAGED/RAIS) em vez de continuar o Macro Twin

- **O quê:** nova fatia de dados sobre emprego formal, fonte a descobrir do zero (provavelmente
  Novo CAGED/Ministério do Trabalho, sem PRD/SPEC ainda).
- **Por que não escolhida:** usuário preferiu o Macro Twin — menor risco técnico, reaproveita
  infraestrutura já provada; Trabalho & Renda fica pro backlog, sem prioridade fechada ainda.
- **Confiança:** 0.5 (fonte não investigada, mais incerteza técnica genuína).

---

## 6. Itens removidos / adiados (YAGNI)

| Item | Por que fora desta fatia | Vai para |
|---|---|---|
| Consumo, investimento, crédito, trade (resto do `SPEC-009`) | Só inflação/juros/câmbio são as 3 séries reais já confirmadas e com consumidor identificado nesta sessão; as demais exigiriam nova descoberta real de fonte/série. | `EPIC-008`, fatias futuras conforme demanda. |
| Forecast endpoint (`SPEC-009`, `model_id`/`version`/intervalo) | É a entrega do `EPIC-020 — Forecast Platform`, um domínio técnico próprio (modelo champion/challenger, `ADR-014`) — misturar aqui seria escopo muito maior do que "mais 3 séries + 1 endpoint de sugestão". | `EPIC-020`, fatia própria futura. |
| Default automático no `POST /v1/simulations/debtlab` | Decisão explícita do usuário — mudar o contrato já shipado (tornar campos opcionais com preenchimento automático) é mais arriscado e menos transparente que um endpoint `GET` separado que o chamador consulta e decide usar. | Não previsto — a decisão foi definitiva, não um adiamento. |
| Câmbio como insumo do DebtLab | A fórmula de `debtlab.py` não tem termo de câmbio — usá-lo exigiria mudar a equação em si, fora de escopo. | Reavaliar se um simulador futuro (ex.: `SIM-018 — Choques Externos`) precisar dele. |
| Trabalho & Renda (CAGED/RAIS) | Escolhido não priorizar nesta rodada (Abordagem C). | Backlog, `EPIC-011`, sem PRD/SPEC ainda — precisa de `/brainstorm` próprio no futuro. |

---

## 7. Requisitos-rascunho (para o `/define`)

- **R1.** 3 novos conectores (instâncias de `BcbSgsConnector`): `ipca_mensal` (série 433),
  `selic_mensal` (série 4390), `cambio_usd_brl` (série 3695) — mesmo padrão RAW→Bronze→Silver→Gold
  já usado em `pib_mensal`/`divida_bruta_pib`.
- **R2.** 3 contratos novos (`ingestion/contracts/{ipca_mensal,selic_mensal,cambio_usd_brl}.yaml`),
  3 pares Silver/Gold, 3 configs `WideSeriesConfig`.
- **R3.** `config.metric_tables` (API) ganha as 3 entradas novas — servidas via
  `/v1/metrics/{metric_id}/national` sem código novo de leitura.
- **R4.** Endpoint novo `GET /v1/simulations/debtlab/suggested-assumptions` — calcula média e
  desvio-padrão móvel dos últimos 12 meses reais de SELIC (`juros_nominal` sugerido) e de
  crescimento mês-a-mês do PIB real (`crescimento_nominal_pib` sugerido), via SQL sobre Gold, sem
  nenhum valor fabricado. Response cita explicitamente a fonte/período de cada sugestão.
- **R5.** `POST /v1/simulations/debtlab` **não muda** — contrato já shipado permanece
  exatamente como está.
- **R6.** Testes unitários dos 3 conectores (mesmo padrão de `test_bcb_sgs_connector.py`, já
  genérico o bastante para reaproveitar) + testes do endpoint de sugestão (média/desvio corretos
  contra dado sintético conhecido).
- **R7.** Integration test real contra `brasil2036-dev` para pelo menos 1 das 3 séries novas
  (mesmo padrão de `test_pipeline_bcb_macro_bigquery.py`).
- **R8.** Backfill real das 3 séries contra `brasil2036-dev`, confirmado antes do `/ship`.

---

## 8. Decisões autônomas registradas

| Decisão | Motivo |
|---|---|
| Nome da feature: `MACRO_TWIN_EXPANSION` | Reflete que é uma continuação do `EPIC-008` já iniciado (PIB), não uma feature nova isolada. |
| Série 4390 (SELIC acumulada mensal), não 432 (meta diária do Copom) | Grão mensal consistente com PIB/dívida — usar a série diária exigiria agregação adicional sem necessidade real para este caso de uso. |
| Série 3695 (câmbio médio mensal), não 1 (câmbio diário) | Mesmo racional — grão mensal consistente. |
| Endpoint de sugestão calcula sobre janela móvel de 12 meses, não outro período | Padrão comum de "trailing twelve months" em análise macro/fiscal, mesmo horizonte já usado implicitamente nas conferências manuais de fatias anteriores (ex.: jul/2026 vs. mesmo mês anterior). Valor exato revisável no `/design`. |

---

## 9. Questões abertas (resolver no `/design`)

1. **Janela exata do cálculo de sugestão** (12 meses é o ponto de partida; `/design` pode ajustar
   se o dado real tiver menos histórico disponível para alguma série).
2. **Formato exato da resposta do endpoint de sugestão** (estrutura JSON, se inclui os pontos
   brutos usados no cálculo ou só o resultado agregado) — decisão de `/design`.
3. **Se `ADR-060` é necessário** — formalizar o padrão "sugestão derivada de janela móvel real,
   nunca fabricada, nunca aplicada automaticamente" pode merecer um ADR próprio, ou pode ser
   coberto por uma nota no `SPEC-009`/`ADR-059` existente. Decisão de `/design`.

---

## 10. Domínios de KB para a Fase Define

- **PRDs/SPECs:** `PRD-003` (Macro Economic Twin), `SPEC-009` (Macro Twin), `SPEC-010` (DebtLab,
  para o endpoint de sugestão não violar o contrato já shipado).
- **ADRs:** `ADR-012` (LLM nunca computa métrica oficial — a sugestão é cálculo determinístico
  SQL, não LLM, mas vale reafirmar o princípio), `ADR-028` (observado/estimado/simulado), `ADR-059`
  (precedente direto: mesmo padrão de conector/pipeline, mesma decisão de não usar AlloyDB).
- **Backlog:** `EPIC-008` (Macro Twin, stories `.02` inflação, `.03` juros, `.04` câmbio).
- **Precedente direto:** `ingestion/src/ingestion/connectors/bcb_sgs.py`,
  `ingestion/{contracts,sql,config}/{pib_mensal,divida_bruta_pib}.*` (molde a replicar),
  `api/src/api/{main,bigquery_repo,config}.py` (padrão de endpoint aditivo).

---

## 11. Quality gate (Fase 0)

- [x] Mínimo de 3 perguntas de discovery feitas e respondidas (4 feitas)
- [x] Pergunta de amostras feita — 3 séries confirmadas reais por chamada direta à API nesta sessão
- [x] Pelo menos 2 abordagens exploradas com trade-offs (A, B, C)
- [x] Usuário confirmou explicitamente a abordagem escolhida (A) em múltiplos checkpoints
- [x] YAGNI aplicado — seção de itens removidos preenchida (5 itens)
- [x] Mínimo de 2 validações incrementais concluídas (checkpoint de escopo das variáveis;
  checkpoint de como conectar ao DebtLab; checkpoint final consolidado)
- [x] Domínios de KB identificados para o Define
- [x] Requisitos-rascunho prontos para o `/define` (R1–R8)

---

## 12. Handoff

Pronto para `/define .claude/sdd/features/BRAINSTORM_MACRO_TWIN_EXPANSION.md`.
