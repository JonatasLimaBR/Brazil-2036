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
│  └─ workflows/          infra.yml (terraform via WIF), data.yml (checks+deploy+verify), security.yml (gitleaks)
├─ ingestion/             job de ingestão da fatia MVP (connector, RAW/Bronze/Silver/Gold SQL, contrato, provenance, pipeline, testes)
├─ infra/terraform/       IaC do projeto dev (backend GCS, buckets, BQ, Artifact Registry, Cloud Run Job, IAM, budget)
├─ scripts/               bootstrap.sh (bootstrap GCP+WIF, uma vez)
└─ docs/
   ├─ discovery/          7 docs: jornadas, AI value/risk, failure modes, irreversibilidade, assurance, métricas, MVP boundaries
   ├─ prd/                18 PRDs (PRD-001…018)
   ├─ adrs/               52 ADRs (ADR-001…052)
   ├─ specs/              33 SPECs (SPEC-001…033)
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

## Estado atual (2026-09-03)

- **Repo:** `github.com/JonatasLimaBR/Brazil-2036`, `origin/main`. Histórico linear (baseline → SDD docs → ADR-051/052 + SPEC-033 → descoberta + cascata → código do PR1).
- **Feature em curso: `MVP_WALKING_SKELETON`** — fatia vertical que prova a cadeia de provenance com "Dívida Consolidada dos Estados e do DF" (CSV `UF;ANO;VALOR` do Tesouro Transparente/CKAN, licença ODbL; métrica `divida_consolidada` bruta/anual). SDD Fases 0–2 concluídas; artefatos em `.claude/sdd/features/{BRAINSTORM,DEFINE,DESIGN,DISCOVERY}_*.md` e `.claude/sdd/reports/BUILD_REPORT_*.md`.
- **Fase 3 (Build) — parcial:**
  - **PR1 (espinha de dados): código completo, verificado localmente** (`ruff` + `mypy --strict` + `pytest` 44 + `terraform validate`). `ingestion/**` + `infra/terraform/**` + `scripts/bootstrap.sh` + workflows `infra.yml`/`data.yml`/`security.yml`. **Falta rodar em GCP real.**
  - Modelo de provisionamento: **GitOps via WIF** — `bootstrap.sh` (manual, uma vez) cria projeto/billing/APIs/bucket-de-state/pool-WIF/`tf-deployer`; o resto vem do `terraform` rodando no GitHub Actions.
  - **PR2 (API + web): não iniciado.**
- **Pendências operacionais:** rodar `scripts/bootstrap.sh` (P2) e adicionar as 5 *Actions Variables* (`GCP_PROJECT`, `GCP_REGION`, `GCP_TF_STATE_BUCKET`, `GCP_WIF_PROVIDER`, `GCP_DEPLOYER_SA`) (P4). Menores: times de `CODEOWNERS` (P5), regenerar `MANIFEST.json` (P6), URL do catálogo dados.gov.br (P7).
- **Nota:** os documentos SDD por feature vivem em `.claude/sdd/` (não versionado como código de produto, mas commitado). `DEFINE`/`DESIGN` seguem `Ready for Build` até PR1+PR2 verificados em GCP.

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
- **CI:** `.github/workflows/` — `infra.yml`, `data.yml`, `security.yml`. Pipeline-alvo completo em CONTEXTO §24. Gate obrigatório que falha = merge bloqueado.
- **Branches:** `main` protegida, PR-only; `feature/*`, `fix/*`, `docs/*`, `chore/*`
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
