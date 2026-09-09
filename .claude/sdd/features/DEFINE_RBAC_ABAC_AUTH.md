# DEFINE — RBAC_ABAC_AUTH

## Metadados

- **Feature:** RBAC_ABAC_AUTH
- **Status:** ✅ Complete (Designed)
- **Fase:** 1 (Define)
- **Entrada:** `.claude/sdd/features/BRAINSTORM_RBAC_ABAC_AUTH.md` (Ready for Define)
- **Criado:** 2026-09-09
- **Idioma:** PT-BR
- **Clarity score:** 13/15 (HIGH)
- **Branch:** a criar — `feature/rbac-abac-auth`
- **Próximo passo:** `/design .claude/sdd/features/DEFINE_RBAC_ABAC_AUTH.md`

> Nota: assets do plugin SDD ausentes — documento segue a lista de seções obrigatórias do skill
> `sdd-define`, mesmo padrão das fatias anteriores.

---

## 1. Problem statement

O projeto tem zero autenticação/autorização em qualquer camada (`EPIC-037`, `PRD-012`,
`ADR-029`/`ADR-030`, `SPEC-028` — todos decididos, nada implementado). A API é 100% pública, sem
distinção de quem faz a requisição, sem organização, sem auditoria de acesso. `ADR-004` (AlloyDB)
nunca foi provisionado em 9 fatias anteriores.

---

## 2. Target users

| Persona | Descrição | Pain point |
|---|---|---|
| **Usuário autenticado real** (primária) | Precisa de identidade real (login) pra que ações como criar cenário de simulação fiquem associadas a alguém, não anônimas | Hoje qualquer requisição é anônima — nenhum endpoint sabe quem está chamando |
| **Avaliador do concurso CGU / arquiteto do projeto** (secundária) | Quer ver o padrão "core determinístico" de segurança (`ADR-017`/`ADR-018`) aplicado também à camada de usuário humano, não só a agentes de código | Hoje a filosofia de permissão só existe pra agentes de código (`AGENTS.md`), nunca pra usuário humano real |

---

## 3. Goals (MoSCoW)

### MUST

- **G1.** Firebase Authentication real — e-mail/senha + Google Sign-In no mínimo; JWT válido
  verificável pelo backend.
- **G2.** AlloyDB provisionado (`ADR-004` realizado) — VPC nova + Private Services Access +
  conectividade Cloud Run→AlloyDB + cluster não-HA (2 vCPU/16GB de referência).
- **G3.** `budget_amount_brl` ajustado no Terraform pra valor realista (~R$1.800-2.000/mês).
- **G4.** Schema AlloyDB: usuários (referência ao Firebase UID), papéis, organizações (mínimo 2
  sintéticas de teste: "uniao"/"org-teste"), atribuição usuário↔organização↔papel, log de
  auditoria de autorização.
- **G5.** Motor de autorização genérico (role+organization+domain+data_classification+action+
  environment, `SPEC-028`) cobrindo a matriz completa dos 16 papéis (`ACCESS-PROFILES.md`) × 10
  ações (`PERMISSION-MATRIX.md`, completada pros 7 papéis que faltam hoje) — default deny.
- **G6.** Middleware FastAPI aplicando a política de verdade nos 3 grupos de endpoint já reais
  (`/v1/metrics/*`, `/v1/simulations/debtlab*`, `/v1/knowledge/ask`).
- **G7.** Isolamento real testado entre "uniao" e "org-teste" sobre o dado operacional novo desta
  fatia (cenários do DebtLab associados a usuário/organização).
- **G8.** Log de auditoria real e consultável (quem, quando, ação, resultado allow/deny),
  persistido em AlloyDB.
- **G9.** Botão de login na landing (`web/`), sem portal novo.

### SHOULD

- **G10.** Testes: unit do motor (matriz completa) + integration real contra AlloyDB + e2e do
  fluxo de login.
- **G11.** ADR novo formalizando a realização de `ADR-004` e a escolha de Firebase Auth.

### COULD

- **G12.** Ações sem subsistema real (FORECAST/PUBLISH/MANAGE_AGENT/MANAGE_MODEL/ADMIN_USERS do
  Admin Center) — política definida e testada isoladamente, sem endpoint real pra aplicar ainda.

---

## 4. Success criteria (mensuráveis)

| # | Critério | Medição |
|---|---|---|
| S1 | Login real funciona | Usuário consegue autenticar via Firebase Auth e obter um JWT válido, verificado ao vivo. |
| S2 | AlloyDB provisionado e alcançável | Cloud Run consegue conectar e ler/escrever no AlloyDB real, verificado ao vivo. |
| S3 | Autorização aplicada nos 3 grupos de endpoint reais | Requisição sem papel suficiente é negada (default deny); requisição com papel suficiente é permitida — testado contra os endpoints reais. |
| S4 | Isolamento multi-org real | Usuário de "uniao" não vê/edita cenário de "org-teste" e vice-versa, testado de verdade. |
| S5 | Auditoria real | Toda negação/allow privilegiado gera 1 linha real no log, consultável. |
| S6 | `budget_amount_brl` reflete o custo real | Valor ajustado no Terraform, aplicado via `infra.yml`. |
| S7 | `/verify-spec` PASS | Verificação independente (sessão nova, read-only) = OVERALL PASS. |
| S8 | `ci-gate` verde | Todo PR desta fatia passa pelo `ci-gate` sem gate enfraquecido. |

---

## 5. Acceptance tests

- **AT1 — login real.** *Given* um usuário novo, *When* autentica via Firebase Auth (e-mail/senha
  ou Google), *Then* recebe um JWT válido que o backend consegue verificar.
- **AT2 — AlloyDB alcançável.** *Given* a infra provisionada, *When* a API tenta uma query real
  contra AlloyDB, *Then* a conexão funciona (sem erro de rede/IAM).
- **AT3 — requisição sem papel suficiente é negada.** *Given* um usuário autenticado sem o papel
  necessário, *When* chama um dos 3 grupos de endpoint protegidos, *Then* recebe 403, e a negação
  é auditada.
- **AT4 — requisição com papel suficiente é permitida.** *Given* um usuário com o papel certo,
  *When* chama o mesmo endpoint, *Then* recebe o resultado normal (200), e o allow (se privilegiado)
  é auditado.
- **AT5 — isolamento multi-org real.** *Given* 2 usuários de organizações diferentes ("uniao"/
  "org-teste"), *When* um tenta acessar um cenário de DebtLab criado pelo outro, *Then* é negado.
- **AT6 — auditoria consultável.** *Given* qualquer allow/deny privilegiado, *When* consulto o log
  de auditoria, *Then* vejo quem, quando, ação e resultado — real, não fabricado.
- **AT7 — ações sem subsistema real ficam só na política.** *Given* uma ação como FORECAST (sem
  endpoint real), *When* inspeciono o motor de autorização, *Then* a política existe e é testada
  isoladamente, sem nenhum endpoint real tentando aplicá-la.
- **AT8 — `budget_amount_brl` real.** *Given* o Terraform aplicado, *When* inspeciono o alerta de
  orçamento no GCP, *Then* o valor reflete o custo real esperado (~R$1.800-2.000+), não R$50.
- **AT9 — ritual de CI completo.** *Given* qualquer PR desta fatia, *When* o CI roda, *Then*
  `ci-gate` resolve e bloqueia merge se qualquer gate falhar.

---

## 6. Out of scope

| Item | Motivo | Destino |
|---|---|---|
| MFA real (`SPEC-028`, `PRD-012` "MFA privileged", `EPIC-037` STORY-037.03) | Nenhuma ação privilegiada real tem endpoint real ainda pra exigir MFA — mesmo princípio de G6/G12. **Reconciliação com `PRD-012` §4 (lista MFA no "Escopo V1" do PRD):** o PRD é a visão de produto completa; esta fatia entrega a fundação de identidade+autorização que MFA vai precisar depois, mas adiar MFA em si é consistente com `PRD-012` §10 ("itens fora do escopo não são adicionados por conveniência técnica" — aqui é o inverso: não adicionar algo sem superfície real pra proteger). | Fatia futura, quando uma ação privilegiada real (Admin Center) existir. |
| Approval queue (`PRD-012` "approval queue", `ADR-019`/`ADR-020`) | Nenhuma ação irreversível/crítica real existe ainda que precise de aprovação — mesmo racional que MFA. Também nunca implementado nas 9 fatias anteriores. | Fatia futura, quando existir uma ação real que precise de four-eyes/approval. |
| Feature flags (`PRD-012` "feature flags") | Sem relação direta com autenticação/autorização em si — não foi discutido no `/brainstorm`, fica explicitamente fora por não ter sido pedido. | Reavaliar se `PRD-012` precisar disso como pré-requisito de uma fatia futura específica. |
| SSO corporativo (OIDC/SAML) | Tier pago do Firebase Auth, sem organização real que precise hoje. | Fatia futura, se uma organização real exigir. |
| Row/column-level security granular além de organização | Nenhum dado sensível/PII identificado que precise de mascaramento de coluna hoje. | Reavaliar se aparecer. |
| Construir Forecast Platform/Agent Center/Admin Center/Model Registry | Escopo de produto inteiro, não de autorização (ver Abordagem C do `/brainstorm`). | `EPIC-020`/`EPIC-026`/`EPIC-036`, fatias próprias. |
| Portal Executivo/Analítico com login | Sem UI de portal nesta fatia — só a API + botão de login. | `EPIC-034`/`EPIC-035`, fatias futuras. |
| Onboarding de organização real | As 2 organizações desta fatia são sintéticas de teste. | Fatia futura, quando houver organização real. |

---

## 7. Constraints

- **C1.** `budget_amount_brl` deve refletir o custo real do AlloyDB antes do merge — nunca deixar
  o alerta de orçamento 30x abaixo do custo real esperado.
- **C2.** Default deny — nenhuma requisição sem papel explícito suficiente é permitida por padrão.
- **C3.** Toda negação/allow privilegiado é auditado de verdade (`SPEC-028`), nunca fabricado.
- **C4.** As 2 organizações de teste nunca são apresentadas como instituições reais onboardadas.
- **C5.** Todo merge em `main` é via PR (branch protection).
- **C6.** Reusa `ci-gate`/gates já existentes, sem enfraquecer.

---

## 8. Assumptions / risk register

| ID | Afirmação | Impacto se falsa | Validada |
|---|---|---|---|
| A1 | O menor cluster AlloyDB viável (2 vCPU/16GB, não-HA) é suficiente pro volume de usuários/sessões esperado nesta fase do projeto | Se insuficiente, `/design` reavalia o tamanho da instância — não muda a decisão de provisionar, só o dimensionamento | ☑ (pesquisa real de custo já feita no brainstorm) |
| A2 | Cloud Run consegue alcançar AlloyDB via Direct VPC egress ou Serverless VPC Access connector sem latência/custo inaceitável | Se algum dos 2 mecanismos não funcionar bem, `/design` escolhe o outro — ambos são caminhos reais documentados pelo GCP | ☐ |
| A3 | Associar `organization_id` aos cenários do DebtLab é suficiente pra provar isolamento multi-org real, sem precisar de um 2º tipo de dado operacional | Se insuficiente, `/design` pode precisar de um 2º dado operacional simples só pra teste de isolamento | ☐ |
| A4 | Verificação de ID token do Firebase Admin SDK no FastAPI é o padrão certo (vs. sessão própria) | Se não for, `/design` escolhe outro mecanismo de verificação — decisão de implementação, não de escopo | ☐ |

---

## 9. Technical context

| Aspecto | Definição |
|---|---|
| **Onde vive** | `infra/terraform/` (+VPC, +Private Services Access, +AlloyDB, +budget ajustado), `api/src/api/` (+middleware de auth, +motor de autorização, +schema AlloyDB), `web/src/` (+botão de login, Firebase client SDK). |
| **Impacto IaC** | **Sim, o maior desta sessão:** VPC nova, Private Services Access, AlloyDB (cluster+instância), conectividade Cloud Run (Direct VPC egress ou Serverless VPC Access), ajuste de `budget_amount_brl`. |
| **Domínios de KB** | `SPEC-028` (Authorization), `PRD-012` (Admin/Access/Organizations), `ADR-029`/`ADR-030`/`ADR-004` (RBAC+ABAC, multi-org, AlloyDB — os 3 realizados/formalizados nesta fatia), `ADR-001`/`ADR-002` (GCP-native/serverless-first, motivo do achado de custo), `ADR-017`/`ADR-018` (precedente de filosofia de permissão, hoje só pra agentes de código). |

---

## 10. Clarity score breakdown

| Elemento | Nota | Máx | Observação |
|---|---|---|---|
| Problem | 3 | 3 | Gap real e verificado: zero auth em qualquer camada, `EPIC-037`/`PRD-012` já decididos mas nada implementado. |
| Users | 2 | 3 | Persona primária bem definida; persona secundária é papel/avaliador, não pessoa — mesmo padrão conservador das fatias anteriores. |
| Goals | 3 | 3 | 9 MUST, 2 SHOULD, 1 COULD; todos rastreáveis à descoberta do brainstorm, incluindo a reconciliação explícita com `PRD-012` (MFA/approval/feature flags adiados com motivo). |
| Success | 3 | 3 | S1-S8 com critérios verificáveis. |
| Scope | 2 | 3 | Out-of-scope bem povoado (8 itens, incluindo reconciliação com `PRD-012`), mas 4 assumptions reais (A1-A4) não totalmente validadas — dimensionamento de AlloyDB e mecanismo de conectividade Cloud Run↔AlloyDB são incertezas técnicas genuínas, só resolvidas no `/design`. |
| **Total** | **13** | **15** | **HIGH — prosseguir para `/design`.** |

---

## 11. Open questions

| ID | Questão | Resolver em |
|---|---|---|
| OQ1 | Serverless VPC Access connector vs. Direct VPC egress | `/design` |
| OQ2 | Tamanho definitivo da instância AlloyDB | `/design` |
| OQ3 | Completar `PERMISSION-MATRIX.md` pros 7 papéis que faltam | `/design` |
| OQ4 | Formato exato do token/sessão (Firebase Admin SDK vs. sessão própria) | `/design` |
| OQ5 | Mecanismo exato de teste de isolamento multi-org (cenários do DebtLab + `organization_id`) | `/design` |

---

## 12. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-09 | 1.0 | Criação a partir de `BRAINSTORM_RBAC_ABAC_AUTH.md`. Clarity 13/15. Reconciliação explícita com `PRD-012` (MFA/approval queue/feature flags adiados com motivo documentado). Status → Ready for Design. | /define (Claude Sonnet 5) |
