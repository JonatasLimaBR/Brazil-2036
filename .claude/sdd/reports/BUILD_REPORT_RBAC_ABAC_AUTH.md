# BUILD REPORT — RBAC_ABAC_AUTH

## Metadados

- **Feature:** RBAC_ABAC_AUTH
- **Fase:** 3 (Build)
- **Entrada:** `.claude/sdd/features/DESIGN_RBAC_ABAC_AUTH.md` (Ready for Build)
- **Branch:** `feature/rbac-abac-auth`
- **Data:** 2026-09-09
- **Status da build:** 🔄 Em andamento (PR1 de 4 — infra) — não pronto para `/verify-spec` ainda
- **Próximo passo:** completar PR2 (motor de autorização + AlloyDB repo), PR3 (aplicação real
  nos endpoints + login na landing), PR4 (testes formais + ADR + matriz) antes do `/verify-spec`

---

## 1. Task execution

### PR1 — Rede + AlloyDB + budget (infra spike, DESIGN, ordem de build sugerida)

| # | Arquivo | Ação | Nota |
|---|---|---|---|
| 1 | `infra/terraform/network.tf` | Create | VPC `rbac-vpc` + subnet `/26` + Private Services Access (`google_compute_global_address`+`google_service_networking_connection`) |
| 2 | `infra/terraform/alloydb.tf` | Create | `google_alloydb_cluster` (não-HA, `network_config` block) + `google_alloydb_instance` (2 vCPU/16GB, `availability_type=ZONAL` explícito) + senha inicial via `random_password`+Secret Manager |
| 3 | `infra/terraform/variables.tf` | Modify | `budget_amount_brl`: `50` → `1800` (D3) |
| 4 | `infra/terraform/apis.tf` | Modify | +`servicenetworking.googleapis.com`, +`alloydb.googleapis.com`, +`vpcaccess.googleapis.com` |
| 5 | `infra/terraform/versions.tf` | Modify | +provider `random` |
| 6 | `.github/workflows/api-web.yml` | Modify | `gcloud run deploy br2036-api` ganha `--network rbac-vpc --subnet rbac-subnet --vpc-egress private-ranges-only` (D2); +step "wait for rbac-subnet" (mesmo padrão já usado pro `api-runtime` SA, evita corrida entre `infra.yml` e `api-web.yml` no mesmo push) |
| 7 | `scripts/bootstrap.sh` | Modify | `tf-deployer` ganha `roles/secretmanager.admin`, `roles/alloydb.admin`, `roles/compute.networkAdmin`, `roles/servicenetworking.networksAdmin` |

---

## 2. Achados técnicos durante o build (não previstos em detalhe pelo DESIGN)

### Achado #1 — `google_alloydb_cluster` não aceita `network` no nível raiz

O esqueleto do `DESIGN §4.3` usava `network = google_compute_network.rbac_vpc.id` direto no
recurso — `terraform validate` real rejeitou (`Unsupported argument`). Introspeccionado o schema
real do provider (`terraform providers schema -json`, não suposto): o campo correto é
`network_config { network = ... }`, um bloco aninhado. Corrigido antes de qualquer commit —
mesma disciplina de "verificar contra o real antes de escrever em cima" já aplicada a bugs de SQL
em fatias anteriores, aqui aplicada a um bug de schema de Terraform.

### Achado #2 — `availability_type` deixado implícito seria uma aposta, não uma decisão

O esqueleto original do `/design` não fixava `availability_type` no `google_alloydb_instance` —
o `terraform plan` real mostrou o campo como `(known after apply)`, ou seja, dependente do
comportamento padrão da API, não da config. Corrigido pra `availability_type = "ZONAL"` explícito
(D1: não-HA) — evita depender de um default implícito que poderia mudar de comportamento entre
versões do provider.

### Achado #3 — IAM do `tf-deployer` precisava de 4 roles novos, nenhum coberto pelas fatias anteriores

`tf-deployer` (usado pelo CI via WIF) não tinha `secretmanager.admin`/`alloydb.admin`/
`compute.networkAdmin`/`servicenetworking.networksAdmin` — nenhuma fatia anterior tinha
precisado de rede/AlloyDB/Secret Manager antes. Concedidos ao vivo via `gcloud` (mesmo ritual do
achado de IAM do `RAG_PROVENANCE_QA`) antes de abrir o PR, pra não repetir o padrão de "CI falha
no 1º push por falta de permissão" já visto naquela fatia.

### Achado #4 — `budget_amount_brl` pode não estar realmente aplicado em produção hoje

`google_billing_budget.dev` (`budget.tf`) só existe (`count`) quando `var.billing_account != ""`
— nem o `terraform plan` do `ci.yml` nem meu `plan` local passam essa variável, então o recurso
de orçamento real fica em `count = 0` em todo `plan`/`apply` automatizado observável. Isso sugere
que o alerta de orçamento real (se existe) foi criado por um `apply` manual único (fora do CI),
similar em espírito ao `scripts/bootstrap.sh`. **Não é um problema introduzido por esta fatia** —
o valor de `budget_amount_brl` está corrigido no Terraform (pronto pra ser aplicado quando/se
`billing_account` for passado), mas não há confirmação nesta sessão de que o alerta real no GCP
já reflete os novos R$1.800. Registrado como achado, não como bug corrigido — fora do escopo
desta fatia investigar/corrigir o wiring do `billing_account` em si.

---

## 3. Verification results (PR1)

- `terraform fmt -check` — limpo.
- `terraform validate` (local, `-backend=false`) — limpo, após corrigir Achado #1.
- `terraform plan` **real** (local, contra o backend/estado reais de `brasil2036-dev`, credenciais
  próprias, só leitura) — **limpo, `Plan: 12 to add, 0 to change, 0 to destroy`**, incluindo os 3
  recursos novos de API habilitada, VPC+subnet+PSA, cluster+instância AlloyDB, secret+versão,
  senha aleatória. Nenhum erro, nenhuma mudança destrutiva.

---

## 4. Autonomous Decisions (PR1)

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | `network_config` block vs. campo raiz (achado real de schema) | (a) manter suposição do design; (b) corrigir pro schema real | (b) | `terraform validate` real rejeitou a suposição — corrigido antes de qualquer commit, mesma disciplina de nunca escrever em cima de suposição não verificada. |
| 2 | `availability_type` implícito vs. explícito | (a) deixar implícito (default da API); (b) `ZONAL` explícito | (b) | Auto-documentação + não depender de comportamento implícito que pode mudar entre versões do provider. |
| 3 | Senha inicial do AlloyDB: hardcoded vs. `random_password`+Secret Manager | (a) hardcoded (nunca — violaria "nunca commitar credenciais"); (b) gerada + Secret Manager | (b) | Único caminho compatível com `CLAUDE.md` ("nunca commitar credenciais, tokens, chaves ou segredos"). |

---

## 5. Blockers / trabalho restante

Nenhum blocker pro PR1. Trabalho restante desta fatia (PR2-PR4, ver `DESIGN §3`): motor de
autorização (`authz.py`), repositório AlloyDB (`alloydb_repo.py`), verificação de token Firebase
(`auth.py`), aplicação real nos 3 grupos de endpoint, colunas de organização em
`debtlab_scenarios`, seed das 2 organizações de teste, botão de login na landing, testes formais,
`ADR-062`, matriz completada.

---

## 6. Status transitions

Ainda não — status muda pra "Built" só depois do PR4 (matriz de teste completa), per
`sdd-build`/`sdd-ship`.

---

## 7. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-09 | 0.1 | PR1 (infra): VPC+PSA+AlloyDB+budget+deploy flags+IAM do `tf-deployer`. 4 achados reais durante o build (schema do `network_config`, `availability_type` explícito, IAM novo, `budget_amount_brl` sem confirmação de aplicação real). `terraform plan` real (read-only, credenciais próprias) limpo contra `brasil2036-dev`: 12 recursos a criar, 0 erro. | /build (Claude Sonnet 5) |
