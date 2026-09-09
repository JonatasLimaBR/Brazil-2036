# BUILD REPORT — LANDING_PAGE_TABS

## Metadados

- **Feature:** LANDING_PAGE_TABS
- **Fase:** 3 (Build)
- **Entrada:** `.claude/sdd/features/DESIGN_LANDING_PAGE_TABS.md` (Ready for Build)
- **Branch:** `feature/landing-page-tabs`
- **Data:** 2026-09-09
- **Status da build:** ✅ Shipped
- **Próximo passo:** `/verify-spec` (sessão nova, read-only) → `/ship`

---

## 1. Task execution

| # | Arquivo | Ação | Nota |
|---|---|---|---|
| 1 | `web/src/components/FiscalSnapshot.astro` | Create | 7 cards fiscais/macro reais (p.2 do PDF), fonte citada literalmente, sem `data-evidence`/`data-status-id` (não é claim de status de entrega, D2) |
| 2 | `web/src/components/Scenarios.astro` | Create | 3 cenários de referência (p.3) |
| 3 | `web/src/components/AccessGovernance.astro` | Create | Acessos/segurança/governança (p.4) |
| 4 | `web/src/components/LandingEvolution.astro` | Create | Evolução da landing (5 versões) + Questão central (p.5-6) |
| 5 | `web/src/components/Expectations.astro` | Create | Expectativas com a iniciativa (p.6) |
| 6 | `web/src/components/Nav.astro` | Modify | 6 links de âncora → 5 botões `role="tab"` (`tablist`); `<script>` inline de troca de aba (click + hash + teclado, WAI-ARIA APG) |
| 7 | `web/src/components/FooterCta.astro` | Modify | Remapeia `#dados-reais`→`#dados`, `#arquitetura`→`#arquitetura-roadmap` |
| 8 | `web/src/pages/index.astro` | Modify | Agrupa as 8 seções existentes + 5 novas em 5 `<div role="tabpanel">` |
| 9 | `web/src/styles/global.css` | Modify | Estilos de `tablist`/tab ativo, `.fiscal-card` (visualmente distinto de `.data-panel`), `.scenario-card`, `.access-list`, `.evolution-list`, `.central-question`, `.expectations-list` |
| 10 | `web/tests/e2e/card.spec.ts` | Modify | 3 testes passam a `page.goto("/#dados")` (achado real do `/design`, `§0`) |
| 11 | `web/tests/e2e/tabs.spec.ts` | Create | 4 testes: aba padrão, navegação por clique, deep-link por hash, cards fiscais com fonte não-pipeline |

---

## 2. Achados técnicos durante o build (não previstos em detalhe pelo DESIGN)

### Achado #1 — `getByText("Brasil hoje")` ambíguo entre 2 elementos

O 1º teste de `tabs.spec.ts` usava `page.getByText("Brasil hoje")`, que resolveu para 2 elementos:
o `<h2>` de `FiscalSnapshot` e o item "Versão 1: Marca + proposta + Brasil Hoje + histórico..."
de `LandingEvolution` (texto literal do PDF, p.5). Corrigido para
`getByRole("heading", { name: /Brasil hoje/i })`, que escopa só ao título.

### Achado #2 — testes e2e locais exigem `VITE_API_URL` real pra não dar falso-negativo

`npm run build` local, sem `VITE_API_URL`, produz um bundle que busca a API num caminho relativo
(`"" + "/v1/metrics/..."`) — contra o próprio servidor estático (`localhost:4173`), não a API real.
Isso fez os 3 testes de `card.spec.ts` (que dependem de dado real da API) falharem com
"element(s) not found" na 1ª rodada local, não por regressão real do código, mas por falta do env
var que só é setado no build de produção (`docker build --build-arg "VITE_API_URL=$API_URL"`,
`.github/workflows/api-web.yml`). Reproduzido corretamente rebuildando local com
`VITE_API_URL="https://br2036-api-gzt6fzwoda-rj.a.run.app" npm run build` — confirmado bundle
carrega a URL real; suíte completa (9/9) passou depois. Não é um achado que precisa de correção de
código — é uma nota de processo pra verificação local futura desta e de outras fatias de `web/`.

---

## 3. Verification results

- `npm run typecheck` (`astro check`) — 0 erros, 0 warnings, 0 hints (23 arquivos).
- `npm run build` — limpo, `output: "static"` preservado, 1 página gerada.
- `npx playwright test` (local, contra build com `VITE_API_URL` real) — **9/9 passed** (1.2min):
  4 novos (`tabs.spec.ts`) + 5 pré-existentes (`card.spec.ts`, incluindo os 3 que dependem de dado
  real da API e o teste de evidência/`[data-evidence]`) — **zero regressão**.

---

## 4. Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | `Nav.astro` existente vira a `tablist`, ou componente de abas novo separado | (a) componente novo; (b) reaproveitar `Nav.astro` | (b) | `Nav` já é sticky e já serve de navegação — duplicar a barra seria redundante sem necessidade real (confirmado no `/design §0`). |
| 2 | Organização do JS de troca de aba: inline em `Nav.astro` ou arquivo `.ts` separado | (a) arquivo separado; (b) inline | (b) | Escopo pequeno (1 função de ativação + listeners), sem necessidade real de um módulo `.ts` próprio pra esta fatia. |
| 3 | Testes `card.spec.ts` que dependem de `#dados-reais`: mudar seletor ou navegar direto pro hash | (a) mudar seletor pra clicar no botão da aba antes; (b) `page.goto("/#dados")` direto | (b) | Mais simples e testa também o deep-link por hash (que já é um requisito, AT6), sem precisar de um passo de clique extra em cada teste. |

---

## 5. Blockers / trabalho restante

Nenhum blocker. Nota de processo (não blocker): verificação e2e local desta fatia (e de qualquer
fatia futura de `web/` que dependa de dado real) precisa de `VITE_API_URL` setado manualmente pro
build local não dar falso-negativo — já documentado no Achado #2.

---

## 6. Status transitions

| Arquivo | Status | Próximo |
|---|---|---|
| `DEFINE_LANDING_PAGE_TABS.md` | ✅ Complete (Built) | `/verify-spec` → `/ship` |
| `DESIGN_LANDING_PAGE_TABS.md` | ✅ Complete (Built) | idem |

---

## 7. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-09 | 1.0 | Build completo: 5 componentes novos (conteúdo real do `Brasil_2036.pdf`), `Nav.astro` virou a `tablist` (5 abas), `index.astro` agrupado em `role="tabpanel"`, CSS de abas/cards novo, 3 testes e2e existentes corrigidos pra ativar a aba certa + 4 testes novos. 2 achados reais durante o build (locator ambíguo corrigido; nota de processo sobre `VITE_API_URL` local). `typecheck`/`build` limpos; e2e 9/9 PASS contra build com API real, 0 regressão. | /build (Claude Sonnet 5) |
