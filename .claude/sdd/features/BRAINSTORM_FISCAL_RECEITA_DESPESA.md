# BRAINSTORM — FISCAL_RECEITA_DESPESA

- **Feature:** FISCAL_RECEITA_DESPESA
- **Status:** ✅ Complete (Defined)
- **Fase:** 0 (Brainstorm)
- **Criado:** 2026-09-05
- **Idioma:** PT-BR (alinhado a `docs/discovery/`)
- **Próximo passo:** `/define .claude/sdd/features/BRAINSTORM_FISCAL_RECEITA_DESPESA.md`

> Nota: assets do plugin SDD ausentes (`kb/_index.yaml`, `BRAINSTORM_TEMPLATE.md` não instalados) —
> documento segue a lista de seções do skill `sdd-brainstorm`, mesmo padrão de
> `BRAINSTORM_MVP_WALKING_SKELETON.md` e `BRAINSTORM_INSS_BENEFICIOS.md`.

---

## 1. Ideia

**Fatia #3**: levar o padrão de pipeline provado 2x (`MVP_WALKING_SKELETON` — dívida — e
`INSS_BENEFICIOS` — 3 datasets, formatos/grão novos) para o domínio **Fiscal & DebtLab (M02)**
— `EPIC-009`, `PRD-004` — ingerindo **receita e despesa** (`STORY-009.01`/`STORY-009.02`), com
**resultado primário** (`STORY-009.03` — métrica derivada, sem ingestão nova) como stretch dentro
da mesma fatia.

Diferente das duas fatias anteriores, aqui **a fonte real ainda não foi escolhida**: o usuário
decidiu explicitamente deixar essa decisão para a tarefa 1 do `/design` (mesmo espírito do que já
foi feito para o formato do ZIP de Emitidos e o dicionário de espécies do INSS) — não inventar
qual API/arquivo específico existe antes de olhar de verdade. `docs/sources/SOURCE-INDEX.csv`
lista **Tesouro Nacional** (linha 10, P0, módulo "Fiscal/dívida") e **SICONFI** (linha 11, P0,
módulo "Estados/municípios") como as duas organizações candidatas, mas nenhuma das duas tem um
recurso específico de receita/despesa catalogado ainda — só a home da organização. A descoberta
real (URL do recurso, schema, granularidade territorial e temporal disponível) é trabalho de
`/design`, não deste documento.

---

## 2. Contexto técnico

| Aspecto | Observação |
|---|---|
| Padrão a reaproveitar | `ingestion/src/ingestion/connectors/base.py` (interface), `divida_estados.py`/`inss_*.py` (implementações de referência para CSV/ZIP/XLSX), `pipeline_incremental.py` + `backfill.py` (escrita por partição, backfill resumível — já generalizados, não específicos de INSS), `bronze.py::load_partition()` (DELETE+INSERT escopado), `registry.py`/`provenance.py` (já corrigidos para MERGE/DELETE+INSERT em tabelas compartilhadas — risco já eliminado, não precisa ser redescoberto). |
| **Achado técnico positivo (diferente do que aconteceu no INSS)** | `api/src/api/main.py::get_national_metric` + `Config.metric_tables` **já são genéricos por `metric_id`** desde o PR2 do INSS — não hardcoded a um domínio. Para expor receita/despesa no agregado nacional, o trabalho de API pode ser **de fato quase grátis**: acrescentar `fiscal_receita`/`fiscal_despesa` em `Config.metric_tables` e apontar para as novas tabelas Gold, sem tocar `main.py`/`bigquery_repo.py`. **Ressalva:** isso vale só para "valor mais recente por metric_id" — o **resultado primário** (receita − despesa) não tem esse atalho pronto; precisa de uma decisão de `/design` (calcular no cliente/web a partir de 2 chamadas, ou uma 3ª rota/endpoint dedicado). |
| Domínios de KB relevantes | `PRD-004` (Fiscal & DebtLab), `SPEC-003/004/005/007` (Connectors/RAW-Bronze-Silver-Gold/Contracts/Provenance — mesmos das 2 fatias anteriores), `SPEC-026` (API/OpenAPI), `SPEC-031`/`ADR-054` (CI gates — já realizado, mais um dataset passa pelo `integration` sem infra nova), `ADR-055` (padrão de escrita por partição/backfill, formalizado no INSS — reaproveitar, não redecidir). `ADR-011` (chave territorial IBGE, se a fonte for por UF), `ADR-012` (LLM nunca computa métrica oficial), `ADR-028` (observed/estimated/simulated). |
| Matriz de risco | `docs/risks/RISK-CONTROL-TEST-MATRIX.md` — leitura obrigatória no `/define`. Risco principal aqui não é dado pessoal-adjacente (como no INSS), e sim **volatilidade/instabilidade de schema da fonte** — já um padrão observado 1x real (Emitidos do INSS mudou de schema 4+ vezes) — vale entrar como assumption a validar cedo na descoberta. |
| Fonte de dados | `docs/sources/SOURCE-INDEX.csv` linhas 10–11: **Tesouro Nacional** (API/files) e **SICONFI** (API/files) — ambas P0, nenhuma com recurso específico catalogado. Descoberta do recurso real (RREO/RGF da União via Tesouro Transparente, ou séries do SICONFI por UF) é tarefa 1 do `/design`. |
| Backlog | `EPIC-009 — Fiscal & DebtLab`: `STORY-009.01` (receita), `STORY-009.02` (despesa), `STORY-009.03` (primário) — as 3 cobertas por esta fatia. `STORY-009.04` (juros), `STORY-009.05` (dívida — já `MVP_WALKING_SKELETON`), `STORY-009.06` (debt simulator), `STORY-009.07` (stress) ficam fora. |

---

## 3. Discovery

| # | Pergunta | Resposta | Impacto no desenho |
|---|---|---|---|
| 1 | Fonte/grão: federal (Tesouro/RREO) ou estadual-municipal (SICONFI)? | **Deixar para a descoberta real no `/design`** (mesmo padrão do INSS). | Sem suposição de formato/granularidade territorial nesta fase; tarefa 1 do `/design` decide com evidência real, registrada como decisão inline (D1). |
| 2 | Objetivo desta fatia? | **Todas as 3 opções**: módulo M02 público na Landing, prova do mecanismo contra uma 4ª fonte, e Gold já no grão que o futuro simulador DebtLab (`STORY-009.06`) vai precisar. | Estrutura em PRs de fase (dados → apresentação), mesmo padrão do INSS PR1/PR2 — sem PR dedicado a "insumo simulador" (mesma razão do INSS: YAGNI, sem simulador real para validar). |
| 3 | Granularidade do dado (total agregado vs por categoria)? | **Total agregado** (1 valor de receita e 1 de despesa por período) — decisão registrada por Claude, aceita pelo usuário ("a melhor opção considerando o contexto"). | Evita explodir o schema com categorias/funções/órgãos nesta fatia; mesmo espírito "walking skeleton" da dívida. Quebra por categoria fica para incremento futuro. |
| 4 | Amostras disponíveis? | **Nenhuma ainda.** | Descoberta do recurso real (schema, formato, encoding) é tarefa 1 do `/design`, igual às 2 fatias anteriores. |
| 5 | Estrutura do Gold (2 tabelas separadas vs 1 fundida)? | **2 tabelas Gold separadas** (`gold_fiscal_receita`, `gold_fiscal_despesa`) — decisão registrada por Claude, aceita pelo usuário ("a melhor abordagem, considerando o cenário e contexto"). | Consistente com a decisão já tomada e provada no INSS (C5: não fundir datasets semanticamente distintos — receita soma, despesa subtrai do resultado). |
| 6 | Incluir resultado primário (`STORY-009.03`) nesta fatia? | **Sim, como SHOULD** — métrica derivada (`receita_total − despesa_total`), sem ingestão nova. | Fecha 3 das 7 stories do `EPIC-009` numa fatia só, condicionado a receita e despesa terem o mesmo grão de período (se não tiverem, cai — registrado como assumption). |

---

## 4. Inventário de amostras

| Tipo | Disponível? | Uso previsto |
|---|---|---|
| Arquivos de entrada | Não | Descoberta do recurso real (Tesouro Transparente ou SICONFI — decisão de `/design`) é a tarefa 1, mesmo padrão das 2 fatias anteriores. |
| Exemplo de saída esperada | Não | Construir à mão no `/define`/`/design`: 1 linha Gold alvo por dataset (grão a definir na descoberta) + objeto de provenance, para receita e para despesa. |
| Ground truth | Não | Um valor conhecido de receita e de despesa de um período real serve de âncora de validação, a obter na descoberta do recurso. |
| Código relacionado | Sim — o padrão inteiro provado 2x (`MVP_WALKING_SKELETON`, `INSS_BENEFICIOS`): connector, contrato, Bronze/Silver/Gold, provenance, `pipeline_incremental.py`/`backfill.py`, `/national` endpoint genérico, `ADR-055`. | Template direto; terceira aplicação do mesmo padrão, não greenfield. |

---

## 5. Abordagens exploradas

### Abordagem A — Uma feature, PRs em fases (dados → apresentação), fonte a descobrir no `/design` ⭐ Escolhida
- **O quê:** 1 ciclo SDD (`FISCAL_RECEITA_DESPESA`) com PRs sequenciais, espelhando o padrão já usado 2x:
  - **PR1 — espinha de dados:** descoberta real da fonte (Tesouro Transparente ou SICONFI) → 1-2 conectores sobre `connectors/base.py` → RAW → Bronze → Silver → **2 tabelas Gold separadas** (`gold_fiscal_receita`, `gold_fiscal_despesa`), grão total agregado por período → provenance → 2 contratos de dados.
  - **PR2 — apresentação:** `Config.metric_tables` ganha as 2 entradas novas (reuso quase grátis do endpoint `/national` já genérico); módulo M02 na Landing com receita, despesa e (se o grão bater) resultado primário calculado a partir dos 2; sem valor hard-coded.
- **Prós:** reaproveita 100% do mecanismo já revisado 2x (connector, contrato, `pipeline_incremental`/`backfill`, `ci-gate`/`integration` sem infra nova, `/national` endpoint sem mudança de código); terceira aplicação do padrão reduz o risco de achado crítico novo (já não há tabela compartilhada com bug conhecido).
- **Contras:** ainda existe descoberta real pendente (fonte, schema, granularidade temporal) — DEFINE/DESIGN não podem fixar tudo antes disso; resultado primário depende de receita e despesa caírem no mesmo grão de período, o que só se confirma na prática.
- **Confiança:** 0.85 — padrão comprovado 2x, incluindo reuso genuinamente mais barato da API desta vez; incerteza real só na fonte/schema, não no mecanismo.
- **Por que escolhida:** confirmada pelo usuário em cada decisão de discovery (§3); é a extensão natural do padrão já validado por dois `/verify-spec` PASS consecutivos.

### Abordagem B — 1 tabela Gold fundida `fiscal_execucao` com coluna `tipo=receita|despesa`
- **O quê:** uma única tabela Gold para os dois lados do lançamento fiscal, distinguidos por coluna.
- **Por que não escolhida:** contradiz a decisão já tomada (e provada útil) no INSS de não fundir datasets semanticamente distintos (C5) — receita e despesa entram em lados opostos do resultado primário; misturar cedo arrisca confundir a métrica em queries futuras (ex.: `SUM(value)` sem filtrar `tipo` dá um número sem sentido). Rejeitada por decisão explícita do usuário, seguindo o precedente.
- **Confiança:** 0.55.

### Abordagem C — Fixar a fonte agora (Tesouro Nacional, RREO da União) sem descoberta real
- **O quê:** assumir de antemão que a fonte é o RREO/RGF federal do Tesouro Transparente, pular a etapa de descoberta no `/design`.
- **Por que não escolhida:** viola a regra inegociável "nunca inventar requisitos" (`CLAUDE.md`) e o próprio aprendizado do INSS (o schema real do Emitidos surpreendeu mesmo depois de "descoberto" uma vez) — o usuário decidiu explicitamente deixar essa escolha para a descoberta real. Rejeitada por decisão de escopo, não por trade-off técnico.
- **Confiança:** N/A (rejeitada por decisão do usuário).

---

## 6. Itens removidos / adiados (YAGNI)

| Item | Por que fora desta fatia | Vai para |
|---|---|---|
| Juros (`STORY-009.04`) | Fonte de dado provavelmente distinta (Selic/BCB, não Tesouro/SICONFI) — misturaria uma 3ª organização nesta fatia sem necessidade. | Fatia própria, sobre o padrão agora provado 3x. |
| Debt simulator (`STORY-009.06`) e stress test (`STORY-009.07`) | Dependem de um simulador ainda não construído (mesma lógica do SIM-004 do INSS: sem simulador real, um "insumo dedicado" seria desenhado às cegas). O Gold desta fatia, bem desenhado, já serve quando o simulador existir. | Épico/fatia própria, quando o simulador DebtLab entrar em backlog. |
| Quebra por categoria (receita tributária/contribuições; despesa por função/órgão) | Explode o schema nesta fatia sem necessidade comprovada de produto; total agregado já prova a cadeia ponta a ponta. | Incremento futuro, se o produto pedir o detalhe. |
| Quebra territorial (UF/município) | Só decidível depois da descoberta real da fonte (§3, pergunta 1) — se a fonte escolhida for nacional (União), não há UF; se for SICONFI, pode haver, mas fica para uma fatia futura sobre o padrão UF já provado 2x. | Fatia futura, se a fonte permitir e o produto pedir. |
| Série histórica no módulo M02 | Mesma decisão das 2 fatias anteriores: valor mais recente + provenance, não série. | `PRD-004` V1, incremento futuro. |
| PR/artefato dedicado a "insumo simulador" | Sem simulador real (DebtLab) para validar um artefato dedicado — mesma decisão do INSS. | Quando o simulador entrar em backlog próprio. |
| Autenticação/RBAC nos novos endpoints | Dados públicos agregados, mesma política das 2 fatias anteriores (`ADR-044`). | N/A — decisão permanente do portal público. |
| Agente/RAG/Copilot fiscal | Sem comportamento de agente nesta fatia — `agent-eval: n/a` no `gates.yaml` já cobre. | Fase de agentes, backlog próprio. |
| 2 tabelas Gold fundidas numa só | Receita e despesa são semanticamente distintas (lados opostos do resultado). Decisão: 2 tabelas Gold separadas. | N/A — decisão permanente, não adiamento. |

---

## 7. Requisitos-rascunho (para o `/define`)

### PR1 — espinha de dados
- **R1.** Descobrir o(s) recurso(s) real(is) de receita e despesa (Tesouro Transparente RREO/RGF, ou SICONFI — decisão de `/design`) e registrar em `dataset_registry` (`br2036_domain='fiscal'`, `br2036_module='M02'`).
- **R2.** 1-2 conectores sobre `connectors/base.py` (número exato depende de a fonte publicar receita e despesa no mesmo recurso ou em recursos separados). RAW imutável, SHA-256, sem reescrita.
- **R3.** Bronze→Silver→Gold: **2 tabelas Gold separadas** (`gold_fiscal_receita`, `gold_fiscal_despesa`), grão **total agregado por período** (mensal ou o que a fonte real oferecer).
- **R4.** Provenance (`metric_provenance`, `SPEC-007`): 1 linha por linha de métrica em cada uma das 2 Gold.
- **R5.** 2 contratos de dados (schema + `NOT NULL` em chaves + `value >= 0`).
- **R6.** Gate `integration` do `ci.yml` cobre pelo menos 1 dos 2 datasets via fixture determinística — zero infraestrutura de CI nova (reaproveita o mecanismo do `CI_ASSURANCE_GATES`).
- **R7.** Prova de aceite: query mostrando Gold + `metric_provenance` coerentes para receita e despesa num período real; `/verify-spec` PASS por requisito.

### PR2 — apresentação
- **R8.** `Config.metric_tables` ganha `fiscal_receita`/`fiscal_despesa` apontando para as 2 tabelas Gold novas — sem mudança de código em `main.py`/`bigquery_repo.py` (achado técnico §2), a confirmar no `/design`.
- **R9.** Resultado primário (SHOULD, `STORY-009.03`): decidir no `/design` como calcular (client-side no módulo web a partir de 2 chamadas de API, ou uma 3ª rota dedicada) — condicionado a receita e despesa terem o mesmo grão de período real.
- **R10.** 1 módulo M02 na Landing com receita, despesa (e resultado primário, se R9 viabilizar) do período mais recente, classe `observed` (`ADR-028`), link "fonte" para cada `source_url` real. Nenhum valor hard-coded (`ADR-012`).
- **R11.** Testes: contrato de dados (2x), integração via `ci-gate` já existente, teste de não-regressão confirmando que as rotas da dívida e do INSS continuam intactas (mesmo padrão do `test_debt_route_unaffected_by_national_route`), e2e leve confirmando os números novos no módulo M02.
- **R12.** Ritual de CI todo verde (reaproveita `ci.yml`/`ci-gate`, zero infraestrutura nova); `/security-check`; `/verify-spec` PASS.

---

## 8. Decisões autônomas registradas

| Decisão | Motivo |
|---|---|
| Fonte real (Tesouro Nacional vs SICONFI) **não fixada** nesta fase | Decisão explícita do usuário: repetir o padrão de descoberta real do INSS em vez de assumir formato/organização antes de olhar o dado de verdade. |
| Granularidade **total agregado**, não por categoria | Decisão de Claude, aceita pelo usuário — evita explodir o schema nesta fatia; mesmo espírito "walking skeleton" já usado 2x. |
| **2 tabelas Gold separadas** (`gold_fiscal_receita`/`gold_fiscal_despesa`), não fundidas | Decisão de Claude, aceita pelo usuário — segue o precedente já provado do INSS (C5): receita e despesa são lados opostos do mesmo resultado, fundir cedo confunde a métrica. |
| Resultado primário incluído como **SHOULD**, não MUST | Depende de receita e despesa caírem no mesmo grão de período real — risco real de não bater, só descoberto na prática; por isso não é um compromisso rígido. |
| Sem PR/artefato dedicado a "insumo simulador" | Mesma razão do INSS: sem simulador DebtLab real para validar um artefato dedicado — YAGNI. |

---

## 9. Questões abertas (resolver no `/define` ou `/design`, via ADR/SPEC quando alterarem arquitetura)

1. **Fonte real e formato do recurso** — Tesouro Transparente (RREO/RGF da União) ou SICONFI (estados/municípios)? Qual granularidade temporal (mensal, bimestral)? Tarefa 1 do `/design`.
2. **1 ou 2 conectores** — depende de a fonte publicar receita e despesa no mesmo arquivo/recurso ou em recursos separados. Só resolve na descoberta real.
3. **Resultado primário (R9)** — client-side (web soma/subtrai a partir de 2 chamadas de API) ou rota dedicada nova? E se receita e despesa não caírem no mesmo grão de período, o que substitui essa meta SHOULD?
4. **Terminologia exata do `metric_id`** — `fiscal_receita`/`fiscal_despesa`, ou nomes mais específicos à fonte real (ex.: `receita_uniao`, `receita_rreo`)? Decisão de `/define`, após a descoberta nomear os conceitos reais.
5. **Volume e custo de query** — retomar o achado residual do `CI_ASSURANCE_GATES` (cap de bytes por query, `R-012`), agora com uma 4ª fonte a considerar.

---

## 10. Domínios de KB para a Fase Define

- **PRDs:** `PRD-004` (Fiscal & DebtLab).
- **SPECs:** `SPEC-003` (Connectors), `SPEC-004` (RAW/Bronze/Silver/Gold), `SPEC-005` (Data Contracts), `SPEC-007` (Provenance), `SPEC-026` (API/OpenAPI Client), `SPEC-031` (CI Gates, já realizado — `ADR-054`), `SPEC-033` (referência de padrão, MVP Walking Skeleton).
- **ADRs:** `ADR-012` (LLM nunca computa métrica oficial), `ADR-028` (observed/estimated/simulated), `ADR-054` (`ci-gate` como required check único), `ADR-055` (escrita por partição/backfill resumível — reaproveitar diretamente).
- **Riscos:** `docs/risks/RISK-CONTROL-TEST-MATRIX.md`, `docs/risks/RISK-REGISTER.md` — atenção a instabilidade de schema da fonte (padrão já observado 1x real no INSS).
- **Backlog:** `EPIC-009` (Fiscal & DebtLab) — `STORY-009.01`, `STORY-009.02`, `STORY-009.03`.
- **Precedente direto:** `.claude/sdd/archive/MVP_WALKING_SKELETON/`, `.claude/sdd/archive/CI_ASSURANCE_GATES/`, `.claude/sdd/archive/INSS_BENEFICIOS/` — padrão de pipeline, CI e API multi-metric já provados, a reaproveitar sem reabrir decisão.

---

## 11. Quality gate (Fase 0)

- [x] Mínimo de 3 perguntas de discovery feitas e respondidas (6 feitas)
- [x] Pergunta de amostras feita (inputs, outputs, ground truth)
- [x] Pelo menos 2 abordagens exploradas com trade-offs (A, B, C)
- [x] Usuário confirmou explicitamente a abordagem escolhida (A) e o desenho emergente (checkpoint §-)
- [x] YAGNI aplicado — seção de itens removidos preenchida (9 itens)
- [x] Mínimo de 2 validações incrementais concluídas (checkpoint de estrutura Gold/objetivo; checkpoint de resumo final ~250 palavras)
- [x] Domínios de KB identificados para o Define
- [x] Requisitos-rascunho prontos para o `/define` (R1–R12)

---

## 12. Handoff

Pronto para `/define .claude/sdd/features/BRAINSTORM_FISCAL_RECEITA_DESPESA.md`.
