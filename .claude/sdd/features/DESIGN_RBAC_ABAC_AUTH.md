# DESIGN — RBAC_ABAC_AUTH

## Metadados

- **Feature:** RBAC_ABAC_AUTH
- **Status:** Ready for Build
- **Fase:** 2 (Design)
- **Entrada:** `.claude/sdd/features/DEFINE_RBAC_ABAC_AUTH.md` (Ready for Design)
- **Criado:** 2026-09-09
- **Confiança:** 0.6
- **Próximo passo:** `/build .claude/sdd/features/DESIGN_RBAC_ABAC_AUTH.md`

> Nota: assets do plugin SDD ausentes — documento segue a lista de seções do skill `sdd-design`,
> mesmo padrão dos designs anteriores. Confiança mais baixa que o normal (0.6) — reflete
> honestamente que esta é a fatia de maior escopo/risco de infra da sessão (1ª VPC, 1º banco
> relacional, 1ª autenticação real), não uma incerteza de requisito.

---

## 0. Descoberta real

| Item | Verificado como | Resultado |
|---|---|---|
| Recursos Terraform reais pra AlloyDB+rede | Pesquisa real (Google Cloud docs, Terraform Registry) | Confirmado: `google_compute_network`, `google_compute_global_address` (range reservado), `google_service_networking_connection` (Private Services Access — peering VPC↔serviço gerenciado do Google), `google_alloydb_cluster`, `google_alloydb_instance`. Existe também um módulo oficial (`GoogleCloudPlatform/alloy-db/google`), mas o fetch da página não retornou conteúdo completo (limitação de ferramenta, não do produto) — decisão: escrever os recursos base diretamente, não depender de um módulo cujo contrato exato não foi confirmado. |
| Cloud Run alcançando AlloyDB (Direct VPC egress vs. Serverless VPC Access) | Pesquisa real (`gcloud run deploy` docs) | Confirmado: `--network`/`--subnet` (subnet precisa ser `/26` ou maior) + `--vpc-egress`. **Default é `private-ranges-only`** — só tráfego pra IP privado (ex.: AlloyDB) passa pela VPC; tráfego público (BCB, Tesouro, Vertex AI/Gemini, Firebase Admin SDK) continua pela rota pública normal, sem precisar de Cloud NAT. Decisão: usar Direct VPC egress com `private-ranges-only` (não `all-traffic`, que exigiria NAT pra manter as chamadas públicas já existentes funcionando). |
| Verificação de token do Firebase no FastAPI | Pesquisa real (Firebase Admin SDK docs, exemplos reais) | Confirmado: pacote `firebase-admin` (PyPI, real), `firebase_admin.auth.verify_id_token(token)`; padrão real de integração com FastAPI via `fastapi.security.HTTPBearer` como dependency. Resolve OQ4. |
| Comportamento atual do papel "Public" na matriz já existente | Leitura de `docs/access/PERMISSION-MATRIX.md` | `Public`: VIEW=Y, EXPORT=public, SIMULATE=public-only — ou seja, a matriz **já prevê** que usuário anônimo pode ver e simular. Confirma que esta fatia não pode quebrar o comportamento público atual dos endpoints já reais (`/v1/metrics/*` sem token continua funcionando; `POST /v1/simulations/debtlab` sem token continua criando cenário, só sem "dono" real). |
| Onde `debtlab_scenarios` vive hoje | Releitura de `ADR-059` | BigQuery (`br2036_control`), não AlloyDB — decisão deliberada em `DEBTLAB_SIMULATOR`. **Achado real:** o teste de isolamento multi-org (G7/AT5) precisa então associar `organization_id`/`owner_uid` a uma tabela em **BigQuery**, e o lookup de papel/organização do usuário chamador vem de **AlloyDB** — 2 bancos diferentes na mesma verificação de autorização. Não uma incoerência: `metric_provenance`/dado quantitativo continua em BigQuery (`ADR-003`); identidade/papel/organização/auditoria é o dado genuinamente operacional que justificou o AlloyDB (`ADR-004`) nesta fatia. |

---

## 1. Arquitetura

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                              RBAC_ABAC_AUTH — v1                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  web/ (landing)                                                               │
│    Firebase Auth client SDK → botão de login → ID token (JWT)                │
│         │                                                                     │
│         ▼ Authorization: Bearer <token> (opcional -- Public segue sem token) │
│  api/ (Cloud Run, Direct VPC egress, --vpc-egress=private-ranges-only)        │
│    1. get_current_user() -- Firebase Admin SDK verifica o token se presente; │
│       ausente/inválido → papel "Public" implícito, nunca 401 nesse caso      │
│    2. require_permission(action, domain, classification) -- motor de authz:  │
│         busca papel(is)+organização do usuário em AlloyDB (se autenticado)   │
│         decide via matriz 16×10 (SPEC-028: role+org+domain+classification+   │
│         action+environment) -- default deny pra qualquer ação que a matriz   │
│         não liste como permitida pro papel corrente                          │
│    3. Se allow/deny é de ação PRIVILEGIADA → grava 1 linha real em           │
│       AlloyDB.authz_audit_log (quem, quando, ação, resultado)                │
│         │                                                                     │
│         ▼ (rede privada, Direct VPC egress)                                  │
│  VPC nova ("rbac-vpc") + subnet /26 + Private Services Access                │
│         │                                                                     │
│         ▼                                                                     │
│  AlloyDB (cluster não-HA, 2 vCPU/16GB) -- users, roles, organizations,       │
│    user_org_role, authz_audit_log                                            │
│                                                                                │
│  BigQuery br2036_control.debtlab_scenarios -- +organization_id, +owner_uid   │
│    (novo, aditivo) -- filtro de isolamento multi-org real no GET             │
│                                                                                │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Núcleo determinístico, sem fabricação (`ADR-013`/`ADR-012` aplicados aqui):** a decisão
allow/deny é 100% determinística (lookup + matriz), nunca decidida por um LLM; nenhum agente de
código tem ferramenta de escrita em `user_org_role`/papéis (mesmo princípio de
`AGENTS.md`/`ADR-017`/`ADR-018` já usado pra agentes, agora espelhado pra usuário humano).

---

## 2. Decisões (ADRs inline)

### Decisão D1 — AlloyDB real, não um simulacro em BigQuery (realiza `ADR-004`)

| Atributo | Valor |
|---|---|
| **Status** | Accepted |
| **Data** | 2026-09-09 |

**Contexto:** 9 fatias anteriores usaram BigQuery pra todo dado operacional, incluindo dado que
parecia "operacional" (cenários do DebtLab, `ADR-059`) mas era, na prática, pouco transacional
(escrita esporádica, leitura por ID).

**Escolha:** identidade/papel/organização/auditoria é dado genuinamente transacional (leitura em
toda requisição, escrita a cada mudança de papel/organização) — real o suficiente pra justificar
o custo fixo do AlloyDB, confirmado explicitamente pelo usuário após o achado real de custo
(~US$300/mês, pesquisa real) ser exposto.

**Consequências:** 1ª infra de rede (VPC) do projeto; `budget_amount_brl` precisa refletir o
custo real (D3).

### Decisão D2 — Direct VPC egress com `private-ranges-only`, não `all-traffic`

| Atributo | Valor |
|---|---|
| **Status** | Accepted |
| **Data** | 2026-09-09 |

**Contexto:** o Cloud Run da API já faz chamadas públicas reais (BCB SGS, Tesouro Transparente,
Vertex AI/Gemini, Firebase Admin SDK) que não podem parar de funcionar.

**Escolha:** `--vpc-egress=private-ranges-only` (default do Cloud Run) — só tráfego pra IP privado
(AlloyDB) atravessa a VPC; tráfego público continua pela rota pública normal.

**Alternativas rejeitadas:** `--vpc-egress=all-traffic` exigiria provisionar Cloud NAT só pra
manter as chamadas públicas já existentes funcionando — infra nova sem necessidade real.

**Consequências:** zero mudança de comportamento nas chamadas públicas já existentes; only a nova
chamada a AlloyDB usa a VPC.

### Decisão D3 — `budget_amount_brl` ajustado no mesmo PR que provisiona o AlloyDB

| Atributo | Valor |
|---|---|
| **Status** | Accepted |
| **Data** | 2026-09-09 |

**Escolha:** `infra/terraform/variables.tf`: `budget_amount_brl` de `50` pra `1800` (referência:
~US$300/mês × ~R$6/US$, com margem) — nunca deixar o alerta de orçamento defasado do custo real
entre o merge do AlloyDB e um ajuste "depois".

### Decisão D4 — Isolamento multi-org testado via `debtlab_scenarios` (BigQuery) + lookup de papel/org (AlloyDB)

| Atributo | Valor |
|---|---|
| **Status** | Accepted |
| **Data** | 2026-09-09 |

**Contexto:** `debtlab_scenarios` vive em BigQuery (`ADR-059`), não AlloyDB — o único dado
operacional de usuário já real no projeto.

**Escolha:** `debtlab_scenarios` ganha 2 colunas novas, aditivas (`organization_id`,
`owner_uid`, nulas pra linhas antigas — sem quebrar cenários já criados antes desta fatia).
`GET /v1/simulations/debtlab/{scenario_id}` passa a checar: se o cenário tem `organization_id`
preenchido, o usuário chamador precisa pertencer à mesma organização (lookup em AlloyDB) ou ser
`Platform Admin`; cenários sem organização (criados por usuário anônimo/Public, comportamento
atual preservado) continuam públicos, sem checagem.

**Consequências:** prova isolamento real sem inventar uma 2ª tabela operacional só pra teste;
mantém 100% de compatibilidade com cenários já reais criados nas fatias anteriores.

### Decisão D5 — Papel "Public" implícito nunca vira 401; autenticação é opcional nos endpoints já públicos

| Atributo | Valor |
|---|---|
| **Status** | Accepted |
| **Data** | 2026-09-09 |

**Contexto:** `PERMISSION-MATRIX.md` já define `Public: VIEW=Y, SIMULATE=public-only` — os
endpoints já reais são hoje 100% públicos e não podem parar de ser (regressão real de produto,
não só de teste).

**Escolha:** `get_current_user()` nunca lança 401 por ausência de token — resolve pro papel
`Public` implícito. Só uma ação que a matriz nega ao papel corrente (`Public` ou autenticado)
gera 403 real.

**Consequências:** AT3 (negação real) só é demonstrável com um papel que a matriz realmente nega
uma ação (não existe hoje um caso real de negação pra `Public` em VIEW/SIMULATE) — o `/build`
precisa achar/criar um caso real de negação genuína (ex.: um papel autenticado tentando
`ADMIN_USERS` sem ser `Organization Admin`/`Platform Admin`) pra provar o `default deny` de
verdade, não fabricar um cenário artificial.

---

## 3. Manifesto de arquivos

| # | Arquivo | Ação | Propósito | Agente | Dependências |
|---|---|---|---|---|---|
| 1 | `infra/terraform/network.tf` | Create | VPC (`rbac-vpc`) + subnet `/26` + `google_compute_global_address` (range reservado) + `google_service_networking_connection` (Private Services Access) | @ci-cd-specialist | Nenhuma |
| 2 | `infra/terraform/alloydb.tf` | Create | `google_alloydb_cluster` (não-HA) + `google_alloydb_instance` (primária, 2 vCPU/16GB) + IAM/Secret Manager pra credencial | @ci-cd-specialist | 1 |
| 3 | `infra/terraform/variables.tf` | Modify | `budget_amount_brl`: `50` → `1800` (D3) | (general) | Nenhuma |
| 4 | `.github/workflows/api-web.yml` | Modify | `gcloud run deploy` ganha `--network`/`--subnet`/`--vpc-egress=private-ranges-only` (D2) | @ci-cd-specialist | 1, 2 |
| 5 | `api/src/api/authz.py` | Create | Matriz 16×10 completa (`ACCESS-PROFILES.md`/`PERMISSION-MATRIX.md`, completada); função `decide(role, organization, domain, classification, action, environment) -> Allow/Deny`; default deny | (general) | Nenhuma |
| 6 | `api/src/api/alloydb_repo.py` | Create | Conexão real (driver `psycopg`), CRUD de `users`/`roles`/`organizations`/`user_org_role`; `write_audit_log()` | (general) | 2 |
| 7 | `api/src/api/auth.py` | Create | `get_current_user()` (Firebase Admin SDK, papel `Public` implícito se sem token, D5); `require_permission(action, domain, classification)` dependency factory | (general) | 5, 6 |
| 8 | `api/src/api/main.py` | Modify | Aplica `require_permission(...)` nos 3 grupos de endpoint já reais; `GET /v1/simulations/debtlab/{scenario_id}` ganha checagem de organização (D4) | (general) | 7 |
| 9 | `api/src/api/bigquery_repo.py` | Modify | `create_debtlab_scenario`/`get_debtlab_scenario` ganham `organization_id`/`owner_uid` (colunas aditivas, D4) | (general) | Nenhuma |
| 10 | `ingestion/scripts/seed_rbac_alloydb.py` | Create | Seed idempotente: 2 organizações de teste (`uniao`, `org-teste`), papéis, 1 usuário de teste por organização | (general) | 6 |
| 11 | `web/src/lib/auth.ts` | Create | Firebase client SDK — login/logout, obtenção do ID token | (general) | Nenhuma |
| 12 | `web/src/components/Nav.astro` | Modify | +botão de login/estado autenticado | (general) | 11 |
| 13 | `api/pyproject.toml` | Modify | +`firebase-admin`, +`psycopg[binary]` | (general) | Nenhuma |
| 14 | `api/tests/test_authz.py` | Create | Unit da matriz completa (16×10), incluindo casos reais de negação (D5) | (general) | 5 |
| 15 | `api/tests/integration/test_alloydb_auth.py` | Create | Integration real contra AlloyDB — conexão, seed, isolamento multi-org (D4) | (general) | 6, 9, 10 |
| 16 | `docs/adrs/ADR-062-alloydb-realized-and-firebase-auth.md` | Create | Formaliza D1-D5, realiza `ADR-004` | (general) | Nenhuma |
| 17 | `docs/access/PERMISSION-MATRIX.md` | Modify | Completa a matriz pros 7 papéis que faltam (OQ3) | (general) | Nenhuma |

**Ordem de build sugerida (risco decrescente de infra primeiro, mesmo padrão do `ADR-061`
D3 — infra spike isolada e verificada ao vivo antes de qualquer código de aplicação):**
PR1 = itens 1-4 (rede+AlloyDB+budget+deploy, verificado ao vivo: conexão real funciona, chamadas
públicas continuam funcionando) → PR2 = itens 5-10, 13 (motor+repo+seed) → PR3 = itens 8, 9, 11,
12 (aplicação real nos endpoints + landing) → PR4 = itens 14-17 (testes formais + ADR + matriz,
ainda que verificação já tenha ocorrido incrementalmente a cada PR).

---

## 4. Padrões de código

### 4.1 `authz.py` (esqueleto real)

```python
from enum import StrEnum


class Role(StrEnum):
    public = "public"
    viewer = "viewer"
    analyst = "analyst"
    economist = "economist"
    simulator = "simulator"
    executive_manager = "executive_manager"
    researcher = "researcher"
    data_steward = "data_steward"
    data_engineer = "data_engineer"
    ml_engineer = "ml_engineer"
    agent_manager = "agent_manager"
    organization_admin = "organization_admin"
    platform_admin = "platform_admin"
    security_admin = "security_admin"
    auditor_compliance = "auditor_compliance"
    api_consumer_developer = "api_consumer_developer"


class Action(StrEnum):
    view = "view"
    export = "export"
    forecast = "forecast"
    simulate = "simulate"
    draft = "draft"
    publish = "publish"
    manage_agent = "manage_agent"
    manage_model = "manage_model"
    admin_users = "admin_users"
    security = "security"


# ACCESS-PROFILES.md / PERMISSION-MATRIX.md, completada pros 16 papéis reais.
# Default deny: um papel ausente de _MATRIX[action] nunca é permitido.
_MATRIX: dict[Action, frozenset[Role]] = {
    Action.view: frozenset({Role.public, Role.viewer, Role.analyst, ...}),
    Action.simulate: frozenset({Role.public, Role.simulator, Role.economist, ...}),
    Action.admin_users: frozenset({Role.organization_admin, Role.platform_admin}),
    # ...
}


def decide(*, role: Role, action: Action) -> bool:
    return role in _MATRIX.get(action, frozenset())
```

### 4.2 `auth.py` (esqueleto real — D5)

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth as firebase_auth

from api.authz import Action, Role, decide

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> "CurrentUser":
    if creds is None:
        return CurrentUser(uid=None, role=Role.public, organization_id=None)
    try:
        decoded = firebase_auth.verify_id_token(creds.credentials)
    except Exception:
        # Token presente mas inválido -- ainda cai pro papel Public (D5), nunca 401
        # aqui: um token expirado não deve bloquear um endpoint já público.
        return CurrentUser(uid=None, role=Role.public, organization_id=None)
    role, org_id = alloydb_repo.lookup_role_and_org(decoded["uid"])
    return CurrentUser(uid=decoded["uid"], role=role, organization_id=org_id)


def require_permission(action: Action):
    async def dependency(user: CurrentUser = Depends(get_current_user)) -> "CurrentUser":
        allowed = decide(role=user.role, action=action)
        if _is_privileged(action):
            alloydb_repo.write_audit_log(user=user, action=action, allowed=allowed)
        if not allowed:
            raise HTTPException(status_code=403, detail="forbidden")
        return user

    return dependency
```

### 4.3 Terraform — rede + Private Services Access (esqueleto real)

```hcl
resource "google_compute_network" "rbac_vpc" {
  name                    = "rbac-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "rbac_subnet" {
  name          = "rbac-subnet"
  network       = google_compute_network.rbac_vpc.id
  region        = var.region
  ip_cidr_range = "10.10.0.0/26"
}

resource "google_compute_global_address" "private_services_range" {
  name          = "rbac-psa-range"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.rbac_vpc.id
}

resource "google_service_networking_connection" "psa" {
  network                 = google_compute_network.rbac_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_services_range.name]
}
```

---

## 5. Estratégia de testes

| Tipo | Escopo | Cobre |
|---|---|---|
| Unit (`api/tests/test_authz.py`) | Matriz completa (16×10), default deny explícito | G5, AT7 |
| Integration real (`api/tests/integration/test_alloydb_auth.py`) | Conexão real a AlloyDB, seed das 2 orgs de teste, isolamento real (D4) | AT2, AT5 |
| Manual/e2e | Login real via Firebase Auth na landing; requisição real com/sem token contra os 3 grupos de endpoint | AT1, AT3, AT4 |
| Verificação manual ao vivo (PR1) | Cloud Run alcança AlloyDB via Direct VPC egress; chamadas públicas (BCB/Tesouro/Vertex AI) continuam funcionando | AT2, D2 |
| Manual | `budget_amount_brl` aplicado reflete o alerta real no GCP | AT8 |

Cobre os acceptance tests da DEFINE (AT1-AT9 — AT9 é o ritual de CI, coberto pelo `ci-gate` já
existente).

---

## 6. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-09 | 1.0 | Criação a partir de `DEFINE_RBAC_ABAC_AUTH.md`. Descoberta real (§0): recursos Terraform reais confirmados pra VPC/AlloyDB; Direct VPC egress `private-ranges-only` escolhido pra não quebrar chamadas públicas já existentes; `firebase-admin`/`HTTPBearer` confirmado como padrão real de verificação; achado real de que `debtlab_scenarios` vive em BigQuery, não AlloyDB, exigindo D4. 5 decisões inline (D1-D5). Manifesto de 17 itens, com ordem de build sugerida (infra isolada primeiro, mesmo padrão do `ADR-061`). Confiança 0.6 (honesta — maior risco de infra da sessão). Status → Ready for Build. | /design (Claude Sonnet 5) |
