# ADR-054 — Single CI merge-gate workflow with an aggregator required check

## Status
Accepted

## Contexto
Esta decisão é parte do baseline arquitetural do BRASIL 2036 e deve ser lida com o `CONTEXTO.md`.
`SPEC-031` exige que todo merge em `main` seja bloqueado por format/lint/typecheck/unit/
integration/contracts/security/Terraform/spec-verify verdes. Os workflows do repo
(`data.yml`, `api-web.yml`, `infra.yml`) são filtrados por path — um job de check filtrado
não pode ser um *required status check* porque um PR que não toca o path deixa o check
pendente ("Expected — waiting") para sempre. Confiar no comportamento "skipped required = pass"
da branch protection é frágil e pouco documentado.

## Decision drivers
- segurança e auditabilidade;
- reprodutibilidade;
- escalabilidade;
- custo operacional;
- aderência ao GCP;
- clareza para portfólio e agentes de código.

## Alternativas consideradas
### A. Jobs stub sempre-verdes por área
Considerada e descartada: duplica jobs e um stub que "passa" mascara ausência real de cobertura.

### B. Manter workflows separados e marcar cada check job como required
Considerada e descartada: é exatamente o deadlock de path filter que motiva esta ADR.

### C. Depender de "skipped required check = pass"
Considerada e descartada: comportamento não garantido entre mudanças do GitHub.

### D. Um workflow `ci.yml` guarda-chuva + job agregador `ci-gate`
Alternativa escolhida.

## Decisão
- **`.github/workflows/ci.yml`** roda em todo `pull_request` (para `main`) e `push` (em `main`),
  **sem filtro de path**.
- Um job `changes` (`dorny/paths-filter`) publica booleans por área; os jobs de gate
  (`lint-typecheck-unit`, `web-check`, `terraform`, `integration`, `spec-verify`, `secret-scan`)
  rodam condicionalmente à área correspondente (ou sempre, no caso de `spec-verify`/`secret-scan`).
- Um job **`ci-gate`** (`if: always()`, `needs` todos os anteriores) reprova **apenas** quando
  algum `needs.*.result` é `failure` ou `cancelled`; `success` e `skipped` passam.
- **`ci-gate` é o único required status check** da proteção de `main`.
- `data.yml` / `api-web.yml` / `infra.yml` perdem seus jobs de check (movidos para `ci.yml`) e
  mantêm apenas o job de deploy/apply, disparado em `push` → `main`.

## Por que
Um único contexto required que **sempre resolve** elimina o deadlock; a lógica de "o que
precisa rodar" fica concentrada no job `changes`; a decisão não depende de semântica de
*skipped*. A config de branch protection fica trivial (um contexto).

## Consequências positivas
- comportamento mais explícito e testável;
- decisão documentada para novos desenvolvedores/agentes;
- redução de ambiguidade;
- todo PR mostra o conjunto completo de gates.

## Consequências negativas / custo aceito
- `ci.yml` concentra muitos jobs — arquivo grande.
- Os workflows de deploy deixam de ter `needs:` nos jobs de check; passam a confiar que o PR
  foi gated (a `main` é protegida) e mantêm apenas um `pytest -q` rápido de pré-voo.

## Verificação
A decisão deve aparecer em SPECs, testes, CI ou políticas de repositório quando aplicável —
`SPEC-031` (realização), `.github/ci/gates.yaml`, `.github/workflows/ci.yml`, e a config de
`required_status_checks` da branch `main`.

## Quando reconsiderar
Reconsiderar quando o GitHub documentar de forma estável "skipped required = pass" (aí os jobs
podem ser required diretamente), ou quando `ci.yml` ficar grande demais para manter e valer a
pena dividir por linguagem/área com um agregador por grupo.
