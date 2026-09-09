# DEFINE — LANDING_PAGE_TABS

## Metadados

- **Feature:** LANDING_PAGE_TABS
- **Status:** ✅ Complete (Built)
- **Fase:** 1 (Define)
- **Entrada:** `.claude/sdd/features/BRAINSTORM_LANDING_PAGE_TABS.md` (Ready for Define)
- **Criado:** 2026-09-09
- **Idioma:** PT-BR
- **Clarity score:** 14/15 (HIGH)
- **Branch:** a criar — `feature/landing-page-tabs`
- **Próximo passo:** `/design .claude/sdd/features/DEFINE_LANDING_PAGE_TABS.md`

> Nota: assets do plugin SDD ausentes — documento segue a lista de seções obrigatórias do skill
> `sdd-define`, mesmo padrão das fatias anteriores.

---

## 1. Problem statement

A landing page shipada (`LANDING_PAGE_ASTRO`) é 1 página de scroll único com 8 seções. O usuário
forneceu `Brasil_2036.pdf` — documento de contextualização da iniciativa com conteúdo real
(proposta, 7 indicadores fiscais/macro reais com fonte citada, cenários, roadmap detalhado) — e
pediu explicitamente uma reestruturação em abas: uma aba "Home" com os dados desse documento, e as
demais informações (já existentes e novas do PDF) distribuídas em outras abas.

---

## 2. Target users

| Persona | Descrição | Pain point |
|---|---|---|
| **Visitante da landing / avaliador do concurso CGU** (primária) | Quer entender rapidamente a proposta e a situação fiscal/econômica atual do Brasil sem rolar por 8 seções de conteúdo misto | Hoje tudo está em scroll único — proposta, dados, módulos, arquitetura e roadmap competem pela mesma tela sem hierarquia de navegação |
| **Usuário do projeto (dono do produto)** | Quer que a landing reflita o pitch já formalizado no documento de contextualização, com uma "porta de entrada" clara (Home) | Hoje a landing não tem o resumo fiscal/macro real (p.2 do PDF) em lugar nenhum |

---

## 3. Goals (MoSCoW)

### MUST

- **G1.** Barra de abas nova em `index.astro`: `Home` / `Dados Reais` / `Módulos & Portais` /
  `Arquitetura & Roadmap` / `Sobre` — client-side, 1 página só, sem migrar pra multi-rota.
- **G2.** Aba Home = proposta (`Hero`/`Proposal` migrados) + componente novo com os 7 cards
  fiscais/macro da p.2 do PDF, valores e citações reproduzidos literalmente.
- **G3.** Cada card fiscal cita a fonte real exata do PDF (Boletim Macrofiscal jul/2026 ou Prisma
  Fiscal ago/2026) + a ressalva de que é referência estática, sem confundir com dado do pipeline
  do projeto (`ADR-012`).
- **G4.** `DataPanel` (dado real via API do projeto) migra pra aba "Dados Reais", separado dos
  cards fiscais da Home — nunca misturados na mesma UI.
- **G5.** `ModuleGrid`+`PortalsGrid` migram pra aba "Módulos & Portais"; texto dos 3 cenários de
  referência (p.3 do PDF) incorporado nessa aba.
- **G6.** `Architecture`+`Roadmap` migram pra aba "Arquitetura & Roadmap"; seção de Acessos/
  Governança (p.4) + Evolução da landing page (p.5) + Questão central (p.6) incorporados nessa aba.
- **G7.** `Benefits` migra pra aba "Sobre"; Expectativas com a iniciativa (p.6) incorporado nessa
  aba.
- **G8.** Hash na URL sincronizado com a aba ativa (deep-link + refresh mantém a aba aberta).
- **G9.** Zero regressão de conteúdo/dado nas 6 seções migradas — mesmo texto, mesmos dados, só
  posição diferente; todo selo/evidência de `status.ts` continua passando sem alteração de
  comportamento.

### SHOULD

- **G10.** Acessibilidade básica das abas (ARIA roles, navegação por teclado).
- **G11.** e2e cobrindo a navegação entre abas (clique + hash direto na URL).

### COULD

- **G12.** Transição visual suave ao trocar de aba (não crítico pro MVP desta fatia).

---

## 4. Success criteria (mensuráveis)

| # | Critério | Medição |
|---|---|---|
| S1 | Home mostra a proposta + os 7 cards fiscais reais | Inspeção visual + teste automatizado: 7 cards presentes, cada um com valor+fonte do PDF. |
| S2 | Nenhum card fiscal é confundido com dado do pipeline | Cada card tem rótulo de fonte distinto do `DataPanel`; teste garante que a citação não é `metric_provenance`. |
| S3 | Navegação entre as 5 abas funciona | e2e: clique em cada aba mostra o conteúdo certo; hash direto na URL abre a aba certa. |
| S4 | Zero regressão nas 6 seções migradas | Testes e2e pré-existentes (`status.ts`, evidência) continuam passando sem alteração. |
| S5 | `/verify-spec` PASS | Verificação independente (sessão nova, read-only) = OVERALL PASS. |
| S6 | `ci-gate` verde | Todo PR desta fatia passa pelo `ci-gate` sem gate enfraquecido. |

---

## 5. Acceptance tests

- **AT1 — Home mostra proposta + 7 cards fiscais.** *Given* a landing carregada, *When* a aba Home
  está ativa (padrão), *Then* vejo a proposta do projeto e 7 cards com PIB/IPCA/Dívida Bruta-PIB
  2026/Dívida Bruta-PIB 2027/déficit primário/receita líquida/despesa total, cada um com valor e
  fonte reais do PDF.
- **AT2 — cards fiscais citam fonte distinta do pipeline.** *Given* a aba Home, *When* inspeciono
  a citação de cada card fiscal, *Then* a fonte é "Boletim Macrofiscal" ou "Prisma Fiscal" (texto
  do PDF), nunca uma URL de `metric_provenance`.
- **AT3 — Dados Reais preserva o `DataPanel` sem mudança de comportamento.** *Given* a aba "Dados
  Reais", *When* a página carrega, *Then* os mesmos dados reais via API que já apareciam na landing
  antes continuam aparecendo, sem alteração de fonte/valor.
- **AT4 — Módulos & Portais inclui os cenários.** *Given* a aba "Módulos & Portais", *When* a leio,
  *Then* vejo o grid de módulos, o grid de portais, e o texto dos 3 cenários de referência (Estresse/
  Tendencial/Brasil nos Trilhos).
- **AT5 — Arquitetura & Roadmap inclui acessos/governança/evolução/questão central.** *Given* a
  aba "Arquitetura & Roadmap", *When* a leio, *Then* vejo a arquitetura GCP, o roadmap de 8 fases,
  a seção de acessos/governança, a evolução da landing (5 versões) e a questão central.
- **AT6 — navegação por hash funciona.** *Given* uma URL com `#dados`, *When* carrego a página,
  *Then* a aba "Dados Reais" já abre ativa.
- **AT7 — zero regressão em testes e2e pré-existentes.** *Given* a suíte e2e já shipada
  (evidência de `status.ts`, cards com `data-evidence`), *When* rodo os testes, *Then* todos
  continuam passando.
- **AT8 — ritual de CI completo.** *Given* qualquer PR desta fatia, *When* o CI roda, *Then*
  `ci-gate` resolve e bloqueia merge se qualquer gate falhar.

---

## 6. Out of scope

| Item | Motivo | Destino |
|---|---|---|
| Migrar pra rotas Astro multi-página | Rejeitado explicitamente pelo usuário — abas client-side são suficientes. | Reavaliar se SEO por página virar prioridade real. |
| Conectar os 7 cards fiscais a uma API/pipeline real | Fora do pedido (conteúdo/UI, não ingestão de dado novo); exigiria descoberta real de uma fonte nova (Boletim Macrofiscal/Prisma Fiscal, formato, direito de uso). | `EPIC-008`/fatia de dado futura, se houver demanda real. |
| Aba nova só pra cenários/evolução da landing/questão central | Rejeitado explicitamente — conteúdo novo entra dentro das abas temáticas já desenhadas. | Reavaliar se o conteúdo crescer o suficiente. |
| Reescrever/expandir o conteúdo das 6 seções migradas | Esta fatia é reposicionamento estrutural, não reescrita de conteúdo já shipado. | Fatia futura de conteúdo, se pedida. |

---

## 7. Constraints

- **C1.** Mantém `output: "static"` (Astro) — 1 build, mesmo modelo de hospedagem (Cloud Run
  estático via `api-web.yml`).
- **C2.** Os 7 cards fiscais nunca citam `metric_provenance` nem qualquer fonte do pipeline do
  projeto como se fossem a mesma coisa (`ADR-012`).
- **C3.** `DataPanel` não muda de comportamento — só de posição (dentro da aba "Dados Reais").
- **C4.** Todo merge em `main` é via PR (branch protection).
- **C5.** Reusa `ci-gate`/gates já existentes, sem enfraquecer.

---

## 8. Assumptions / risk register

| ID | Afirmação | Impacto se falsa | Validada |
|---|---|---|---|
| A1 | O texto extraído do PDF nesta sessão (via leitura direta do arquivo) é fiel ao conteúdo real das 6 páginas, sem perda de valores/citações | Cards fiscais poderiam citar valor/fonte errados — mitigado por reproduzir literalmente o texto já extraído, não reparafrasear | ☑ (extração já feita e conferida nesta sessão) |
| A2 | O padrão de abas client-side não quebra nenhum teste e2e/mecanismo de evidência já existente (`status.ts`, `data-evidence`) | Se quebrar, precisa de ajuste de seletor nos testes existentes — mesmo padrão de achado real já visto em `LANDING_PAGE_ASTRO` PR2 | ☐ |
| A3 | Não há necessidade de nova entrada em `status.ts` pro conteúdo novo (cenários/acessos-governança/evolução/questão central) — é conteúdo narrativo, não item com badge de status | Se falsa, `/design` adiciona entradas novas em `status.ts` com evidência real | ☐ |

---

## 9. Technical context

| Aspecto | Definição |
|---|---|
| **Onde vive** | `web/src/pages/index.astro` (barra de abas + wiring), `web/src/components/` (+1 componente novo pros cards fiscais, migração de posição dos 8 existentes), `web/src/styles/global.css` (+estilos de abas), possivelmente `web/src/scripts/` ou inline `<script>` (JS mínimo de troca de aba). |
| **Impacto IaC** | Nenhum — só `web/`, mesmo pipeline de deploy (`api-web.yml`) já existente. |
| **Domínios de KB** | `ADR-058` (Astro), `ADR-012` (nunca fabricar — motiva G3/C2), `ADR-041` (Landing é produto de Fase 1); precedente direto em todos os componentes/testes já existentes de `web/`. |

---

## 10. Clarity score breakdown

| Elemento | Nota | Máx | Observação |
|---|---|---|---|
| Problem | 3 | 3 | Pedido explícito do usuário, com o PDF já lido e a tensão de fonte de dado já identificada e resolvida na descoberta. |
| Users | 2 | 3 | Persona primária bem definida (visitante/avaliador); persona secundária (dono do produto) é papel, não pessoa — mesmo padrão conservador das fatias anteriores. |
| Goals | 3 | 3 | 9 MUST, 2 SHOULD, 1 COULD; todos rastreáveis à descoberta do brainstorm, incluindo a resolução explícita da tensão de fonte (G3/G4). |
| Success | 3 | 3 | S1-S6 com critérios verificáveis. |
| Scope | 3 | 3 | Out-of-scope bem povoado (4 itens), todas as 3 assumptions reais já resolvidas ou com plano claro de validação no `/design`. |
| **Total** | **14** | **15** | **HIGH — prosseguir para `/design`.** |

---

## 11. Open questions

| ID | Questão | Resolver em |
|---|---|---|
| OQ1 | Texto exato dos cards fiscais — reproduzir literalmente ou adaptar levemente o tom (mantendo valor+fonte intactos) | `/design` |
| OQ2 | Posição visual da barra de abas (abaixo do `Nav` existente, substituindo-o, ou integrada) | `/design` |
| OQ3 | Padrão de acessibilidade das abas (ARIA roles, navegação por teclado) | `/design` |
| OQ4 | Confirmar se algum item do conteúdo novo precisa de entrada em `status.ts` (A3) | `/design` |

---

## 12. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-09 | 1.0 | Criação a partir de `BRAINSTORM_LANDING_PAGE_TABS.md`. Clarity 14/15. Status → Ready for Design. | /define (Claude Sonnet 5) |
