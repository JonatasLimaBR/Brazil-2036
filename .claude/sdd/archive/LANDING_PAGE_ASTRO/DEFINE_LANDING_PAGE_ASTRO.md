# DEFINE — LANDING_PAGE_ASTRO

## Metadados

- **Feature:** LANDING_PAGE_ASTRO
- **Status:** ✅ Shipped

> Shipped and archived 2026-09-07.
- **Fase:** 1 (Define)
- **Entrada:** `.claude/sdd/features/BRAINSTORM_LANDING_PAGE_ASTRO.md` (Ready for Define)
- **Criado:** 2026-09-06
- **Idioma:** PT-BR
- **Clarity score:** 13/15 (HIGH)
- **Branch:** a criar — `feature/landing-page-astro`
- **Próximo passo:** `/design .claude/sdd/features/DEFINE_LANDING_PAGE_ASTRO.md`

> Nota: assets do plugin SDD ausentes — documento segue a lista de seções obrigatórias do skill
> `sdd-define`, mesmo padrão das fatias anteriores.

---

## 1. Problem statement

A landing page pública hoje (`web/`) reflete só o "walking skeleton" (1 card de dívida + 2
módulos simples, ~200 linhas) — não comunica a proposta completa do produto. O usuário forneceu
um mockup completo (`docs/landpage.png`) com a visão de produto (nav, hero, painel de dados,
proposta, grid de módulos, portais, arquitetura, roadmap, benefícios), mas parte desse mockup
(painel "Command Center" com índices/alertas que não existem de verdade) não pode ser
implementada literalmente sem violar a regra inegociável de nunca fabricar métrica oficial
(`ADR-012`).

---

## 2. Target users

| Persona | Descrição | Pain point |
|---|---|---|
| **Cidadão, jornalista, pesquisador, avaliador do concurso CGU** (primária, `PRD-001`) | Público da landing pública | Precisa entender em minutos a proposta e o estado real do projeto — hoje só vê 3 números soltos, sem contexto de produto. |
| **Time de implementação / agentes de código** (secundária) | Quem mantém a Landing daqui pra frente | Precisa de um critério objetivo para os selos de status (módulo/fase/componente real vs. planejado), não um julgamento subjetivo a cada atualização. |

---

## 3. Goals (MoSCoW)

### MUST
- **G1.** Migrar `web/` de Vite+TS puro para **Astro** (saída estática, sem SSR), preservando o
  cliente OpenAPI gerado e a regra "nenhum valor hard-coded no bundle" (testada via e2e).
- **G2.** Nav fixo com âncoras para as seções da página.
- **G3.** Hero institucional (nome, tagline, proposta, CTAs) — conteúdo editorial do mockup.
- **G4.** Painel de dados **reais** substituindo o "Command Center" fictício do mockup: dívida,
  receita/despesa/primário fiscal, INSS (quando houver dado) — cada número com `data_class`
  (`ADR-028`) e link de fonte.
- **G5.** Build/deploy (`Dockerfile` de `web/`, `api-web.yml`) funcionando com a saída do Astro.
- **G6.** Testes e2e confirmando: nenhum valor hard-coded no bundle (regra já testada nas 3
  fatias anteriores), painel de dados renderiza ou degrada graciosamente.
- **G7.** Grid de módulos ("O que a plataforma terá") com selo de status **real/parcial/
  planejado**, seguindo o critério objetivo do `§10` deste documento.
- **G8.** Diagrama de arquitetura GCP com selo **real/planejado** por componente, seguindo o
  mesmo critério (`§10`).
- **G9.** Roadmap de 8 fases com selo **concluída/em andamento/não iniciada** por fase, seguindo
  o mesmo critério (`§10`).
- **G10.** Nenhum selo de status pode ser fabricado — todo selo rastreável a um fato real
  citável (`SHIPPED` doc, arquivo Terraform, ADR) — verificado no `/verify-spec`.

### SHOULD
- **G11.** Seção "Proposta do projeto" (Integrar/Entender/Prever/Agir) — editorial, do mockup.
- **G12.** Grid de portais — editorial (nenhum portal tem página real ainda).
- **G13.** Grid de benefícios esperados — editorial, do mockup.
- **G14.** Rodapé com CTA — editorial, do mockup.

### COULD
- **G15.** ADR novo (`docs/adrs/ADR-0XX-landing-page-astro.md`, número exato a confirmar no
  `/design`) formalizando a migração de stack, superando `ADR-051` explicitamente (nunca
  substituir um ADR silenciosamente).

---

## 4. Success criteria (mensuráveis)

| # | Critério | Medição |
|---|---|---|
| S1 | Migração Astro funcional | `npm run build` gera saída estática servível pelo `Dockerfile` atual (ou um ajustado, documentado); `npm run typecheck`/e2e verdes. |
| S2 | Sem valor fabricado | 100% dos números do painel de dados vêm de fetch em tempo de request (grep no bundle final confirma ausência de literais, mesmo teste das 3 fatias anteriores). |
| S3 | Selos de status rastreáveis | Todo selo `real`/`parcial`/`planejado` (módulos), `real`/`planejado` (arquitetura) e `concluída`/`em andamento`/`não iniciada` (roadmap) tem uma justificativa citável num comentário de código ou no `/design`/`BUILD_REPORT` apontando para o fato real (SHIPPED doc, `.tf`, ADR). |
| S4 | Sem regressão | As 3 fatias de dados (dívida, INSS, fiscal) continuam renderizando exatamente como antes na nova estrutura Astro. |
| S5 | `/verify-spec` PASS | Verificação independente (sessão nova, read-only) = OVERALL PASS, incluindo checagem de que nenhum selo de status é fabricado. |
| S6 | `ci-gate` verde | Todo PR desta fatia passa pelo `ci-gate` sem gate enfraquecido. |
| S7 | ADR de migração existe | `ADR-051` tem uma nota apontando para o ADR novo que o supera (ou é atualizado com uma seção "Superseded by"), conforme a regra de nunca substituir ADR silenciosamente. |

---

## 5. Acceptance tests

- **AT1 — migração Astro sem regressão visual/funcional.** *Given* a página migrada, *When*
  comparo contra o comportamento atual, *Then* dívida/INSS/fiscal continuam renderizando (ou
  degradando) exatamente como hoje.
- **AT2 — nenhum valor hard-coded.** *Given* o bundle final de produção, *When* busco pelos
  valores reais conhecidos (ex.: a cifra da dívida de 2022), *Then* nenhum aparece literalmente
  no JS servido — mesmo teste já usado nas 3 fatias anteriores, adaptado à estrutura Astro.
- **AT3 — painel de dados reais, não Command Center fictício.** *Given* a landing pública,
  *When* renderiza a seção de indicadores, *Then** os números vêm de `GET /v1/metrics/...` reais
  (dívida, fiscal, INSS), nunca um índice/alerta/recomendação inventado.
- **AT4 — selo de módulo rastreável.** *Given* o grid de módulos, *When* inspeciono o selo de
  cada card, *Then* consigo apontar o fato real por trás (SHIPPED doc ou ausência de um) — para
  Fiscal & Debt e Previdência & INSS no mínimo (os 2 módulos com algum dado real hoje).
- **AT5 — selo de arquitetura rastreável.** *Given* o diagrama de arquitetura, *When* inspeciono
  um componente marcado "real" (ex.: BigQuery), *Then* consigo apontar o Terraform/uso real
  correspondente.
- **AT6 — selo de roadmap rastreável.** *Given* o roadmap de 8 fases, *When* inspeciono uma fase
  marcada "concluída" ou "em andamento", *Then* consigo apontar o(s) `SHIPPED` doc(s)
  correspondente(s).
- **AT7 — build/deploy funcional.** *Given* o PR mergeado, *When* `api-web.yml` roda pós-merge,
  *Then* o deploy da web funciona com a saída do Astro, mesmo padrão de sucesso das fatias
  anteriores.
- **AT8 — ADR de migração existe e não substitui `ADR-051` silenciosamente.** *Given* o novo ADR,
  *When* leio `ADR-051`, *Then* há uma referência cruzada explícita (nota de superseded, ou
  seção "Quando reconsiderar" satisfeita e apontada).
- **AT9 — CI ritual completo.** *Given* qualquer PR desta fatia, *When* o CI roda, *Then*
  `ci-gate` resolve e bloqueia merge se qualquer gate falhar.

---

## 6. Out of scope

| Item | Motivo | Destino |
|---|---|---|
| Painel "Command Center" fiel ao mockup (On-Track Index, alertas, recomendações) | Métricas não existem de verdade; implementar violaria `ADR-012`. | Quando as features correspondentes (`EPIC-040`/`EPIC-023`/`EPIC-036`) existirem com dado real. |
| Portal executivo autenticado, simuladores avançados, edição administrativa | Já fora de escopo V1 do `PRD-001`. | Fases futuras do roadmap. |
| Roteamento client-side multi-página | Mockup é 1 página longa com âncoras, não múltiplas páginas. | Reavaliar se o produto crescer para Portais completos de verdade. |
| Gráfico interativo do "Brasil On-Track Index" | Métrica não existe. | Junto da feature que criar o índice de verdade. |
| Dark mode / internacionalização | Não pedido. | Reavaliar se houver pedido de produto. |
| Cenários 2036 detalhados (`STORY-002.06`) | Mockup fornecido não aprofunda essa seção. | Fatia futura dedicada. |

---

## 7. Constraints

- **C1.** Saída do Astro deve continuar servível como estático via Cloud Run (mesmo modelo de
  deploy atual, `api-web.yml`) — sem introduzir SSR/backend novo.
- **C2.** Nenhum valor numérico oficial hard-coded no bundle (`ADR-012`).
- **C3.** Nenhum selo de status fabricado — todo selo rastreável a um fato real (`C10` do
  Brainstorm).
- **C4.** `ADR-051` não pode ser silenciosamente substituído — precisa de um ADR novo com
  referência cruzada explícita.
- **C5.** Todo merge em `main` é via PR (branch protection).
- **C6.** Reusa `ci-gate`/`web-check` já existentes — ajustar se necessário para o novo comando
  de build do Astro, mas sem enfraquecer o gate.

---

## 8. Assumptions / risk register

| ID | Afirmação | Impacto se falsa | Validada |
|---|---|---|---|
| A1 | O modo estático do Astro (`output: 'static'`) gera um `dist/` compatível com o `Dockerfile` atual (serve estático via um servidor simples) sem mudança grande de infra | Precisaria ajustar o `Dockerfile`/`api-web.yml` mais do que o esperado — mais escopo de `/design` | ☐ |
| A2 | O critério objetivo de status (`§10`) é suficiente para classificar todos os módulos/fases/componentes do mockup sem ambiguidade restante | Alguns itens ficam em uma zona cinzenta (ex.: "parcialmente provisionado") — precisa de uma 4ª categoria ou nota textual, decisão de `/design` | ☐ |
| A3 | O texto exato de cada card do mockup (nomes de módulos, bullets de cada fase do roadmap, componentes do diagrama de arquitetura) pode ser extraído fielmente da imagem `docs/landpage.png` sem perda de informação | Se algum texto for ilegível/ambíguo na imagem, `/design` precisa decidir um texto equivalente razoável, documentado como tal, não inventado livremente | ☐ |

---

## 9. Technical context

| Aspecto | Definição |
|---|---|
| **Onde vive** | `web/` inteiro (migração), `web/src/pages/`ou equivalente Astro (a decidir no `/design`), `web/Dockerfile`, `.github/workflows/api-web.yml` (possível ajuste de comando de build), `web/tests/e2e/` (adaptação), `docs/adrs/` (+1 ADR novo). |
| **Impacto IaC** | Nenhum esperado em Terraform — mudança é de build de frontend, não de infraestrutura GCP. |
| **Domínios de KB** | `PRD-001`, `ADR-051` (a superar), `ADR-012`, `ADR-028`, `ADR-024`/`SPEC-026`, `ADR-040`; `EPIC-002` (backlog). |

---

## 10. Critério objetivo para selos de status (resolve OQ2 do Brainstorm)

- **Módulo = `real`**: tem ≥1 `metric_id` com dado real carregado em Gold **e** endpoint público
  funcionando servindo esse dado (confirmável via `curl` na API de produção).
- **Módulo = `parcial`**: tem ≥1 dataset do módulo com dado real, mas ≥1 outro dataset do mesmo
  módulo sem dado real ainda (ex.: Previdência & INSS — Emitidos/Indeferidos têm dado real,
  Mantidos não).
- **Módulo = `planejado`**: nenhum dataset do módulo tem dado real hoje.
- **Componente de arquitetura = `real`**: existe de verdade em `infra/terraform/*.tf` **e** está
  em uso ativo por algum pipeline/serviço já `SHIPPED`.
- **Componente de arquitetura = `planejado`**: mencionado em ADR/CONTEXTO como decisão de stack
  futura, mas sem recurso Terraform provisionado ou sem uso real ainda.
- **Fase do roadmap = `concluída`**: todas as entregas centrais listadas para aquela fase (não
  necessariamente cada bullet do mockup ao pé da letra) correspondem a pelo menos 1 feature
  `SHIPPED` que as cobre.
- **Fase do roadmap = `em andamento`**: alguma entrega central da fase já tem trabalho real
  `SHIPPED`, mas não todas (ex.: Fundação GCP tem ambiente dev completo, mas não stg/prod).
- **Fase do roadmap = `não iniciada`**: nenhuma entrega central da fase tem trabalho real ainda.

O mapeamento exato item-a-item (qual módulo/fase/componente recebe qual selo) é tarefa do
`/design` (descoberta real: reler `docs/landpage.png` com atenção ao texto exato de cada card,
cruzar contra `.claude/sdd/archive/*/SHIPPED_*.md` e `infra/terraform/*.tf` reais) — não deste
documento, para não fixar uma classificação antes de reler a fonte visual com cuidado.

---

## 11. Clarity score breakdown

| Elemento | Nota | Máx | Observação |
|---|---|---|---|
| Problem | 3 | 3 | Gap concreto: landing atual não reflete a proposta; parte do mockup não pode ser implementada literalmente (achado real, não hipotético). |
| Users | 2 | 3 | Público do portal (`PRD-001`, bem definido) + time de implementação (papel, não pessoa identificada) — reduz 1 ponto, mesmo padrão das fatias anteriores. |
| Goals | 3 | 3 | 10 MUST, 4 SHOULD, 1 COULD; todos mensuráveis e rastreáveis ao Brainstorm. |
| Success | 3 | 3 | S1–S7 com critérios verificáveis. |
| Scope | 2 | 3 | Out-of-scope bem povoado (6 itens), mas 3 assumptions reais (A1–A3) ainda não validadas — a migração de stack em si carrega incerteza técnica genuína que só o `/design` resolve. |
| **Total** | **13** | **15** | **HIGH — prosseguir para `/design`.** |

---

## 12. Open questions

| ID | Questão | Resolver em |
|---|---|---|
| OQ1 | Estrutura de páginas/componentes Astro (1 página só com `.astro` + ilhas, ou múltiplos arquivos `.astro` por seção)? | `/design` |
| OQ2 | Mapeamento exato item-a-item dos selos de status (módulos/fases/arquitetura) | `/design`, releitura cuidadosa de `docs/landpage.png` + fontes reais (`§10`) |
| OQ3 | Número exato do ADR novo (`ADR-058` provável, confirmar contra `docs/adrs/` no momento da execução) | `/design` |
| OQ4 | Ajuste necessário em `Dockerfile`/`api-web.yml` para servir a saída do Astro | `/design`, investigação real |

---

## 13. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-06 | 1.0 | Criação a partir de `BRAINSTORM_LANDING_PAGE_ASTRO.md`. Clarity 13/15. Status → Ready for Design. | /define (Claude Sonnet 5) |
