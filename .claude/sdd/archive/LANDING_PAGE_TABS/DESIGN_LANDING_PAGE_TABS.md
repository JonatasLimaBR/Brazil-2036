# DESIGN — LANDING_PAGE_TABS

## Metadados

- **Feature:** LANDING_PAGE_TABS
- **Status:** ✅ Shipped
- **Fase:** 2 (Design)
- **Entrada:** `.claude/sdd/features/DEFINE_LANDING_PAGE_TABS.md` (Ready for Design)
- **Criado:** 2026-09-09
- **Confiança:** 0.85
- **Próximo passo:** `/build .claude/sdd/features/DESIGN_LANDING_PAGE_TABS.md`

> Nota: assets do plugin SDD ausentes — documento segue a lista de seções do skill `sdd-design`,
> mesmo padrão dos designs anteriores.

---

## 0. Descoberta real

Antes de desenhar, inspecionado contra o código real (não suposto):

| Item | Verificado como | Resultado |
|---|---|---|
| Estrutura atual da landing | Leitura de `web/src/pages/index.astro`, todos os 8 componentes | 1 página, scroll único, `<Nav/><main><Hero/><DataPanel/><Proposal/><ModuleGrid/><PortalsGrid/><Architecture/><Roadmap/><Benefits/></main><FooterCta/>`. |
| `Nav.astro` já serve de navegação por âncora | Leitura direta | 6 links (`#visao-geral`,`#modulos`,`#arquitetura`,`#roadmap`,`#portais`,`#contato`) + 2 CTAs (`#roadmap`,`#dados-reais`) — resolve OQ2: o próprio `Nav` vira a barra de abas, não um componente novo. |
| IDs de seção que testes e2e referenciam diretamente | `grep` em `web/tests/e2e/card.spec.ts` | `#dados-reais`, `#card`, `#inss-module`, `#fiscal-module`, `[data-evidence]` (`ModuleGrid`/`Architecture`/`Roadmap`). |
| `DataPanel` busca dado real independente de visibilidade CSS | Leitura de `DataPanel.astro` | `<script>import { renderMetricsPanel } from "../lib/metrics"; void renderMetricsPanel();</script>` roda incondicionalmente no load — `fetch()` não é bloqueado por `hidden`/`display:none` no elemento pai. Confirma que esconder a aba "Dados Reais" por padrão não atrasa o carregamento do dado real. |
| **Achado real que exige mudança nos testes e2e (resolve A2 do `DEFINE`)** | Leitura de `card.spec.ts` | 3 dos 4 testes usam `expect(locator).toBeVisible()` sobre elementos dentro de `#dados-reais` (`#card`, `[data-testid="inss-*"]`, `[data-testid="fiscal-*"]`) — Playwright `toBeVisible()` falha se o elemento estiver `hidden`. Como a aba "Dados Reais" não é a aba padrão (Home é), esses 3 testes vão quebrar se não forem atualizados pra ativar a aba certa antes de afirmar visibilidade. O 4º teste (`[data-evidence]`, sem `toBeVisible()`) e o teste de bundle (via `request.get`, não `page`) não dependem de visibilidade — não precisam mudar. |
| `FooterCta`/`Proposal`/`Benefits` — ids e position fora de `<main>` | Leitura direta | `FooterCta` fica fora de `<main>` (sempre visível, independente da aba) — mantido assim, é rodapé constante. `Proposal`/`Benefits` não têm `id` próprio — sem risco de colisão ao agrupar em painéis de aba. |

---

## 1. Arquitetura

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                    index.astro (1 página, output: static)                │
├──────────────────────────────────────────────────────────────────────────┤
│  <Nav>                                                                    │
│    role="tablist": [Home] [Dados Reais] [Módulos & Portais]              │
│                     [Arquitetura & Roadmap] [Sobre]                      │
│    <script> tabs.ts (inline): click/hash → mostra 1 painel, esconde      │
│    os outros (`hidden`), sincroniza `location.hash`, seta `aria-selected`│
│  </Nav>                                                                   │
│                                                                            │
│  <main>                                                                   │
│    <div id="tab-home" role="tabpanel">      <Hero/> <FiscalSnapshot/>    │
│    <div id="tab-dados" role="tabpanel" hidden>  <DataPanel/>             │
│    <div id="tab-modulos-portais" hidden>    <ModuleGrid/> <PortalsGrid/> │
│                                              <Scenarios/>                 │
│    <div id="tab-arquitetura-roadmap" hidden><Architecture/>              │
│                                              <AccessGovernance/>          │
│                                              <Roadmap/>                   │
│                                              <LandingEvolution/>          │
│    <div id="tab-sobre" hidden>              <Benefits/> <Expectations/>  │
│  </main>                                                                  │
│                                                                            │
│  <FooterCta/>  -- fora de <main>, sempre visível, independe da aba       │
└──────────────────────────────────────────────────────────────────────────┘
```

`Proposal.astro` entra dentro de `<div id="tab-home">`, junto de `Hero`/`FiscalSnapshot`.

---

## 2. Decisões (ADRs inline)

### Decisão D1 — Abas client-side numa página só, `Nav` já existente vira a `tablist`

| Atributo | Valor |
|---|---|
| **Status** | Accepted |
| **Data** | 2026-09-09 |

**Contexto:** a landing precisa de navegação por abas sem perder `output: "static"`/1 build.

**Escolha:** os 6 links de `Nav.astro` viram 5 botões `role="tab"` (`tablist`); cada grupo de
seções em `index.astro` vira um `<div role="tabpanel" hidden>`; JS inline mínimo alterna
`hidden`+`aria-selected`+`location.hash`.

**Alternativas rejeitadas:** multi-rota Astro (rejeitada no `/brainstorm` — mudaria o modelo de
URL sem necessidade real); componente de nav novo separado do `Nav` existente (rejeitado por
duplicar a barra sticky já existente sem necessidade).

**Consequências:** zero mudança de hosting/build; 3 testes e2e existentes precisam ativar a aba
certa antes de afirmar visibilidade (achado real, `§0`).

### Decisão D2 — Os 7 cards fiscais nunca reusam o componente/estilo do `DataPanel`

| Atributo | Valor |
|---|---|
| **Status** | Accepted |
| **Data** | 2026-09-09 |

**Contexto:** os 7 números da p.2 do PDF (Boletim Macrofiscal/Prisma Fiscal) são reais, mas de uma
fonte diferente da que o pipeline do projeto ingere — confundi-los com o `DataPanel` violaria
`ADR-012`.

**Escolha:** componente novo (`FiscalSnapshot.astro`), visualmente distinto do `.data-panel`
(cor/borda própria), cada card com `<p class="fiscal-card__source">` citando literalmente a fonte
do PDF + a ressalva "Referência de agosto/2026 — atualização automática prevista para versões
futuras da plataforma" (paráfrase mínima da frase do PDF, mantendo o sentido exato). Nenhum campo
`data-evidence`/`data-status-id` (não é claim de status de entrega do projeto — é citação direta
de um documento externo).

**Consequências:** 2 "tipos de real" na landing, cada um com seu próprio rótulo visual — nunca
misturados na mesma seção.

---

## 3. Manifesto de arquivos

| # | Arquivo | Ação | Propósito | Agente | Dependências |
|---|---|---|---|---|---|
| 1 | `web/src/components/FiscalSnapshot.astro` | Create | 7 cards fiscais/macro (D2) | (general) | Nenhuma |
| 2 | `web/src/components/Scenarios.astro` | Create | 3 cenários de referência (p.3 do PDF) | (general) | Nenhuma |
| 3 | `web/src/components/AccessGovernance.astro` | Create | Acessos/segurança/governança (p.4) | (general) | Nenhuma |
| 4 | `web/src/components/LandingEvolution.astro` | Create | Evolução da landing (5 versões) + Questão central (p.5-6) | (general) | Nenhuma |
| 5 | `web/src/components/Expectations.astro` | Create | Expectativas com a iniciativa (p.6) | (general) | Nenhuma |
| 6 | `web/src/components/Nav.astro` | Modify | Vira a `tablist`; 5 botões `role="tab"`; `<script>` de troca de aba | (general) | 1-5 (hrefs apontam pros ids das divs de aba) |
| 7 | `web/src/components/FooterCta.astro` | Modify | Remapeia `#dados-reais`→`#dados`, `#arquitetura`→`#arquitetura-roadmap` | (general) | 6 |
| 8 | `web/src/pages/index.astro` | Modify | Agrupa as seções em 5 `<div role="tabpanel">` | (general) | 1-7 |
| 9 | `web/src/styles/global.css` | Modify | Estilos de `tablist`/`tab`/`tabpanel`, `.fiscal-card`, `.scenario-card`, etc. | (general) | Nenhuma |
| 10 | `web/tests/e2e/card.spec.ts` | Modify | 3 testes passam a `page.goto("/#dados")` antes de afirmar visibilidade (achado real `§0`) | (general) | 6, 8 |
| 11 | `web/tests/e2e/tabs.spec.ts` | Create | Navegação por clique + deep-link por hash (AT6/G11) | (general) | 6, 8 |

Nenhum arquivo de `api/`/`ingestion/`/`infra/` — fatia 100% `web/`.

---

## 4. Padrões de código

### 4.1 `index.astro` (esqueleto real)

```astro
---
import AccessGovernance from "../components/AccessGovernance.astro";
import Architecture from "../components/Architecture.astro";
import Benefits from "../components/Benefits.astro";
import DataPanel from "../components/DataPanel.astro";
import Expectations from "../components/Expectations.astro";
import FiscalSnapshot from "../components/FiscalSnapshot.astro";
import FooterCta from "../components/FooterCta.astro";
import Hero from "../components/Hero.astro";
import LandingEvolution from "../components/LandingEvolution.astro";
import ModuleGrid from "../components/ModuleGrid.astro";
import Nav from "../components/Nav.astro";
import PortalsGrid from "../components/PortalsGrid.astro";
import Proposal from "../components/Proposal.astro";
import Roadmap from "../components/Roadmap.astro";
import Scenarios from "../components/Scenarios.astro";
import "../styles/global.css";
---

<!doctype html>
<html lang="pt-BR">
  <head>...</head>
  <body>
    <div class="brand-bar"></div>
    <Nav />
    <main>
      <div id="tab-home" role="tabpanel" aria-labelledby="tab-btn-home">
        <Hero />
        <FiscalSnapshot />
        <Proposal />
      </div>
      <div id="tab-dados" role="tabpanel" aria-labelledby="tab-btn-dados" hidden>
        <DataPanel />
      </div>
      <div id="tab-modulos-portais" role="tabpanel" aria-labelledby="tab-btn-modulos-portais" hidden>
        <ModuleGrid />
        <PortalsGrid />
        <Scenarios />
      </div>
      <div id="tab-arquitetura-roadmap" role="tabpanel" aria-labelledby="tab-btn-arquitetura-roadmap" hidden>
        <Architecture />
        <AccessGovernance />
        <Roadmap />
        <LandingEvolution />
      </div>
      <div id="tab-sobre" role="tabpanel" aria-labelledby="tab-btn-sobre" hidden>
        <Benefits />
        <Expectations />
      </div>
    </main>
    <FooterCta />
  </body>
</html>
```

### 4.2 `Nav.astro` (esqueleto real — tablist + script)

```astro
---
const tabs = [
  { id: "home", label: "Home" },
  { id: "dados", label: "Dados Reais" },
  { id: "modulos-portais", label: "Módulos & Portais" },
  { id: "arquitetura-roadmap", label: "Arquitetura & Roadmap" },
  { id: "sobre", label: "Sobre" },
];
---

<header class="nav">
  <a class="nav__brand" href="#home">...</a>
  <ul class="nav__links" role="tablist">
    {tabs.map((t, i) => (
      <li>
        <button
          role="tab"
          id={`tab-btn-${t.id}`}
          aria-controls={`tab-${t.id}`}
          aria-selected={i === 0 ? "true" : "false"}
          data-tab-target={t.id}
        >
          {t.label}
        </button>
      </li>
    ))}
  </ul>
  <a class="nav__cta nav__cta--secondary" href="#arquitetura-roadmap">Ver Roadmap</a>
  <a class="nav__cta" href="#dados">Explorar Plataforma</a>
</header>

<script>
  const TABS = ["home", "dados", "modulos-portais", "arquitetura-roadmap", "sobre"];

  function activate(tabId: string): void {
    if (!TABS.includes(tabId)) tabId = "home";
    for (const id of TABS) {
      const panel = document.getElementById(`tab-${id}`);
      const btn = document.getElementById(`tab-btn-${id}`);
      if (panel) panel.hidden = id !== tabId;
      if (btn) btn.setAttribute("aria-selected", String(id === tabId));
    }
  }

  function fromHash(): string {
    return window.location.hash.replace("#", "") || "home";
  }

  document.querySelectorAll<HTMLButtonElement>("[data-tab-target]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.tabTarget!;
      window.location.hash = id;
    });
  });

  window.addEventListener("hashchange", () => activate(fromHash()));
  // Keyboard: seta esquerda/direita move o foco entre abas (WAI-ARIA APG tabs pattern, G10).
  const tablist = document.querySelector('[role="tablist"]');
  tablist?.addEventListener("keydown", (e: KeyboardEvent) => {
    const buttons = Array.from(
      document.querySelectorAll<HTMLButtonElement>("[data-tab-target]")
    );
    const idx = buttons.findIndex((b) => b === document.activeElement);
    if (idx === -1) return;
    if (e.key === "ArrowRight") buttons[(idx + 1) % buttons.length]?.focus();
    if (e.key === "ArrowLeft") buttons[(idx - 1 + buttons.length) % buttons.length]?.focus();
  });

  activate(fromHash());
</script>
```

`TABS`/`activate`/`fromHash` ficam duplicados textualmente entre a leitura acima e o arquivo real
só se o `/build` decidir inline puro; se preferir, extrair pra `web/src/scripts/tabs.ts` e importar
— decisão de organização de arquivo, não de comportamento, fica pro `/build`.

### 4.3 `FiscalSnapshot.astro` (esqueleto real — D2)

```astro
---
const cards = [
  { label: "PIB — projeção 2026", value: "+2,3%", source: "SPE/MF — Boletim Macrofiscal de julho/2026" },
  { label: "IPCA — projeção 2026", value: "5,1%", source: "SPE/MF — Boletim Macrofiscal de julho/2026" },
  { label: "Dívida Bruta/PIB — 2026", value: "83,0%", source: "Prisma Fiscal — agosto/2026" },
  { label: "Dívida Bruta/PIB — 2027", value: "86,77%", source: "Prisma Fiscal — agosto/2026" },
  { label: "Déficit primário Gov. Central 2026", value: "R$ 59,145 bi", source: "Mediana Prisma Fiscal — agosto/2026" },
  { label: "Receita líquida 2026", value: "R$ 2,574 tri", source: "Mediana Prisma Fiscal — agosto/2026" },
  { label: "Despesa total 2026", value: "R$ 2,624 tri", source: "Mediana Prisma Fiscal — agosto/2026" },
];
---

<section id="brasil-hoje" class="fiscal-snapshot">
  <h2 class="section-title">Brasil hoje — contexto econômico e fiscal</h2>
  <p class="fiscal-snapshot__note">
    Valores de referência de agosto de 2026. Em versões futuras da plataforma, estes indicadores
    serão atualizados automaticamente pelas fontes oficiais.
  </p>
  <div class="fiscal-grid">
    {cards.map((c) => (
      <article class="fiscal-card">
        <h3>{c.label}</h3>
        <p class="fiscal-card__value">{c.value}</p>
        <p class="fiscal-card__source">{c.source}</p>
      </article>
    ))}
  </div>
</section>
```

---

## 5. Estratégia de testes

| Tipo | Escopo | Cobre |
|---|---|---|
| e2e (`card.spec.ts`, modificado) | 3 testes passam a `page.goto("/#dados")` (ativa a aba certa via hash antes de afirmar `toBeVisible()`) | AT3, evita regressão (achado real `§0`) |
| e2e (`card.spec.ts`, inalterado) | Teste de evidência (`[data-evidence]`) e teste de bundle (`request.get`) — não dependem de visibilidade | AT7 |
| e2e (`tabs.spec.ts`, novo) | Clique em cada um dos 5 botões de aba → painel certo visível, outros `hidden`; `page.goto("/#dados")` abre direto na aba certa; aba padrão sem hash é "Home" | AT1, AT4-AT6 |
| Inspeção manual | Conferir os 7 cards fiscais contra o PDF (valor+fonte exatos) | AT1, AT2 |
| Manual (build local) | `npm run typecheck`/`build` limpos | S5 (junto ao `ci-gate`) |

Cobre todos os acceptance tests da DEFINE (AT1-AT8 — AT8 é o ritual de CI, coberto pelo `ci-gate`
já existente).

---

## 6. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-09 | 1.0 | Criação a partir de `DEFINE_LANDING_PAGE_TABS.md`. Descoberta real (§0): `Nav.astro` já serve de navegação e vira a `tablist` (resolve OQ2); achado real de que 3 testes e2e existentes quebrariam sem ativar a aba certa antes de afirmar visibilidade (resolve A2); `DataPanel` confirmado como não bloqueado por `hidden` no carregamento de dado real. 2 decisões inline (D1-D2). Manifesto de 11 itens. Status → Ready for Build. | /design (Claude Sonnet 5) |
