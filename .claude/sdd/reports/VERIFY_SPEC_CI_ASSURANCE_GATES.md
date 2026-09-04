# /verify-spec — CI_ASSURANCE_GATES (SPEC-031)

- **Data:** 2026-09-04
- **Revisor:** subagente `code-reviewer` isolado (não construiu o código), read-only
- **Veredito:** ✅ **OVERALL PASS**

## Resumo

- Mecanismo provado ao vivo: run verde do `ci.yml` no PR #1 com `web-check`/`terraform` corretamente **SKIPPED** e `integration` **SUCCESS em 1m7s** contra BigQuery real; run vermelho anterior onde `secret-scan` falho → `ci-gate` falho → PR bloqueado.
- Branch protection: `required_status_checks == [ci-gate]`. PR #1 `MERGEABLE`/`CLEAN`.
- `spec_verify` (8 testes) + run real contra SPEC-033 (PASS, 31 checks) confirmam que o verificador pega deliverable ausente, padrão proibido e `agent-eval` sem `reason`.
- Não-negociáveis do `CLAUDE.md`: **todos PASS** (WIF-only, nenhum gate rebaixado a warning, `spec_verify` é piso mecânico e não substitui o `/verify-spec` humano, contrato/provenance de produção intocados — `= 27` + `verify_chain.py` seguem no `data.yml` pós-merge).

## Achados e disposição

| # | Achado | Disposição |
|---|---|---|
| 1 (LOW-MED) | `ci-gate` não guardava o job `changes` — se `changes` quebrasse, todos os gates ficavam *skipped* e o `ci-gate` verde | **corrigido** — `changes` no `needs` + passo "changes must have run" que falha se `changes.result != success` |
| 2 (LOW) | PR de fork pula `integration`/`terraform` sem anotação | **corrigido** — job `fork-note` emite `::notice::` explicando que um mantenedor precisa rodar o CI de um branch do repo |
| 3 (LOW) | Sem `maximum_bytes_billed` nas queries de integração (R-012) | **residual aceito** — fixture de 6 linhas + TTL de 1h nos datasets `citest_*` ⇒ custo de frações de centavo; cap por query exigiria mexer no código de produção (`bigquery_io.run_sql`). Incremento futuro. |
| 4 (INFO) | Datasets `citest_<run>_*` (não `br2036_citest_*` do DEFINE) | consistente internamente (sweep casa `citest_`); documentado no DESIGN/BUILD |
| 5 (INFO) | Assert de completude = 3 (fixture), não 27 | deliberado (DESIGN §7.3); produção segue exigindo 27 no `verify_chain.py` |
| 6 (INFO) | `main` protegida só por CI (sem review obrigatório, CODEOWNERS advisory, admin não vinculado) | pré-existente (ADR-038); fora do escopo desta feature — anotar para o mantenedor |
| 7 (INFO) | Warnings de Node 20 deprecation nas actions | não bloqueia; bump agendado |

## Conclusão

Liberado para merge do PR #1 e `/ship`. Achados #1 e #2 corrigidos nesta rodada; #3/#6 são
residuais rastreados; #4/#5/#7 são info.
