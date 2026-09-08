# BRASIL 2036 — Nos Trilhos

> Plataforma Nacional de Inteligência Econômica, Fiscal e Social. Repositório **spec-driven**:
> integra dados abertos oficiais (dados.gov.br, IBGE, BCB, Tesouro, INSS, SICONFI, CAGED, PNCP…)
> em indicadores canônicos e rastreáveis, Digital Twins (nacional / estadual / municipal),
> simuladores fora do LLM, forecast champion/challenger, análise causal e agentes especializados.
> Hoje o repositório contém **apenas documentação e contratos de processo** — não há código de
> aplicação. Alvo: 2º Concurso de Reúso de Dados Abertos da CGU (inscrições 29/06–11/09/2026).

---

## Contrato operacional (permanente)

Estas regras valem em toda sessão de código e **não** são alteradas pelo `/start`.

### Ordem de contexto obrigatória
Antes de alterar código:
1. Ler `/CONTEXTO.md`.
2. Localizar o PRD relevante em `/docs/prd`.
3. Ler o SPEC de implementação em `/docs/specs`.
4. Ler os ADRs relacionados em `/docs/adrs`.
5. Ler `/docs/risks/RISK-CONTROL-TEST-MATRIX.md`.
6. Inspecionar os testes existentes antes de editar implementação.

### Regras inegociáveis
- Nunca inventar requisitos.
- Nunca alterar produção diretamente.
- Nunca commitar credenciais, tokens, chaves ou segredos.
- Nunca enfraquecer ou burlar um gate de CI obrigatório.
- Nunca alterar um SPEC só para uma implementação passar.
- Nunca substituir um ADR silenciosamente; supere-o com outro ADR.
- Nunca conceder ferramentas de escrita a um agente read-only.
- Nunca publicar cenário / modelo / métrica automaticamente quando há aprovação exigida.
- Nunca deixar um LLM fabricar uma métrica numérica oficial.
- Toda resposta quantitativa oficial preserva provenance.
- Valores observados, estimados e simulados permanecem explicitamente distinguíveis.
- Sessões de review são read-only e não corrigem o código que revisam.

### Ritual de conclusão
Rodar os equivalentes do repositório:
- `/verify-spec`
- `/security-check`
- `/agent-eval` quando o comportamento de agente for afetado
- testes unit / integration / contract afetados pela mudança

### Estilo de código
Mudanças pequenas e revisáveis. Preservar contratos. Adicionar testes para comportamento alterado.

---

## Stack

Nenhum código ainda. Stack planejada, fixada em ADRs (`docs/adrs/`):

- **Cloud:** GCP, serverless-first (ADR-001, ADR-002). GKE fora da V1.
- **Verdade quantitativa:** BigQuery (ADR-003), camadas RAW → Bronze → Silver → Gold (ADR-005, ADR-006).
- **Estado operacional / approvals / checkpoints:** AlloyDB (ADR-004).
- **Transformação SQL:** Dataform (ADR-007).
- **Discovery de dados:** dados.gov.br como catálogo (ADR-008) + Dataset Registry interno (ADR-009).
- **IA:** Vertex AI / Gemini; RAG híbrido lexical + vector + metadata (ADR-026); GraphService (ADR-027).
- **API:** FastAPI → Pydantic → OpenAPI → cliente TS gerado (ADR-024); SSE para progresso de agente (ADR-025).
- **IaC:** Terraform (ADR-039) + Workload Identity Federation, sem chave estática (ADR-040).
- **Harness de código:** Claude Code (ADR-031); arquivos de agente em inglês (ADR-032).
- **Núcleo determinístico, borda probabilística** (ADR-013); simuladores fora do LLM (ADR-042).

## Estrutura

```
BRASIL2036/
├─ README.md              ponto de entrada, ordem de leitura
├─ CONTEXTO.md            memória canônica do produto (v5.0, PT-BR)
├─ AGENTS.md              agentes do produto: classes e permissão por capability (EN)
├─ CLAUDE.md              este arquivo — contrato operacional + orientação
├─ INDEX.md               índice de todos os artefatos (v5)
├─ MANIFEST.json          manifesto de integridade (path / sha256 / bytes)
├─ backlog/
│  └─ BACKLOG-MESTRE.md   47 épicos (EPIC-001…047)
├─ .github/
│  ├─ CODEOWNERS
│  ├─ pull_request_template.md
│  ├─ ci/gates.yaml       manifesto SPEC-031: gate → job/status (agent-eval: n/a)
│  └─ workflows/          ci.yml (gate de merge: changes+lint/type/unit+web+terraform+integration+spec-verify+secret-scan→ci-gate), infra.yml (apply), data.yml (deploy-and-run), api-web.yml (deploy)
├─ ingestion/             job de ingestão da fatia MVP (connector, RAW/Bronze/Silver/Gold SQL, contrato, provenance, pipeline, testes)
├─ infra/terraform/       IaC do projeto dev (backend GCS, buckets, BQ, Artifact Registry, Cloud Run Job, IAM, budget)
├─ scripts/               bootstrap.sh (bootstrap GCP+WIF, uma vez)
└─ docs/
   ├─ discovery/          7 docs: jornadas, AI value/risk, failure modes, irreversibilidade, assurance, métricas, MVP boundaries
   ├─ prd/                18 PRDs (PRD-001…018)
   ├─ adrs/               59 ADRs (ADR-001…059)
   ├─ specs/              34 SPECs (SPEC-001…034)
   ├─ risks/              RISK-REGISTER.md, RISK-CONTROL-TEST-MATRIX.md
   ├─ governance/         AI-GOVERNANCE, DATA-GOVERNANCE, RESPONSIBLE-AI
   ├─ access/             ACCESS-PROFILES.md, PERMISSION-MATRIX.md
   ├─ architecture/       ARCHITECTURE.md
   ├─ runbooks/           AGENT-INCIDENT, COST-ANOMALY, PIPELINE-FAILURE, SCHEMA-DRIFT
   ├─ simulators/         SIMULATORS-CATALOG.md (SIM-001…024)
   ├─ process/            PROCESS-VISIBLE.md
   └─ sources/            SOURCE-INDEX.md / .csv
```

(`.claude/` guarda os comandos e skills do harness — ver "Comandos úteis" — e, em `.claude/sdd/`, os artefatos do workflow SDD por feature.)

## Estado atual (2026-09-08)

- **Repo:** `github.com/JonatasLimaBR/Brazil-2036`, `origin/main`. **Branch protection ativa desde 2026-09-04**: PR-only, `required_status_checks = [ci-gate]`.
- **GCP:** projeto `brasil2036-dev`, região `southamerica-east1`. Provisionamento **GitOps via WIF**: `scripts/bootstrap.sh` (uma vez) → 5 *Actions Variables* → `ci.yml` (gate de merge) + `infra.yml`/`data.yml`/`api-web.yml` (deploy/apply pós-merge). Sem chave estática.
- **`MVP_WALKING_SKELETON` — ✅ SHIPPED (2026-09-03).** Ciclo SDD 0–4 completo; `/verify-spec` independente = OVERALL PASS. Prova a cadeia de provenance ponta a ponta com "Dívida Consolidada dos Estados e do DF" (Tesouro Transparente/CKAN, ODbL; `metric_id='divida_consolidada'`, bruta, anual por UF).
  - Vivo: web `https://br2036-web-gzt6fzwoda-rj.a.run.app` · api `https://br2036-api-gzt6fzwoda-rj.a.run.app`.
  - Arquivo: `.claude/sdd/archive/MVP_WALKING_SKELETON/`. Código em `ingestion/`, `api/`, `web/`, `infra/terraform/`, `scripts/`. SPEC-033, ADR-051/052/053.
- **`CI_ASSURANCE_GATES` — ✅ SHIPPED (2026-09-04).** Realiza `SPEC-031`/ADR-054: `ci.yml` (guarda-chuva sem filtro de path) → `changes` decide gates condicionais (`lint-typecheck-unit`, `web-check`, `terraform`, `integration` contra BigQuery real em dataset `citest_<run>_*` isolado, `spec-verify`, `secret-scan`) → `ci-gate` agrega (`if: always()`) e é o único required check. `scripts/spec_verify.py` + `.github/ci/gates.yaml` dão piso mecânico ao `/verify-spec` humano (não o substituem). PR #1 provou ao vivo (integration 1m7s, ci-gate verde); PR #2 (docs-only) provou o pass-through (ci-gate verde em ~6 s).
  - Arquivo: `.claude/sdd/archive/CI_ASSURANCE_GATES/`. ADR-054; SPEC-031/ADR-036 atualizados.
- **`INSS_BENEFICIOS` — ✅ SHIPPED (2026-09-05).** Ciclo SDD 0–4 completo (Brainstorm→Define→Design→Build→`/verify-spec` OVERALL PASS→Ship). Fatia #2: ingestão dos 3 datasets P0 de INSS (Emitidos/Mantidos/Indeferidos, `SPEC-011`/`PRD-005`/`EPIC-010`, `ADR-055`). Prova o padrão de pipeline contra um domínio mais hostil (3 formatos de origem — ZIP/CSV/XLSX —, grão UF×espécie×mês, schema real instável). **Corrigiu um risco crítico pré-existente** antes de tocar produção: `registry.py`/`provenance.py` faziam `CREATE OR REPLACE TABLE` em tabelas *compartilhadas* (`dataset_registry`, `metric_provenance`) — rodar para um 2º dataset teria apagado os dados da dívida. Endpoint aditivo `GET /v1/metrics/{metric_id}/national` + módulo M03 na Landing.
  - **Backfill real contra `brasil2036-dev` (confirmado pelo usuário a cada etapa):** Indeferidos completo — 37/38 meses, 15.142 linhas. Emitidos — 1 mês no formato atual, 1.216 linhas (schema-fonte mudou 4+ vezes em <3 anos; histórico completo exigiria parser adaptativo, fora de escopo por decisão explícita do usuário). Mantidos — nenhum mês rodado (mecanismo provado só via CI).
  - `/verify-spec` independente = OVERALL PASS, verificado ao vivo contra BigQuery/endpoints em produção. Achado E1 (endpoint nacional de Mantidos devolvia 500 em vez de 404) corrigido (PR #12); achado W1 (Indeferidos não preserva XLSX original em RAW) aceito como desvio documentado, baixa prioridade.
  - Arquivo: `.claude/sdd/archive/INSS_BENEFICIOS/`. ADR-055; código em `ingestion/src/ingestion/connectors/inss_*.py`, `api/src/api/`, `web/src/inss.ts`.
- **`FISCAL_RECEITA_DESPESA` — ✅ SHIPPED (2026-09-05).** Ciclo SDD 0–4 completo (Brainstorm→Define→Design→Build→`/verify-spec` OVERALL PASS 0.93→Ship). Fatia #3: receita líquida, despesa total e resultado primário do Governo Central (`EPIC-009`, `STORY-009.01/02/03`, `ADR-056`). Fonte real descoberta e inspecionada no `/design` (não suposição): "Resultado do Tesouro Nacional — Série Histórica" (Tesouro Transparente/CKAN, ODbL) — 1 arquivo XLSX republica o histórico mensal inteiro a cada mês (forma de publicação nova, nem "1 arquivo imutável" da dívida nem "1 recurso por período" do INSS — novo módulo `pipeline_wide_series.py`). **Achado crítico (D10) corrigido antes de tocar produção:** 135 dos 356 meses reais (38%) de resultado primário são negativos (déficit) — `contract.check_gold_period` rejeitava incondicionalmente qualquer valor negativo; corrigido com `allow_negative`, aplicado só a `fiscal_primario`. `bronze.load()`/`provenance.write_from_gold()` generalizados de forma aditiva (testes de regressão cobrindo dívida e INSS). 1 tabela Gold (`gold_fiscal_uniao`) com 3 `metric_id`s — reaproveita o endpoint `/national` genérico do INSS sem mudar `main.py`/`bigquery_repo.py`. Módulo M02 na Landing ("Receita líquida"/"Despesa total"/"Resultado primário", com qualificador "(déficit)" quando negativo).
  - **Backfill real contra `brasil2036-dev` (confirmado pelo usuário) — completo, diferente das 2 fatias anteriores:** 355 meses (1997-01 a 2026-07), 1.065 linhas Gold, valores conferidos manualmente contra o arquivo-fonte real (jul/2026: receita líquida R$ 226,3 bi, despesa R$ 215,5 bi, primário R$ 10,8 bi — batem exatamente). Dívida (27) e INSS (1.216 + 15.142) confirmadamente intactos.
  - `/verify-spec` independente = OVERALL PASS (confiança 0.93), todos os AT1-AT11/S1-S7 aprovados com evidência ao vivo (BigQuery real, endpoints de produção). 1 achado WARNING não-bloqueante (e2e fiscal com asserção fraca, mesmo padrão já aceito no INSS).
  - Arquivo: `.claude/sdd/archive/FISCAL_RECEITA_DESPESA/`. ADR-056; código em `ingestion/src/ingestion/{connectors/fiscal_uniao.py,pipeline_wide_series.py}`, `api/src/api/config.yaml`, `web/src/fiscal.ts`.
- **`BIGQUERY_OPERATIONAL_STANDARDS` — ✅ SHIPPED (2026-09-06).** Ciclo SDD 0–4 completo (Brainstorm→Define→Design→Build→`/verify-spec` OVERALL PASS ~92%→Ship). Primeira feature do projeto que não é uma fatia de dados — norma de engenharia transversal (mesmo papel de `SPEC-031` para CI), pedida pelo usuário ao final da fatia fiscal. Fecha o achado residual `R-012` (rastreado desde `CI_ASSURANCE_GATES`, nunca fechado) — nenhuma query de produção tinha `maximum_bytes_billed`. `run_sql()`/`scalar()` (`ingestion/`) e `build_bigquery_run_query()` (`api/`) agora aplicam **1 GiB por padrão**, aditivo. Pesquisa real sobre billing do BigQuery (não suposição): `LOAD DATA` é billado como carga grátis, não como bytes processados — `bronze.py` opta explicitamente por não ter cap (já visto arquivo-fonte real de 7+ GB no INSS). `SPEC-034` formaliza a convenção de particionamento/clustering já usada nas 3 fatias (extraída do real, não inventada) + política de retenção por camada. `ADR-057` formaliza a decisão de código.
  - **Achado real não planejado, corrigido no mesmo dia (PR #21):** o merge do PR do cap disparou o job automático `data.yml`, cujo passo "verify provenance chain" (`ingestion/scripts/verify_chain.py`) falhou de verdade em produção — bug pré-existente (não relacionado ao cap): a query contava `metric_provenance` só por `reference_year`, sem filtrar `metric_id`; como a tabela é compartilhada (`ADR-055`) e o backfill real da fatia fiscal (1997-2026) tem linhas em 2022 (ano da dívida), a contagem somava as duas métricas (27 dívida + 36 fiscal = 63 ≠ 27 esperado). Corrigido com filtro `--metric-id` explícito; verificado contra produção antes e depois da correção.
  - `/verify-spec` independente = OVERALL PASS (~92%), reproduziu de forma independente o bug/correção do `verify_chain.py` contra BigQuery real. Achado WARNING (teste de rejeição acima do cap prometido no DESIGN mas nunca escrito) corrigido no mesmo dia (PR #23, `_RejectingFakeBigQuery`); achado INFO cosmético (exemplo de clustering do INSS Mantidos no SPEC-034) corrigido junto.
  - Arquivo: `.claude/sdd/archive/BIGQUERY_OPERATIONAL_STANDARDS/`. SPEC-034; ADR-057; código em `ingestion/src/ingestion/{bigquery_io.py,bronze.py,scripts/verify_chain.py}`, `api/src/api/bigquery_repo.py`.
- **`LANDING_PAGE_ASTRO` — ✅ SHIPPED (2026-09-07).** Ciclo SDD 0–4 completo (Brainstorm→Define→Design→Build→`/verify-spec` OVERALL PASS WITH FINDINGS→Ship). Implementa `docs/landpage.png` (mockup fornecido pelo usuário) com dado real (não fabricado) e selos de status rastreáveis. Migra `web/` de Vite+TS puro para **Astro** (`output: "static"`) — `ADR-058` supera `ADR-051` explicitamente (nota "Superseded by" em `ADR-051`, nunca substituição silenciosa). Painel "Command Center" fictício do mockup (índices/alertas inventados) substituído por painel de dados reais (dívida/fiscal/INSS, mesmos 3 endpoints já em produção) — decisão do usuário para não violar `ADR-012`. Grid de módulos (15), arquitetura GCP (12 componentes) e roadmap (8 fases) carregam selo `real`/`parcial`/`planejado` (ou `concluída`/`em andamento`/`não iniciada`) com `evidence` obrigatório em `web/src/data/status.ts` (35 entradas), citando um `SHIPPED` doc/ADR/Terraform real por entrada — mecanismo para impedir selo fabricado, com `data-evidence` também exposto no DOM e testado por e2e.
  - PR #25 (estrutura Astro + dados reais): achado real corrigido no mesmo PR — `spec-checks/SPEC-033.yaml` ainda apontava para `web/src/main.ts` (deletado pela migração); atualizado para `web/src/lib/metrics.ts`.
  - PR #26 (conteúdo com status real): achado real corrigido no mesmo PR — o novo card "Previdência & INSS" do grid de módulos colidiu com o `<h3>` do painel de dados no e2e pré-existente (`getByText` ambíguo); corrigido escopando o locator a `#dados-reais`.
  - `/verify-spec` independente (subagente `general-purpose`, sessão nova, read-only) = OVERALL PASS WITH FINDINGS — nenhum valor/selo fabricado. 4 achados reais corrigidos (PR #28): âncora `#contato` morta (Nav + FooterCta); CTA "Ver Roadmap" do mockup ausente sem nota de desvio; evidência do IAM/WIF imprecisa (citava Terraform, é `bootstrap.sh`); `.github/ci/gates.yaml` desatualizado (`tsc --noEmit` → `astro check`). 1 achado pré-existente aceito (comentários fracos do e2e de INSS/fiscal, já rastreado); 1 é limitação de ambiente do revisor, não do projeto.
  - `typecheck`/`build`/e2e (5/5, incluindo teste "todo selo tem evidence não-vazio") verdes contra a API real de produção em todos os PRs; `ci-gate` verde em `#25`, `#26`, `#27`, `#28`.
  - Arquivo: `.claude/sdd/archive/LANDING_PAGE_ASTRO/`. ADR-058; código em `web/src/{pages/index.astro,components/*.astro,lib/metrics.ts,data/status.ts}`.
- **`DEBTLAB_SIMULATOR` — ✅ SHIPPED (2026-09-08).** Ciclo SDD 0–4 completo (Brainstorm→Define→Design→Build→`/verify-spec` OVERALL PASS WITH FINDINGS→Ship). Primeiro simulador determinístico do projeto (`SIM-002`/`SPEC-010`/`PRD-004`), prova o padrão "núcleo determinístico, borda probabilística" (`ADR-013`/`ADR-042`) que nenhuma das 6 features anteriores havia tocado. Escopo cresceu por decisão explícita do usuário durante o `/brainstorm` ("incluir tudo que falta para entregar dados reais", rejeitando 2 simplificações oferecidas): a fatia combina ingestão real de PIB + Dívida Bruta do Governo Geral (BCB SGS, séries 4380/13762, fonte P0 já listada em `SOURCE-INDEX.csv`) com o engine + Monte Carlo (`SPEC-016`) já no V1.
  - **Achado real que mudou o desenho:** `divida_consolidada` (dívida estadual PAF, 2022) não é a métrica certa para "base debt/GDP" — é dívida bruta nacional do governo geral, um conceito diferente. Corrigido antes de construir: nova métrica real (`divida_bruta_pib`) ingerida em vez de reaproveitar a errada.
  - **Primeira permissão de escrita da API:** `api-runtime` era 100% somente-leitura ("read-only on Gold") — `roles/bigquery.dataEditor` escopado só a `br2036_control` (least-privilege); CORS ganhou `POST`. Persistência de cenário em BigQuery, não AlloyDB (`ADR-004` nunca provisionado em 6 features; custo fixo sem approval workflow real que justifique, contra `ADR-002` serverless-first). `ADR-059` formaliza sem superar `ADR-004`.
  - **Achado real pós-merge, corrigido no mesmo dia (PR #33):** `maximum_bytes_billed=None` passado literalmente pro `QueryJobConfig` serializava como a string `"None"` (BigQuery rejeita, `TYPE_INT64`) — primeiro `POST /v1/simulations/debtlab` real em produção 500ou minutos após o merge do PR2. Corrigido; teste de regressão verificado contra o padrão com bug e contra o fix.
  - **Backfill real contra `brasil2036-dev`:** `pib_mensal` 438 linhas, `divida_bruta_pib` 236 linhas. `POST`/`GET /v1/simulations/debtlab` verificados ao vivo ponta a ponta.
  - `/verify-spec` independente (subagente `general-purpose`, sessão nova, read-only) = OVERALL PASS WITH FINDINGS — fórmula do engine re-derivada à mão pelo revisor, bateu exatamente contra código e API real; nenhum valor/selo fabricado. 2 achados reais corrigidos (PR #35): formato de `created_at` inconsistente entre `POST`/`GET`; frase imprecisa no BUILD_REPORT sobre o comportamento real do bug do PR #33 (levanta `ValueError`, não normaliza silenciosamente). 1 achado pré-existente aceito (pipelines novos não plugados no job noturno automático, mesmo padrão já rastreado).
  - Arquivo: `.claude/sdd/archive/DEBTLAB_SIMULATOR/`. ADR-059; código em `ingestion/src/ingestion/connectors/bcb_sgs.py`, `api/src/api/simulators/`.
- **`MACRO_TWIN_EXPANSION` — ✅ SHIPPED (2026-09-08).** Ciclo SDD 0–4 completo (Brainstorm→Define→Design→Build→`/verify-spec` OVERALL PASS WITH FINDINGS (0.94)→Ship). Continua o Macro Twin (`EPIC-008`/`PRD-003`/`SPEC-009`) com 3 séries reais novas do BCB SGS — IPCA (série 433, `ipca_mensal`, único com `allow_negative: true` — achado real: mês de deflação), SELIC (série 4390 mensal, não 432 diária), câmbio USD/BRL (série 3695 mensal, não 1 diária) — 100% reaproveitando o `BcbSgsConnector`/`pipeline_wide_series.py` provado no `DEBTLAB_SIMULATOR`, cada série com seu próprio conjunto Bronze/Silver/Gold (sem tabela compartilhada). Novo endpoint `GET /v1/simulations/debtlab/suggested-assumptions` deriva premissas sugeridas (juros nominal anualizado a partir de SELIC composta 12x; crescimento nominal do PIB via YoY médio de 12 meses) de dado Gold real, `data_class=estimated` (`ADR-028`) — `ADR-060` formaliza a metodologia.
  - **2º bug real de produção da sessão (PR #39, mesmo dia):** a query YoY de `pib_mensal` tinha `ORDER BY`/`LIMIT` fora dos parênteses do `SELECT` agregador — BigQuery rejeitou (`400 ORDER BY clause expression references column reference_date which is neither grouped nor aggregated`) na 1ª chamada real do endpoint novo. Corrigido com aninhamento SQL de 3 níveis. **Causa raiz sistêmica fechada junto:** `api/` nunca tinha tido teste de integração contra BigQuery real (só mocks por substring, que não pegam erro de sintaxe SQL) — mesma categoria do bug do `maximum_bytes_billed` no `DEBTLAB_SIMULATOR`. Fechado com `api/tests/integration/` + marker `integration` em `api/pyproject.toml` (espelhando `ingestion/`) + nova etapa no job `integration` do `ci.yml`, validada ao vivo pela 1ª vez no próprio PR #39 (`ci-gate` verde, 5m14s).
  - **Backfill real contra `brasil2036-dev`:** confirmado completo para as 3 séries novas via `/v1/metrics/{id}/national` ao vivo (`data_class: observed` em todas). Endpoint `suggested-assumptions` reverificado ao vivo pós-deploy: `HTTP 200`, `juros_nominal.mean≈0.1349`, `crescimento_nominal_pib.mean≈0.0716`.
  - `/verify-spec` independente (subagente `general-purpose`, sessão nova, read-only) = OVERALL PASS WITH FINDINGS (0.94) — todos os 8 AT verificados ao vivo em produção; narrativa do bug/hotfix (Achado #4) reproduzida de forma independente, incluindo a matemática do `pytest.approx` conferida à mão. 1 achado real pré-existente (não desta feature, mas agravado por ela): `web/src/data/status.ts` ainda marcava "Macro Economic Twin" como `planejado` com evidência desatualizada, visível ao vivo na landing — corrigido para `parcial` com evidência real (5 `metric_id`s reais) antes do `/ship`.
  - Arquivo: `.claude/sdd/archive/MACRO_TWIN_EXPANSION/`. PRs `#37`-`#41` (ingestão, endpoint, hotfix real, docs sync, ship). ADR-060; código em `ingestion/{contracts,config,sql}/{ipca_mensal,selic_mensal,cambio_usd_brl}*`, `api/src/api/bigquery_repo.py::suggested_assumptions()`, `api/tests/integration/`.
- **Follow-ups rastreados (SHIPPED §7 de CI_ASSURANCE_GATES):** revisão humana obrigatória em `main` (hoje só CI); job noturno contra a fonte real do Tesouro (drift); bump de actions Node 20. **Follow-ups antigos ainda abertos (MVP_WALKING_SKELETON §7):** URL do catálogo dados.gov.br → `dataset_registry.source_url` (concurso CGU); `wif.tf`/serviços no Terraform; `MANIFEST.json`; provenance histórica. **Follow-ups do INSS_BENEFICIOS:** parser adaptativo por nome de coluna para backfill completo de Emitidos/Mantidos; Mantidos sem dado real carregado; W1 (RAW do Indeferidos não preserva XLSX original) — baixa prioridade. **Follow-up do FISCAL_RECEITA_DESPESA:** e2e do módulo fiscal com asserção fraca (SHIPPED §7) — baixa prioridade. **Follow-ups do BIGQUERY_OPERATIONAL_STANDARDS (SHIPPED §7):** `ingestion/scripts/*.py` sem cobertura de teste unitário (só verificação por execução real — já deixou 1 bug real escapar até produção); orçamento de projeto/billing export (`R-012`, `EPIC-042`, ainda não implementado); TTL de Bronze/Silver (`SPEC-034 §3`, decisão explícita de não implementar ainda — YAGNI); enforcement automático via lint de CI. **Follow-ups do LANDING_PAGE_ASTRO (SHIPPED §7):** comentários de graceful-degradation em `card.spec.ts` desatualizados (pré-existente); `status.ts` exige atualização manual a cada `/ship` futuro, sem enforcement automático. **Follow-ups do DEBTLAB_SIMULATOR (SHIPPED §7):** `pib_mensal`/`divida_bruta_pib` não plugados no job noturno `data.yml` (mesmo padrão de débito já rastreado); sem UI de simulador em `web/` ainda; rate-limiting real do endpoint de escrita fica pra quando RBAC/ABAC existir. **Follow-ups do MACRO_TWIN_EXPANSION:** `ipca_mensal`/`selic_mensal`/`cambio_usd_brl` não plugados no job noturno `data.yml` (mesmo padrão já rastreado); Macro Twin ainda sem forecast/cenários completos (`EPIC-008`); sem UI de `suggested-assumptions` em `web/` ainda.
- **Próximo passo:** iniciar a próxima feature via `/brainstorm` ou `/define` — sequência já combinada com o usuário: RAG básico → RBAC/ABAC + portal autenticado (fatia de dados #4/Macro Twin concluída).

## Arquivos-chave

| Arquivo | Função |
|---------|--------|
| `CONTEXTO.md` | Memória canônica: identidade, problema, objetivos, arquitetura GCP, 18 módulos, 24 simuladores, security by architecture, MVP, roadmap de 15 fases |
| `AGENTS.md` | Classes de agente (READ / COMPUTE / DRAFT / PUBLISH / PRIVILEGED-SECURITY) e a regra de permissão por *capability* (proibido = ausente do toolset) |
| `README.md` | Onde começar e o processo Discovery → PRD → ADR → SPEC → Tests → Code → Eval → Review → PR → Merge |
| `INDEX.md` | Lista completa de artefatos |
| `MANIFEST.json` | Hash sha256 de cada arquivo — verificação de integridade do pacote |
| `backlog/BACKLOG-MESTRE.md` | 47 épicos priorizados (Discovery → Landing → Foundation → Open Data Hub → Data Platform → Macro/Fiscal/INSS → Simulators/RAG/Agent MVP) |
| `docs/architecture/ARCHITECTURE.md` | Pipeline dados.gov.br → RAW → Bronze/Silver/Gold → Semantic/Forecast/Graph/RAG → Vertex → Orchestrator → Approval Queue → Portais; *truth boundaries* |
| `docs/risks/RISK-CONTROL-TEST-MATRIX.md` | Risco → controle → teste (leitura obrigatória antes de código) |
| `docs/specs/SPEC-030-CLAUDE-HARNESS.md` | Contrato do harness de código |
| `docs/specs/SPEC-031-CI-GATES.md` | Gates de CI obrigatórios |
| `.claude/commands/*.md` | Rituais: understand / implement / verify-spec, security-check, agent-eval, review-pr |
| `.claude/skills/*/SKILL.md` | Skills vendorizadas e pinadas (`skills.lock`): agent-security, data-contract, gcp-data-engineering, spec-verifier, terraform-review |

## Convenções

- **Python (`ingestion/`):** `uv` para ambiente; `ruff` (lint+format, line-length 100), `mypy --strict`, `pytest`. Rodar: `cd ingestion && uv run ruff check . && uv run mypy && uv run python -m pytest -q`.
- **IaC (`infra/terraform/`):** Terraform ≥ 1.5, provider `google ~> 6`; `terraform fmt` + `validate` no CI; backend GCS.
- **CI:** `.github/workflows/ci.yml` é o gate de merge (único required check = `ci-gate`); `infra.yml`/`data.yml`/`api-web.yml` só fazem deploy/apply pós-merge em push→`main`. Pipeline-alvo completo em CONTEXTO §24. Gate obrigatório que falha = merge bloqueado (SPEC-031/ADR-054).
- **Branches:** `main` protegida (branch protection ativa 2026-09-04), PR-only; `feature/*`, `fix/*`, `docs/*`, `chore/*`
- **Commits:** Conventional Commits
- **Idioma:** artefatos de produto (CONTEXTO, PRD, ADR, SPEC) em PT-BR; arquivos de agente/harness (`CLAUDE.md`, `AGENTS.md`, `.claude/`) em inglês por design (ADR-032); código e comentários em inglês

## Como trabalhar

```bash
# Fluxo por feature (author em uma sessão, reviewer em sessão nova e read-only):
#   /understand-spec  ->  /implement-spec  ->  /verify-spec  ->  /security-check  ->  /agent-eval  ->  /review-pr
# Provisionamento GCP: scripts/bootstrap.sh (uma vez) -> Actions Variables -> push (infra.yml + data.yml via WIF)
```

---

## Agentes recomendados

| Agente | Quando usar |
|--------|-------------|
| `brainstorm-agent`, `planner` / `the-planner`, `design-agent` | Fase atual: explorar abordagem, planejar e desenhar a arquitetura de um SPEC antes de escrever código |
| `security-reviewer`, `code-reviewer` | Toda mudança de código — sempre |
| `python-developer`, `python-reviewer` | Código Python (conectores, engines, API, agentes) |
| `gcp-data-architect`, `ai-data-engineer-gcp` | Infra de dados GCP, pipelines BigQuery / Dataform, RAW imutável |
| `data-contracts-engineer`, `data-quality-analyst` | Data contracts, schema drift / quarantine, Data Trust Score |
| `databricks-spark-expert`, `dbt-specialist`, `airflow-specialist` | Transformação em escala e orquestração, quando aplicável |
| `genai-architect`, `ai-prompt-specialist` | Orquestrador de agentes, tool registry, grounding, versões de prompt |
| `ci-cd-specialist` | Terraform, Workload Identity Federation, pipelines de CI |
| `sql-optimizer` | SQL BigQuery, semantic / metric layer |
| `typescript-reviewer` | Cliente TS gerado do OpenAPI, portais |

## Comandos úteis

| Comando | Quando usar |
|---------|-------------|
| `/understand-spec` | Ler CONTEXTO + PRD + SPEC + ADRs + matriz de risco + testes e devolver escopo, critérios de aceite, riscos e testes a rodar |
| `/implement-spec` | Implementar exatamente o SPEC selecionado, sem comportamento extra |
| `/verify-spec` | Verificação independente PASS/FAIL por requisito (sessão nova, read-only) |
| `/security-check` | Segredos, fronteiras de autorização, exposição de tool, PII em log, impacto IAM/Terraform, bypass de approval |
| `/agent-eval` | Suites de eval de agente: groundedness, tool selection, citação/provenance, fidelidade numérica, tentativas de capability não autorizada |
| `/review-pr` | Revisar PR contra PRD / SPEC / ADRs / riscos / testes |
| `/core:status`, `/core:health` | Status do projeto / diagnóstico do agentcode |
| `/brainstorm`, `/define`, `/design`, `/build`, `/ship` | Workflow SDD por fase |
| `/pipeline`, `/spark`, `/sql`, `/party`, `/preflight` | Auxiliares de engenharia de dados |

---

_Regenerado por `/start --force` em 2026-09-02. O "Contrato operacional (permanente)" acima foi
preservado do `CLAUDE.md` original — backup em `CLAUDE.md.bak.20260902-174025`._
