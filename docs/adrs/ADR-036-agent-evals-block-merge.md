# ADR-036 — Agent evals block merge

## Status
Accepted

## Nota (2026-09-04)
Enquanto não houver comportamento de agente em produção, o gate `agent-eval` é declarado
`status: n/a` (com motivo) em `.github/ci/gates.yaml`, e `scripts/spec_verify.py` verifica que
essa declaração existe — a ausência do gate é explícita, não silenciosa. Quando um agente entrar,
mudar para `status: active` com um job real (ADR-054 / SPEC-031).

## Contexto
Esta decisão é parte do baseline arquitetural do BRASIL 2036 e deve ser lida com o `CONTEXTO.md`.

## Decision drivers
- segurança e auditabilidade;
- reprodutibilidade;
- escalabilidade;
- custo operacional;
- aderência ao GCP;
- clareza para portfólio e agentes de código.

## Alternativas consideradas
### A. Dashboard-only eval
Alternativa considerada e descartada por não equilibrar adequadamente os drivers acima.

### B. Nightly eval
Alternativa considerada; pode ser válida em outro contexto, mas aumenta risco, acoplamento ou complexidade para este projeto.

### C. Required eval gate for affected agent code
Alternativa escolhida ou base para a decisão.

## Decisão
**Required eval gate for affected agent code.**

## Por que
Risk without enforcement decays.

## Consequências positivas
- comportamento mais explícito e testável;
- decisão documentada para novos desenvolvedores/agentes;
- redução de ambiguidade.

## Consequências negativas / custo aceito
Eval flakiness must be managed.

## Verificação
A decisão deve aparecer em SPECs, testes, CI ou políticas de repositório quando aplicável.

## Quando reconsiderar
Reconsiderar quando métricas operacionais, requisitos legais, custo, escala ou limitações de plataforma demonstrarem que os decision drivers mudaram materialmente.
