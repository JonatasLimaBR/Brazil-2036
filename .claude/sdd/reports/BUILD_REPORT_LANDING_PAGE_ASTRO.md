# BUILD REPORT — LANDING_PAGE_ASTRO

## Metadados

- **Feature:** LANDING_PAGE_ASTRO
- **Fase:** 3 (Build)
- **Entrada:** `.claude/sdd/features/DESIGN_LANDING_PAGE_ASTRO.md` (v1.0)
- **Branch:** PR1 `feature/landing-page-astro`
- **Data:** 2026-09-06
- **Status da build:** ✅ PR1 + PR2 completos — pronto para `/verify-spec`
- **Próximo passo:** `/verify-spec` (sessão nova, read-only) → `/ship`

> Assets do plugin SDD ausentes — relatório segue a lista de seções do skill `sdd-build`.

---

## 1. Task execution (PR1 — estrutura Astro + dados reais)

| # | Arquivo | Ação | Nota |
|---|---|---|---|
| 1 | `docs/adrs/ADR-058-landing-page-astro-supersedes-adr-051.md` | Create | Formaliza D1 |
| 2 | `docs/adrs/ADR-051-frontend-stack-vite-typescript-for-public-landing.md` | Modify | +nota "Superseded by ADR-058" (D2) |
| 3 | `web/package.json` | Modify | +`astro@5.18.2` (achado: pinado à última versão compatível com Node 20 — Astro 6+ exige Node ≥22.12, ver §4), +`@astrojs/check`, remove `vite` direto |
| 4 | `web/astro.config.mjs` | Create | `output: "static"`, `vite.envPrefix: ["VITE_"]` (D1, confirmado por pesquisa real) |
| 5 | `web/src/pages/index.astro` | Create | Página única (versão PR1: Nav+Hero+DataPanel) |
| 6 | `web/src/components/Nav.astro` | Create | Nav com âncoras |
| 7 | `web/src/components/Hero.astro` | Create | Hero + badges (texto literal do mockup) |
| 8 | `web/src/lib/metrics.ts` | Create | Consolida fetch de `main.ts`/`inss.ts`/`fiscal.ts` (D4) |
| 9 | `web/src/components/DataPanel.astro` | Create | Painel de dados reais (substitui Command Center fictício) |
| 10 | `web/src/main.ts`, `inss.ts`, `fiscal.ts`, `index.html` | Delete | Lógica migrada para `lib/metrics.ts` + `DataPanel.astro` + `index.astro` |
| 11 | `web/src/styles.css` → `web/src/styles/global.css` | Move+Modify | Paleta completa (verde/amarelo/azul) + classes novas (nav, hero, data-panel) |
| 12 | `web/tests/e2e/card.spec.ts` | Modify | Regex de bundle path ajustado (`assets/` → `_astro/`, achado real, ver §4) |
| 13 | `web/tsconfig.json` | Modify | `extends: "astro/tsconfigs/strict"` |
| 14 | `INDEX.md` | Modify | +ADR-058 |
| 15 | `web/nginx.conf` | Modify | Achado real não previsto no manifesto: regra de cache imutável apontava para `/assets/` (Vite), corrigida para `/_astro/` (Astro) — sem isso o header de cache de longo prazo nunca se aplicaria |
| 16 | `web/README.md` | Modify | Reflete a nova stack |
| 17 | `.gitignore` | Modify | +`web/.astro/` (cache gerado pelo Astro) |
| 18 | `web/src/vite-env.d.ts` | Modify | `/// <reference types="astro/client" />` em vez de `vite/client` |

---

## 1b. Task execution (PR2 — conteúdo com status real)

| # | Arquivo | Ação | Nota |
|---|---|---|---|
| 15 | `web/src/data/status.ts` | Create | 3 constantes tipadas (`MODULE_STATUS` 15, `ARCHITECTURE_STATUS` 12, `ROADMAP_PHASES` 8) com `evidence` obrigatório por entrada (D3), valores de `DESIGN §0.4/0.5/0.6` |
| 16 | `web/src/components/Proposal.astro` | Create | 4 cards (Integrar/Entender/Prever/Agir), texto literal de `docs/landpage.png` |
| 17 | `web/src/components/ModuleGrid.astro` | Create | 15 cards + selo de status a partir de `MODULE_STATUS`; cada card carrega `data-evidence` no DOM |
| 18 | `web/src/components/PortalsGrid.astro` | Create | 8 cards editoriais (nenhum portal real ainda) |
| 19 | `web/src/components/Architecture.astro` | Create | 12 componentes + selo a partir de `ARCHITECTURE_STATUS`, com `data-evidence` no DOM |
| 20 | `web/src/components/Roadmap.astro` | Create | 8 fases + selo a partir de `ROADMAP_PHASES`, com `data-evidence` no DOM |
| 21 | `web/src/components/Benefits.astro` | Create | 6 cards editoriais |
| 22 | `web/src/components/FooterCta.astro` | Create | CTA final + barra de rodapé, texto literal do mockup |
| 23 | `web/src/pages/index.astro` | Modify | Monta as 6 seções novas na página única |
| 24 | `web/tests/e2e/card.spec.ts` | Modify | +teste `evidence não-vazio` no DOM (`[data-evidence]`); corrige colisão de `getByText` com o novo card "Previdência & INSS" do grid de módulos (achado real, ver §2b) |

---

## 2. Achados técnicos durante o build (não previstos em detalhe pelo DESIGN)

### Achado #1 — versão do Astro precisa ser fixada contra a versão de Node do projeto

Astro 6.x e 7.x (mais recentes no npm) exigem Node ≥22.12.0. O projeto usa Node 20 tanto
localmente quanto em CI (`ci.yml`/`api-web.yml`, `node-version: "20"`) — bump de Node não está
no escopo desta fatia (é o follow-up já rastreado "bump de actions Node 20"). Resolvido fixando
`astro@5.18.2`, a última versão da série 5.x, compatível com `node: "18.20.8 || ^20.3.0 ||
>=22.0.0"` — confirmado via `npm view astro@5.18.2 engines` antes de instalar, não suposição.

### Achado #2 — regra de cache do nginx apontava para o diretório errado

`web/nginx.conf` tinha `location /assets/` com cache imutável de 1 ano — path do Vite. Astro
emite em `/_astro/`. Sem essa correção, o header de cache de longo prazo nunca seria aplicado
(silenciosamente, sem quebrar o site, só perdendo a otimização). Corrigido.

### Achado #3 — regex do teste e2e "sem valor hard-coded" dependia do path do Vite

Mesma causa raiz do achado #2, mas no teste: `card.spec.ts` procurava `src="...assets/...\.js"`.
Corrigido para `_astro/`, confirmado rodando o e2e de verdade contra a API real de produção.

---

## 2b. Achados técnicos durante o build de PR2

### Achado #4 — `spec-checks/SPEC-033.yaml` ainda referenciava `web/src/main.ts`

O gate mecânico `spec-verify` (SPEC-033) falhou no CI do PR1 (achado só visível em produção, não
localmente, já que `spec_verify.py` não roda no `npm run` local) porque checava a existência de
`web/src/main.ts` — arquivo legitimamente deletado por esta migração, sua lógica agora vive em
`web/src/lib/metrics.ts`. Corrigido apontando o check para o novo caminho; não é enfraquecer o
gate, é atualizar uma checagem mecânica para refletir uma mudança de arquitetura real e já
documentada (D4). Corrigido e mergeado antes do squash merge de PR1 (`ci-gate` ficou verde).

### Achado #5 — `ModuleGrid.astro` colidiu com um teste e2e pré-existente

O card "Previdência & INSS" do grid de módulos (PR2) tem o mesmo texto do `<h3>` do painel de
dados reais (PR1) — `getByText("Previdência & INSS")` no teste `INSS module renders...` passou a
resolver 2 elementos (strict-mode violation do Playwright). Corrigido escopando o locator a
`#dados-reais` (`page.locator("#dados-reais").getByText(...)`), sem alterar o que o teste
verifica — só reduz o escopo de busca ao painel de dados, que é a intenção original do teste.

---

## 3. Verification results (PR1)

- `npm run typecheck` (`astro check`) — **0 erros, 0 avisos, 0 dicas** (9 arquivos)
- `npm run build` (`astro build`) — gera `dist/` com sucesso, saída estática idêntica em formato à do Vite
- `npm run e2e` rodado **localmente contra a API real de produção**
  (`VITE_API_URL=https://br2036-api-gzt6fzwoda-rj.a.run.app`), não um preview sem backend
  (lição já aplicada desde a correção pós-INSS, PR #14 de uma fatia anterior): **4/4 passam**,
  incluindo a dívida renderizando valor real, INSS/fiscal renderizando os dados reais já
  carregados nas fatias anteriores, e a asserção de bundle sem valor hard-coded.
- Nenhuma mudança necessária em `.github/workflows/ci.yml`/`api-web.yml` — os nomes dos scripts
  npm (`typecheck`, `build`) não mudaram, só a implementação por trás deles.

---

## 3b. Verification results (PR2)

- `npm run typecheck` (`astro check`) — **0 erros, 0 avisos, 0 dicas** (16 arquivos)
- `npm run build` — gera `dist/` com sucesso
- `npm run e2e` rodado **localmente contra a API real de produção** — **5/5 passam**, incluindo o
  novo teste "every module, architecture and roadmap status badge carries non-empty evidence"
  (prova viva de C3/S3/G10: nenhum selo sem `evidence`)
- Verificação visual: screenshot full-page do preview local confirmada manualmente — todas as 10
  seções do mockup presentes, dados reais renderizando (dívida R$ 332.702.923.996 SP/2022, INSS
  emitidos/indeferidos reais, fiscal receita/despesa/primário reais em 2026-07), selos de status
  com cor coerente (verde=real, amarelo=parcial, cinza=planejado)

---

## 4. Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | Versão exata do Astro a instalar (DESIGN não especificou) | (a) última versão (7.x/6.x, exige Node ≥22); (b) última versão compatível com Node 20 do projeto | (b) `astro@5.18.2` | Bump de Node está fora de escopo desta fatia (follow-up já rastreado); confirmado via `npm view ... engines` antes de instalar, não suposição. |
| 2 | Corrigir `nginx.conf`/regex do e2e (achados #2/#3) não estavam no manifesto do DESIGN | (a) deixar para uma fatia futura; (b) corrigir agora, já que são consequência direta da própria migração | (b) corrigir agora | Deixar o cache imutável apontando pro path errado seria um regressão silenciosa de performance introduzida por esta própria fatia — corrigir é parte de "build/deploy funcional" (G5), não scope creep. |
| 3 | Estrutura de componentes Astro (1 arquivo por seção vs. tudo em `index.astro`) | (a) tudo num arquivo só; (b) 1 componente `.astro` por seção, `index.astro` só monta | (b) componentizado | Mesmo padrão de manutenibilidade já usado em `main.ts`/`inss.ts`/`fiscal.ts` (1 módulo por responsabilidade); facilita PR2 (adicionar componentes novos sem tocar nos existentes). |

---

## 5. Blockers / trabalho restante

Nenhum. PR1 e PR2 completos, verificados localmente contra a API real de produção. Segue para
`/verify-spec` (sessão nova, read-only) antes do `/ship`.

---

## 6. Status transitions

| Arquivo | Status | Próximo |
|---|---|---|
| `DEFINE_LANDING_PAGE_ASTRO.md` | ✅ Complete (Built) | `/verify-spec` → `/ship` |
| `DESIGN_LANDING_PAGE_ASTRO.md` | ✅ Complete (Built) | idem |

---

## 7. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-06 | 1.0 | PR1 completo: migração Astro, painel de dados reais, ADR-058. 3 achados técnicos de build corrigidos (versão do Astro, cache nginx, regex e2e). `typecheck`/`build`/`e2e` (4/4 contra API real de produção) verdes. | /build (Claude Sonnet 5) |
| 2026-09-06 | 1.1 | PR2 completo: `status.ts` (3 constantes, 35 entradas, `evidence` obrigatória) + 6 componentes editoriais/status-aware + `index.astro` monta as 10 seções. 2 achados corrigidos (`SPEC-033.yaml` apontava pro `main.ts` deletado; colisão de `getByText` entre `ModuleGrid` e `DataPanel`). `typecheck`/`build`/`e2e` (5/5, incluindo o novo teste de `evidence`) verdes contra API real de produção. Verificação visual por screenshot. Status → pronto para `/verify-spec`. | /build (Claude Sonnet 5) |
