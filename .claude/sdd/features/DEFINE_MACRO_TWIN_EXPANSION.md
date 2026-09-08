# DEFINE — MACRO_TWIN_EXPANSION

## Metadados

- **Feature:** MACRO_TWIN_EXPANSION
- **Status:** ✅ Complete (Built)
- **Fase:** 1 (Define)
- **Entrada:** `.claude/sdd/features/BRAINSTORM_MACRO_TWIN_EXPANSION.md` (Ready for Define)
- **Criado:** 2026-09-08
- **Idioma:** PT-BR
- **Clarity score:** 13/15 (HIGH)
- **Branch:** a criar — `feature/macro-twin-expansion`
- **Próximo passo:** `/design .claude/sdd/features/DEFINE_MACRO_TWIN_EXPANSION.md`

> Nota: assets do plugin SDD ausentes — documento segue a lista de seções obrigatórias do skill
> `sdd-define`, mesmo padrão das fatias anteriores.

---

## 1. Problem statement

O `EPIC-008 — Macro Twin` (`PRD-003`/`SPEC-009`) ficou parcialmente iniciado no
`DEBTLAB_SIMULATOR` — só PIB (`STORY-008.01`) foi ingerido, como meio para o simulador, não como
entrega do Macro Twin em si. Faltam inflação, juros e câmbio: 3 séries reais já confirmadas
disponíveis na mesma API do BCB SGS já integrada, com o mesmo grão mensal do PIB. Além disso, o
`DebtLab` shipado exige que o usuário digite premissas de cenário (`juros`/`crescimento`) sem
nenhuma referência a dado real — com SELIC e crescimento do PIB reais agora disponíveis, essas
premissas podem ser informadas por sugestões reais, não só por chute do usuário.

---

## 2. Target users

| Persona | Descrição | Pain point |
|---|---|---|
| **Analista fiscal / macro** (primária, `PRD-003`) | Quer ver indicadores macro reais e criar cenários de DebtLab informados por dado real | Hoje só vê PIB e dívida; premissas do simulador são digitadas sem nenhuma referência |
| **Avaliador do concurso CGU** (secundária) | Julga a cobertura de dados abertos e a sofisticação analítica | Mais séries reais + conexão entre elas (dado alimentando simulador) demonstra integração real, não só catálogo de números soltos |

---

## 3. Goals (MoSCoW)

### MUST

- **G1.** Ingerir IPCA real (BCB SGS série 433, "Variação mensal") via pipeline
  RAW→Bronze→Silver→Gold, mesmo padrão das fatias anteriores.
- **G2.** Ingerir SELIC acumulada mensal real (série 4390 — não a 432, que é a meta diária do
  Copom, grão incompatível).
- **G3.** Ingerir câmbio USD/BRL médio mensal real (série 3695 — não a série 1, diária).
- **G4.** Cada série mantém seu próprio conector/Bronze/Silver/Gold independente — não um
  pipeline combinado (achado real do `DEBTLAB_SIMULATOR`: evita provenance errada e colisão de
  `CREATE OR REPLACE`).
- **G5.** As 3 séries servidas via `/v1/metrics/{metric_id}/national` já existente, sem código
  novo de leitura.
- **G6.** Endpoint novo `GET /v1/simulations/debtlab/suggested-assumptions` — sugere
  `juros_nominal` (a partir de SELIC real) e `crescimento_nominal_pib` (a partir do PIB real),
  média±desvio-padrão de uma janela móvel real, nunca fabricado, com fonte/período citados na
  resposta.
- **G7.** `POST /v1/simulations/debtlab` **não muda** — contrato já shipado permanece idêntico.
- **G8.** Testes unitários dos 3 conectores + do endpoint de sugestão + ≥1 integration test real
  contra `brasil2036-dev`.

### SHOULD

- **G9.** Backfill real das 3 séries contra `brasil2036-dev`, confirmado antes do `/ship`.
- **G10.** ADR novo formalizando o padrão "sugestão derivada de janela móvel real, nunca
  fabricada, nunca aplicada automaticamente" — se o `/design` decidir que merece formalização
  própria em vez de nota em `ADR-059`/`SPEC-009`.

### COULD

- **G11.** Câmbio como insumo de um simulador futuro (ex.: `SIM-018 — Choques Externos`) — não
  nesta fatia, a fórmula do `DebtLab` não tem termo de câmbio.

---

## 4. Success criteria (mensuráveis)

| # | Critério | Medição |
|---|---|---|
| S1 | 3 séries reais carregadas e servidas | Endpoints `/v1/metrics/{ipca_mensal,selic_mensal,cambio_usd_brl}/national` retornando dado real. |
| S2 | Sugestão do DebtLab é real, não fabricada | Resposta do endpoint novo cita fonte/período; valores conferem contra a série BCB real. |
| S3 | Zero regressão no `POST` já shipado | Todos os testes existentes de `test_debtlab_endpoint.py` continuam passando sem alteração. |
| S4 | Testes cobrindo os 3 conectores + endpoint de sugestão | Unit tests + ≥1 integration test real PASS. |
| S5 | Backfill real confirmado | 3 séries com dado real em `brasil2036-dev`, confirmado antes do `/ship`. |
| S6 | `/verify-spec` PASS | Verificação independente (sessão nova, read-only) = OVERALL PASS. |
| S7 | `ci-gate` verde | Todo PR desta fatia passa pelo `ci-gate` sem gate enfraquecido. |

---

## 5. Acceptance tests

- **AT1 — IPCA real ingerido e servido.** *Given* o pipeline rodado contra `brasil2036-dev`,
  *When* consulto `/v1/metrics/ipca_mensal/national`, *Then* recebo um valor real, com provenance
  citando a série 433 do BCB.
- **AT2 — SELIC real ingerida e servida.** Mesma estrutura, série 4390.
- **AT3 — câmbio real ingerido e servido.** Mesma estrutura, série 3695.
- **AT4 — cada série tem seu próprio conjunto de tabelas.** *Given* as 3 ingestões rodadas,
  *When* inspeciono `dataset_registry`/`metric_provenance`, *Then* cada `metric_id` cita a URL
  correta da sua própria série BCB, nenhuma compartilhada incorretamente.
- **AT5 — endpoint de sugestão retorna valor real.** *Given* SELIC e PIB reais já carregados,
  *When* chamo `GET /v1/simulations/debtlab/suggested-assumptions`, *Then* recebo
  `juros_nominal`/`crescimento_nominal_pib` sugeridos com média/desvio calculados sobre dado real,
  fonte/período citados, nenhum valor inventado.
- **AT6 — `POST /v1/simulations/debtlab` inalterado.** *Given* o mesmo request usado nos testes já
  shipados, *When* chamo o endpoint, *Then* o comportamento é idêntico ao de antes desta fatia.
- **AT7 — câmbio não afeta o cálculo do DebtLab.** *Given* a fórmula do engine, *When* inspeciono
  o código, *Then* nenhuma referência a câmbio existe em `debtlab.py`.
- **AT8 — ritual de CI completo.** *Given* qualquer PR desta fatia, *When* o CI roda, *Then*
  `ci-gate` resolve e bloqueia merge se qualquer gate falhar.

---

## 6. Out of scope

| Item | Motivo | Destino |
|---|---|---|
| Consumo, investimento, crédito, trade (resto do `SPEC-009`) | Só as 3 séries já confirmadas nesta sessão têm consumidor identificado; as demais exigiriam nova descoberta real. | `EPIC-008`, fatias futuras. |
| Forecast endpoint (`SPEC-009`, `model_id`/`version`/intervalo) | Entrega do `EPIC-020 — Forecast Platform`, domínio técnico próprio (`ADR-014`). | `EPIC-020`, fatia própria futura. |
| Default automático no `POST /v1/simulations/debtlab` | Decisão explícita do usuário — endpoint `GET` separado é mais transparente que mudar o contrato já shipado. | Não previsto. |
| Câmbio como insumo do DebtLab | Fórmula não tem termo de câmbio. | Reavaliar com um simulador futuro que precise dele. |
| Trabalho & Renda (CAGED/RAIS) | Não priorizado nesta rodada. | Backlog, `EPIC-011`, `/brainstorm` próprio no futuro. |

---

## 7. Constraints

- **C1.** Cada série mantém conjunto de tabelas Bronze/Silver/Gold próprio, não combinado
  (`§0` do Brainstorm, achado real do `DEBTLAB_SIMULATOR`).
- **C2.** `POST /v1/simulations/debtlab` não pode ter seu contrato alterado nesta fatia.
- **C3.** Toda sugestão do endpoint novo é calculada sobre dado real (SQL determinístico), nunca
  fabricada, nunca gerada por LLM (`ADR-012`).
- **C4.** Todo merge em `main` é via PR (branch protection).
- **C5.** Reusa `ci-gate`/gates já existentes, sem enfraquecer.

---

## 8. Assumptions / risk register

| ID | Afirmação | Impacto se falsa | Validada |
|---|---|---|---|
| A1 | As 3 séries têm ≥12 meses de histórico real disponível na API do BCB para calcular média/desvio de uma janela móvel | Pode exigir uma janela menor ou um cálculo alternativo — mais escopo de `/design` | ☐ |
| A2 | Formato exato da resposta do endpoint de sugestão (estrutura JSON, se inclui pontos brutos ou só agregado) | Decisão de `/design`, sem impacto no escopo geral se mudar | ☐ |
| A3 | O padrão "sugestão derivada de janela móvel real" precisa de um ADR novo (`ADR-060`) ou cabe como nota em `ADR-059`/`SPEC-009` | Decisão de `/design`; não muda a implementação, só a documentação | ☐ |

---

## 9. Technical context

| Aspecto | Definição |
|---|---|
| **Onde vive** | `ingestion/src/ingestion/connectors/bcb_sgs.py` (reaproveitado, sem mudança), `ingestion/{contracts,sql,config}/` (+3 séries novas), `api/src/api/{main,bigquery_repo,config}.py` (+1 endpoint de sugestão), `docs/adrs/` (+1 ADR, se o `/design` decidir). |
| **Impacto IaC** | Nenhum esperado — reusa `br2036_gold`/`br2036_control` já provisionados. |
| **Domínios de KB** | `PRD-003`, `SPEC-009`, `SPEC-010` (contrato do DebtLab a preservar); `ADR-012`, `ADR-028`, `ADR-059` (precedente direto). |

---

## 10. Clarity score breakdown

| Elemento | Nota | Máx | Observação |
|---|---|---|---|
| Problem | 3 | 3 | Gap concreto: Macro Twin incompleto + premissas do DebtLab sem referência real, ambos resolvidos pela mesma fatia. |
| Users | 2 | 3 | Persona primária bem definida; avaliador CGU é papel, não pessoa — mesmo padrão conservador das fatias anteriores. |
| Goals | 3 | 3 | 8 MUST, 2 SHOULD, 1 COULD; todos mensuráveis e rastreáveis ao Brainstorm. |
| Success | 3 | 3 | S1–S7 com critérios verificáveis. |
| Scope | 2 | 3 | Out-of-scope bem povoado (5 itens), mas 3 assumptions reais (A1–A3) ainda não validadas — janela de histórico e formato de resposta carregam incerteza técnica genuína, só resolvida no `/design`. |
| **Total** | **13** | **15** | **HIGH — prosseguir para `/design`.** |

---

## 11. Open questions

| ID | Questão | Resolver em |
|---|---|---|
| OQ1 | Janela exata do cálculo de sugestão (12 meses é o ponto de partida) | `/design` |
| OQ2 | Formato exato da resposta do endpoint de sugestão | `/design` |
| OQ3 | Se `ADR-060` é necessário ou uma nota em `ADR-059`/`SPEC-009` basta | `/design` |
| OQ4 | Confirmar histórico suficiente das 3 séries reais para a janela escolhida | `/design`, descoberta real |

---

## 12. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-08 | 1.0 | Criação a partir de `BRAINSTORM_MACRO_TWIN_EXPANSION.md`. Clarity 13/15. Status → Ready for Design. | /define (Claude Sonnet 5) |
