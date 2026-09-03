# /verify-spec — MVP_WALKING_SKELETON (SPEC-033)

- **Data:** 2026-09-03
- **Revisor:** subagente `code-reviewer` em contexto isolado (não construiu o código), read-only
- **Veredito:** ✅ **OVERALL PASS — com follow-ups obrigatórios**

## Matriz de requisitos (resumo)

| Faixa | Resultado |
|---|---|
| R1–R8 (PR1) | PASS (R5 com teste fraco; R8 é deviação sancionada por ADR-052) |
| R9 (infra só por Terraform) | **PARTIAL** → resolvido por **ADR-053** (WIF + serviços Cloud Run fora do TF, exposição pública declarada) |
| R10–R14 (PR2) | PASS |
| AT1–AT7, AT9, AT10 | PASS |
| AT8 (Terraform/WIF) | **PARTIAL** → ADR-053 declara a exposição pública |
| AT11 (ritual de CI) | **PARTIAL** → gates de integração real e spec-verifier são follow-up rastreado |

## Não-negociáveis do `CLAUDE.md`

Todos **PASS**: provenance preservada em toda resposta quantitativa (a API devolve 404 se não
houver linha de provenance); observed/estimated/simulated tipados em dados+API+UI (não é
disclaimer textual); zero credencial estática no repo (WIF + gitleaks); nenhuma métrica
oficial computada por LLM (`model='none'`); SQL não foi enfraquecido para passar teste
(`MERGE`→`CREATE OR REPLACE` tem driver técnico — buffer de streaming — documentado no `.sql`).

## Achados e disposição

| # | Achado | Disposição |
|---|---|---|
| 1 | Serviços Cloud Run fora do Terraform | **ADR-053** (aceito, exposição declarada) |
| 2 | Pool WIF em `bootstrap.sh`, não em `wif.tf` | **ADR-053** (chicken-egg); `wif.tf` = follow-up |
| 3 | CODEOWNERS com path errado + sem `infra/**`, `api/**`, `web/**`, `ingestion/contracts/**`, `docs/specs/**` | **corrigido** (`.github/CODEOWNERS` reescrito) |
| 4 | ADR-007 sem back-ref ao ADR-052 | **corrigido** (seção "Refinamentos" no ADR-007) |
| 5 | RAW bucket: SA com `storage.objectAdmin` | **corrigido** → `objectCreator` + `objectViewer` |
| 6 | `dataset_registry.source_url` vazio; card linka `resource_url` | OQ9 conhecido — confirmar URL do catálogo dados.gov.br (relevante p/ concurso CGU) |
| 7 | CI sem gate de integração real nem spec-verifier | **follow-up rastreado** em SPEC-033 §Follow-ups |
| 8–9 | Bronze `CREATE OR REPLACE` (não append); `parsing.py` espelha o SQL mas não é usado | info — sem ação nesta fatia |

## Conclusão

A fatia cumpre o objetivo — **cadeia de provenance provada ponta a ponta no ambiente vivo**.
Achados 3/4/5 corrigidos nesta rodada; 1/2 formalizados via ADR-053; 6/7 são follow-ups
rastreados. Nenhum não-negociável violado. **Liberado para `/ship`.**
