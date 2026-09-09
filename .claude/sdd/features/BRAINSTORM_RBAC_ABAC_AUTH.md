# BRAINSTORM — RBAC_ABAC_AUTH

- **Feature:** RBAC_ABAC_AUTH
- **Status:** ✅ Complete (Defined)

- **Fase:** 0 (Brainstorm)
- **Criado:** 2026-09-09
- **Idioma:** PT-BR (alinhado a `docs/discovery/`)
- **Próximo passo:** `/define .claude/sdd/features/BRAINSTORM_RBAC_ABAC_AUTH.md`

> Nota: assets do plugin SDD ausentes — documento segue a lista de seções do skill
> `sdd-brainstorm`, mesmo padrão dos brainstorms anteriores.

---

## 1. Ideia

Próximo item da sequência já combinada com o usuário: RBAC/ABAC + portal autenticado
(`EPIC-037 — Access & Organizations`, `ADR-029`, `ADR-030`, `SPEC-028`). Hoje o projeto tem **zero
autenticação/autorização em qualquer camada** — a API (`api-runtime`) é 100% pública
(`CORS allow_origins=["*"]`, sem middleware de auth), a landing não tem login, e nenhuma tabela de
usuário/sessão existe. `EPIC-037` sozinho já cobre RBAC, ABAC, MFA, multi-org e row/column
security — maior que qualquer fatia única já shipada.

**Escopo consolidado ao longo da descoberta, por decisão explícita do usuário em cada
checkpoint — como em `DEBTLAB_SIMULATOR`, o usuário rejeitou repetidamente as simplificações
oferecidas:**
1. **Identidade real:** Firebase Authentication (serviço gerenciado GCP-native, `ADR-001`).
2. **Autorização real:** motor completo dos 16 papéis já nomeados em `ACCESS-PROFILES.md` × as 10
   ações de `PERMISSION-MATRIX.md` (role+organization+domain+data_classification+action,
   `SPEC-028`) — não uma versão reduzida a 2 papéis.
3. **Persistência:** `ADR-004` (AlloyDB) finalmente provisionado — 1ª vez em 9 fatias. Achado real
   de custo (pesquisa real, não suposta): o menor cluster AlloyDB viável (não-HA, dev) custa
   ~US$300/mês contínuo — 30x acima do `budget_amount_brl` (R$50) já configurado no Terraform.
   Confirmado com o usuário, com o achado explícito na mesa: `budget_amount_brl` é ajustado pra um
   valor realista (~R$1.800-2.000/mês) na mesma fatia.
4. **Multi-organização real:** testada com 2 organizações sintéticas explicitamente rotuladas como
   teste ("uniao", "org-teste") — nunca apresentadas como instituições reais onboardadas.
5. **Superfície de aplicação real:** a política completa (16×10) é definida e testada, mas só
   **aplicada de verdade** (middleware protegendo requisição real) nos 3 grupos de endpoint já
   shipados (`/v1/metrics/*`, `/v1/simulations/debtlab*`, `/v1/knowledge/ask`) — ações sem
   subsistema real ainda (FORECAST, PUBLISH, MANAGE_AGENT, MANAGE_MODEL, todo o Admin Center)
   ficam com a política definida e testada isoladamente, sem endpoint real pra aplicar. Isso evita
   o extremo oposto: construir Forecast Platform/Agent Center/Admin Center do zero só pra ter algo
   pra proteger.
6. **Sem portal novo:** a landing ganha um botão de login (Firebase Auth); nenhum Portal
   Executivo/Analítico/Admin Center é construído nesta fatia.

---

## 2. Contexto técnico

| Aspecto | Observação |
|---|---|
| **Estado atual de auth** | Zero — confirmado por leitura de `api/src/api/main.py` (CORS `allow_origins=["*"]`, nenhum middleware de auth) e ausência de qualquer tabela de usuário/sessão em `infra/terraform/*.tf` ou nos schemas já existentes. |
| **`ADR-029`/`SPEC-028` já decididos, sem detalhe de implementação** | `SPEC-028`: decision input = role, organization, domain, data_classification, action, environment; default deny; MFA pra ações privilegiadas; toda negação/allow privilegiado é auditável. `ADR-029`: RBAC + org/domain/classification/action (não RBAC puro, não ABAC puro). |
| **16 papéis já nomeados** | `docs/access/ACCESS-PROFILES.md`: Public, Viewer, Analyst, Economist, Simulator, Executive/Manager, Researcher, Data Steward, Data Engineer, ML Engineer, Agent Manager, Organization Admin, Platform Admin, Security Admin, Auditor/Compliance, API Consumer/Developer. |
| **Matriz baseline já esboçada** | `docs/access/PERMISSION-MATRIX.md`: 9 papéis × 10 ações (VIEW/EXPORT/FORECAST/SIMULATE/DRAFT/PUBLISH/MANAGE_AGENT/MANAGE_MODEL/ADMIN_USERS/SECURITY) — falta completar pros 16 papéis inteiros (7 papéis citados em `ACCESS-PROFILES.md` não aparecem na matriz ainda: Researcher, Data Steward, Data Engineer, Auditor/Compliance, API Consumer/Developer, e a distinção Viewer vs. Analyst). |
| **Custo real do AlloyDB (pesquisa real, `bytebase.com`)** | Menor cluster viável (2 vCPU/16GB, não-HA): ~US$257/mês compute + ~US$45/mês storage/backup ≈ **US$300/mês**. HA dobra o compute. Exige VPC nova + Private Services Access + (Serverless VPC Access connector ou Direct VPC egress) pro Cloud Run alcançar — nenhum desses recursos existe hoje em `infra/terraform/`. |
| **`budget_amount_brl` atual** | `infra/terraform/variables.tf`: `default = 50` (R$50/mês) — projetado pro custo baixo do MVP 100% serverless. Precisa de ajuste real nesta fatia. |
| **Endpoints reais já shipados que ganham enforcement** | `GET /v1/metrics/{metric_id}` e `/national` (VIEW), `GET /v1/provenance/{metric_id}` (VIEW), `POST /v1/simulations/debtlab` + `GET .../{scenario_id}` + `GET .../suggested-assumptions` (SIMULATE/VIEW), `POST /v1/knowledge/ask` (VIEW, classe READ). |
| **Ações sem subsistema real ainda** | FORECAST (sem endpoint de forecast, `EPIC-020` nunca iniciado), PUBLISH (sem workflow de publicação, `ADR-019`/`ADR-020` nunca implementados), MANAGE_AGENT (sem Agent Manager/Agent Center, `EPIC-026`), MANAGE_MODEL (sem registro de modelo), ADMIN_USERS pro Admin Center completo (`EPIC-036`, 11 stories, zero código). |

---

## 3. Discovery

| # | Pergunta | Resposta | Impacto no desenho |
|---|---|---|---|
| 1 | Qual provedor de identidade real? | **Firebase Authentication.** | Login real via SDK gerenciado; JWT verificado no FastAPI. |
| 2 | Escopo mínimo (2 papéis) ou RBAC completo (16 papéis) já nesta fatia? | **RBAC completo (16 papéis).** Usuário rejeitou a simplificação. | Motor de autorização cobre a matriz cheia desde o início, não incrementalmente. |
| 3 | Ações sem subsistema real (FORECAST/PUBLISH/MANAGE_AGENT/MANAGE_MODEL/Admin Center): construir os subsistemas, ou só definir a política sem aplicar? | **Política completa definida, aplicação real só onde já há endpoint.** | Evita o extremo de embutir Forecast Platform/Agent Center/Admin Center dentro desta fatia. |
| 4 | Qual portal ganha login primeiro? | **Nenhum portal novo — só proteger a API já real + botão de login na landing.** | Sem UI de portal nesta fatia; escopo fica em `api/`+`infra/`+1 botão em `web/`. |
| 5 | Onde persistir papel/organização/auditoria — BigQuery (padrão de sempre) ou finalmente provisionar AlloyDB? | **AlloyDB, mesmo com o achado real de custo (~US$300/mês, 30x o budget atual).** Usuário confirmou explicitamente após o achado ser exposto. | `ADR-004` realizado; `budget_amount_brl` ajustado no Terraform; VPC/Private Services Access/conector novos. |
| 6 | Multi-organização real testada, ou só o campo no esquema com 1 org? | **Multi-org completo, isolamento testado de verdade.** | Precisa de 2 organizações reais/sintéticas pra testar isolamento — não fica só no esquema. |
| 7 | Quem são as 2 organizações de teste? | **2 organizações sintéticas explicitamente rotuladas** ("uniao"/"org-teste"), nunca apresentadas como instituições reais onboardadas. | Evita implicar que um ministério/estado real já usa a plataforma. |

---

## 4. Inventário de amostras

| Tipo | Disponível? | Uso previsto |
|---|---|---|
| Papéis/ações já nomeados | Sim — `ACCESS-PROFILES.md`/`PERMISSION-MATRIX.md`, real, já no repo. | Base do motor de autorização; matriz precisa ser completada pros 16 papéis (hoje só 9 estão na tabela). |
| Endpoints reais a proteger | Sim — todos já shipados e em produção (`/v1/metrics/*`, `/v1/simulations/debtlab*`, `/v1/knowledge/ask`). | Pontos de enforcement real do middleware de autorização. |
| Custo real do AlloyDB | Sim — pesquisa real feita nesta sessão (bytebase.com, breakdown de compute/storage). | Base pro ajuste de `budget_amount_brl`; decisão de tamanho de instância (2 vCPU/16GB, não-HA) pra v1. |
| Precedente de auth/RBAC no projeto | Não — primeira vez. | `/design` desenha do zero o middleware FastAPI de verificação de JWT + política de autorização; sem KB específico de auth no projeto ainda. |
| Precedente de rede/VPC no projeto | Não — `infra/terraform/` hoje não tem nenhum recurso de rede (`grep` confirmado nesta sessão). | `/design` precisa desenhar a VPC/Private Services Access/conector do zero — descoberta real de qual abordagem (Serverless VPC Access vs. Direct VPC egress) fica pro `/design`. |

---

## 5. Abordagens exploradas

### Abordagem A — Firebase Auth + AlloyDB + RBAC/ABAC completo (16×10) + multi-org real, aplicado aos endpoints já reais ⭐ Escolhida
- **O quê:** login real via Firebase Auth; motor de autorização genérico (role+org+domain+
  classification+action) rodando contra dados persistidos em AlloyDB (finalmente provisionado);
  matriz completa dos 16 papéis; 2 organizações de teste provando isolamento real; middleware
  FastAPI aplicando a política nos 3 grupos de endpoint já shipados; log de auditoria de toda
  negação/allow privilegiado (`SPEC-028`).
- **Prós:** prova o padrão completo de autorização de uma vez, sem retrabalho incremental depois;
  resolve o débito de 9 fatias sem AlloyDB; multi-org testado de verdade, não só no esquema.
- **Contras:** escopo muito maior que qualquer fatia anterior — combina 3 capabilities novas
  inteiras (identidade, banco relacional operacional, motor de autorização) numa fatia só; custo
  real novo e substancial (~US$300/mês); infra de rede (VPC) nunca tocada antes no projeto.
- **Confiança:** 0.65 — cada peça individual é bem entendida (Firebase Auth é padrão de mercado,
  AlloyDB é documentado, a matriz já está esboçada), mas a combinação das 3 ao mesmo tempo, numa
  1ª fatia de um domínio inteiramente novo pro projeto, é o maior salto de escopo desta sessão.
  Descoberta real adicional (contagem exata de linhas por tabela de auditoria esperada, tamanho
  de instância AlloyDB definitivo, escolha entre Serverless VPC Access e Direct VPC egress) fica
  pro `/design`.

### Abordagem B — Login básico (2 papéis) + BigQuery + só 1 endpoint protegido
- **Por que não escolhida:** rejeitada explicitamente pelo usuário em múltiplos checkpoints —
  a simplificação foi oferecida como recomendação em cada uma das 3 decisões centrais (escopo de
  papéis, persistência, multi-org) e rejeitada nas 3.
- **Confiança:** 0.9 (mais simples e mais rápido de entregar) — mas não é a direção que o usuário
  quer.

### Abordagem C — Construir os subsistemas que faltam (Forecast/Publish/Agent Center/Admin Center) só pra ter algo real pra proteger com FORECAST/PUBLISH/MANAGE_AGENT/MANAGE_MODEL/ADMIN_USERS
- **Por que não escolhida:** rejeitada explicitamente na pergunta #3 — embutiria 4-5 fatias de
  produto inteiras (cada uma um `EPIC` próprio) dentro de uma fatia de autorização.
- **Confiança:** 0.3 (escopo essencialmente ilimitado, sem fronteira real).

---

## 6. Itens removidos / adiados (YAGNI)

| Item | Por que fora desta fatia | Vai para |
|---|---|---|
| MFA real (`SPEC-028`, `EPIC-037` STORY-037.03) | Nenhuma ação privilegiada real (ADMIN_USERS/SECURITY) tem endpoint real ainda pra exigir MFA — mesmo princípio de "só aplicar onde há superfície real" (item 5 do escopo consolidado). | Fatia futura, quando Admin Center ou uma ação privilegiada real existir. |
| SSO corporativo (OIDC/SAML) | Firebase Auth suporta, mas é tier pago/enterprise sem organização real que precise disso hoje. | Fatia futura, se uma organização real exigir SSO próprio. |
| Row/column-level security granular (`EPIC-037` STORY-037.05) além do escopo por organização | Nenhum dado sensível/PII identificado nas métricas já reais (todas são estatística oficial agregada) que precise de mascaramento de coluna — isolamento por `organization` já cobre o caso real conhecido. | Reavaliar se um dado real com necessidade de mascaramento aparecer. |
| Construir Forecast Platform/Agent Center/Admin Center/Model Registry | Ver Abordagem C — escopo de produto inteiro, não de autorização. | `EPIC-020`/`EPIC-026`/`EPIC-036`, fatias próprias futuras. |
| Portal Executivo/Analítico com login | Rejeitado explicitamente na pergunta #4 — sem UI de portal nesta fatia. | `EPIC-034`/`EPIC-035`, fatias futuras. |
| Onboarding de organização real (ministério/estado de verdade) | As 2 organizações desta fatia são sintéticas de teste, não uma parceria real. | Fatia futura, quando houver uma organização real pra onboardar. |

---

## 7. Requisitos-rascunho (para o `/define`)

- **R1.** Firebase Authentication configurado (e-mail/senha + Google Sign-In no mínimo); usuário
  autenticado recebe um JWT válido verificável pelo backend.
- **R2.** `infra/terraform/`: VPC nova + Private Services Access + (Serverless VPC Access
  connector ou Direct VPC egress, decisão do `/design`) + cluster AlloyDB (2 vCPU/16GB, não-HA) +
  instância primária — 1ª realização de `ADR-004`.
- **R3.** `budget_amount_brl` ajustado no Terraform pra um valor realista que cubra o custo real do
  AlloyDB (~R$1.800-2.000/mês) + o custo já existente — não pode ficar em R$50.
- **R4.** Schema em AlloyDB: usuários (referência ao Firebase UID), papéis por usuário, organizações
  (mínimo 2: "uniao", "org-teste"), atribuição usuário↔organização↔papel, log de auditoria de
  autorização (toda negação/allow privilegiado, `SPEC-028`).
- **R5.** Motor de autorização genérico em `api/` — decision input: role, organization, domain,
  data_classification, action, environment (`SPEC-028`); default deny; matriz completa dos 16
  papéis × 10 ações (`ACCESS-PROFILES.md`/`PERMISSION-MATRIX.md`, completada pros 7 papéis que
  faltam na matriz atual).
- **R6.** Middleware FastAPI aplicando a política de verdade nos 3 grupos de endpoint já reais
  (`/v1/metrics/*`, `/v1/simulations/debtlab*`, `/v1/knowledge/ask`) — cada ação sem subsistema
  real (FORECAST/PUBLISH/MANAGE_AGENT/MANAGE_MODEL/ADMIN_USERS-Admin-Center) tem a política
  testada isoladamente (unit test do motor), sem endpoint real pra aplicar ainda.
- **R7.** Isolamento real testado entre "uniao" e "org-teste" — um usuário de uma organização não
  acessa dado/cenário/sessão de outra (quando aplicável ao domínio — a maioria dos dados já reais
  é estatística pública nacional, não segmentada por organização; o teste de isolamento foca no
  dado operacional novo desta fatia, ex.: cenários do DebtLab associados a um usuário/organização).
- **R8.** Log de auditoria consultável (mínimo: quem, quando, ação, resultado allow/deny) — real,
  persistido em AlloyDB, não fabricado/simulado.
- **R9.** Landing (`web/`) ganha um botão de login (Firebase Auth client SDK) — sem portal novo,
  sem UI além do necessário pra autenticar e obter o token.
- **R10.** Testes: unit do motor de autorização (matriz completa, incluindo os casos sem endpoint
  real); integration real contra AlloyDB (conexão, schema, isolamento); e2e do fluxo de login na
  landing.
- **R11.** ADR novo formalizando a realização de `ADR-004` (AlloyDB provisionado) e a decisão de
  identidade (Firebase Auth) — sem superar nenhum ADR existente, só realizá-los.

---

## 8. Decisões autônomas registradas

| Decisão | Motivo |
|---|---|
| Nome da feature: `RBAC_ABAC_AUTH` | Reflete as 2 capabilities centrais (autorização + autenticação), não o detalhe de infra (AlloyDB) nem o item de backlog (`EPIC-037`) isoladamente. |
| Pesquisa real de custo do AlloyDB feita durante o brainstorm, não deixada pro `/design` | O achado (30x o budget configurado) é grande o suficiente pra mudar a decisão do usuário — trazido à mesa antes da confirmação final, não depois. |

---

## 9. Questões abertas (resolver no `/define` ou `/design`)

1. **Serverless VPC Access connector vs. Direct VPC egress** pro Cloud Run alcançar o AlloyDB —
   `/design` decide com base em custo/latência/simplicidade reais.
2. **Tamanho exato da instância AlloyDB** (2 vCPU/16GB é a referência de custo desta pesquisa; o
   `/design` confirma se isso é suficiente pro volume esperado de usuários/sessões).
3. **Completar a matriz `PERMISSION-MATRIX.md`** pros 7 papéis que faltam (Researcher, Data
   Steward, Data Engineer, Auditor/Compliance, API Consumer/Developer, e a distinção
   Viewer/Analyst) — trabalho de definição de política, não de infraestrutura, fica pro `/define`.
4. **Formato exato do token/sessão** entre Firebase Auth e o backend FastAPI (verificação de ID
   token do Firebase Admin SDK vs. sessão própria) — `/design`.
5. **Exato mecanismo de teste de isolamento multi-org** (que dado operacional novo desta fatia
   serve de prova — provavelmente associar `organization_id` aos cenários do DebtLab, já que
   `debtlab_scenarios` é o único dado operacional de usuário já real) — `/design`.

---

## 10. Domínios de KB para a Fase Define

- **PRDs:** `PRD-012` (Admin, Access, Organizations — a confirmar se cobre esta fatia ou é mais
  amplo).
- **SPECs:** `SPEC-028` (Authorization, já lido), `SPEC-029` (Admin — referenciado, não
  implementado nesta fatia).
- **ADRs:** `ADR-029` (RBAC+ABAC), `ADR-030` (multi-org tenancy), `ADR-004` (AlloyDB — realizado
  nesta fatia), `ADR-001`/`ADR-002` (GCP-native/serverless-first — motivo do achado de custo do
  AlloyDB precisar de decisão explícita), `ADR-017`/`ADR-018` (capability-based agent permissions/
  security by absence — precedente de filosofia de permissão já usado pros agentes de código,
  pode informar o motor de autorização de usuário).
- **Docs de acesso:** `docs/access/ACCESS-PROFILES.md`, `docs/access/PERMISSION-MATRIX.md` (ambos
  já lidos, base direta do motor).
- **Riscos:** `docs/risks/RISK-REGISTER.md`, `RISK-CONTROL-TEST-MATRIX.md` — checar controles já
  mapeados pra autenticação/autorização (provavelmente ainda sem teste real, primeira vez que a
  capability existe).
- **Backlog:** `EPIC-037` (Access & Organizations, todas as 5 stories tocadas por esta fatia em
  algum grau).
- **Precedente direto:** `api/src/api/main.py`/`bigquery_repo.py` (padrão de endpoint/dependency
  injection a estender com middleware de auth), `infra/terraform/cloud_run_services.tf` (padrão de
  IAM/service account já usado, a estender pro acesso do Cloud Run à AlloyDB).

---

## 11. Quality gate (Fase 0)

- [x] Mínimo de 3 perguntas de discovery feitas e respondidas (7 feitas)
- [x] Pergunta de amostras feita — papéis/ações/endpoints reais confirmados disponíveis; precedente
  de auth/rede confirmado como gap real, não suposto
- [x] Pelo menos 2 abordagens exploradas com trade-offs (A, B, C)
- [x] Usuário confirmou explicitamente a abordagem escolhida (A) em múltiplos checkpoints,
  incluindo depois de um achado real de custo que poderia ter mudado a decisão
- [x] YAGNI aplicado — seção de itens removidos preenchida (6 itens)
- [x] Mínimo de 2 validações incrementais concluídas (checkpoint do achado de custo do AlloyDB;
  checkpoint de confirmação final do desenho consolidado)
- [x] Domínios de KB identificados para o Define
- [x] Requisitos-rascunho prontos para o `/define` (R1–R11)

---

## 12. Handoff

Pronto para `/define .claude/sdd/features/BRAINSTORM_RBAC_ABAC_AUTH.md`.
