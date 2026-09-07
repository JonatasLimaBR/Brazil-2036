# BRAINSTORM — LANDING_PAGE_ASTRO

- **Feature:** LANDING_PAGE_ASTRO
- **Status:** ✅ Complete (Defined)
- **Fase:** 0 (Brainstorm)
- **Criado:** 2026-09-06
- **Idioma:** PT-BR (alinhado a `docs/discovery/`)
- **Próximo passo:** `/define .claude/sdd/features/BRAINSTORM_LANDING_PAGE_ASTRO.md`

> Nota: assets do plugin SDD ausentes — documento segue a lista de seções do skill
> `sdd-brainstorm`, mesmo padrão dos brainstorms anteriores.

---

## 1. Ideia

Atualizar a landing page pública (`web/`) para refletir a visão completa fornecida pelo usuário
em `docs/landpage.png` (nav, hero, painel de dados, proposta do projeto, grid de módulos,
portais, arquitetura GCP, roadmap de 8 fases, benefícios, rodapé) — combinado explicitamente com
o usuário para ser feito depois de fechar as fatias de dados (dívida, INSS, fiscal) e a feature
de padrões operacionais BigQuery, o que já aconteceu.

Diferente de toda fatia anterior (sempre um dataset novo), esta é a primeira fatia de **produto
de apresentação**: hoje `web/` só tem 1 card (dívida) + 2 módulos (INSS, fiscal) — 3 seções
simples, ~200 linhas de TypeScript sem framework. O mockup pede ~10 seções, várias delas
100% editoriais (sem dado ao vivo). Esse salto de complexidade já era previsto:
`ADR-051` (que escolheu Vite+TS sem framework) tem uma cláusula explícita "quando a Landing
tiver muitas seções interativas, reconsiderar Astro/Next.js" — o gatilho que este documento
aciona.

**Achado crítico já resolvido na descoberta (antes de qualquer código):** o painel "Command
Center" do mockup mostra números como "Brasil On-Track Index 72,4", "Dívida/PIB 73,6%",
"123,4 mi beneficiários", "18 alertas ativos", "33 recomendações" — nenhuma dessas métricas
existe de verdade hoje (são conceitos de fases futuras do roadmap: On-Track Index é `EPIC-040`,
Policy Lab é `EPIC-023`, ambos não construídos). Implementar isso literalmente violaria a regra
inegociável do `CLAUDE.md` ("nunca deixar um LLM fabricar uma métrica numérica oficial") e
`ADR-012`. **Decisão do usuário: substituir por um painel com dado real disponível hoje**
(dívida, receita/despesa/primário fiscal, INSS quando houver), não a visão aspiracional inteira.

---

## 2. Contexto técnico

| Aspecto | Observação |
|---|---|
| Stack atual | `ADR-051`: Vite + TypeScript sem framework, saída estática no Cloud Run. `web/src/`: `main.ts` (dívida), `inss.ts` (módulo M03), `fiscal.ts` (módulo M02), `styles.css`, cliente OpenAPI gerado. ~200 linhas totais. |
| **Decisão de stack desta fatia** | Usuário optou por **migrar para Astro agora** (não manter Vite+TS puro), antecipando a migração que o próprio `ADR-051` já previa como provável quando a Landing crescesse. Precisa de um ADR novo que **supere** `ADR-051` (`CLAUDE.md`: nunca substituir ADR silenciosamente) — decisão para o `/design`. |
| Fonte visual | `docs/landpage.png` — mockup completo fornecido pelo usuário nesta sessão (não um design system formal em Figma ou similar; é a única referência visual). Paleta: verde/amarelo/azul (bandeira do Brasil), já parcialmente presente em `styles.css` (`--green: #1b7a3d`). |
| **Dado real disponível hoje (para o painel substituto do Command Center)** | `divida_consolidada` (dívida, anual por UF), `fiscal_receita`/`fiscal_despesa`/`fiscal_primario` (mensal, nacional, 355 meses reais), `inss_beneficios_emitidos`/`_indeferidos` (parcial), `inss_beneficios_mantidos` (sem dado real ainda). Todos via `GET /v1/metrics/{metric_id}/national` (INSS/fiscal) ou `GET /v1/metrics/{metric_id}` (dívida, grão UF). |
| **Status real para grid de módulos/roadmap/arquitetura (G da seção 3)** | Extraído das 5 features já `SHIPPED` nesta sessão (`.claude/sdd/archive/`) e do estado real de `infra/terraform/` — não uma estimativa livre. Módulos com dado real: Fiscal & Debt (completo), Previdência & INSS (parcial). Demais ~10 módulos do grid: sem dado, backlog (`EPIC-003` Macro, `EPIC-011` Trabalho, `EPIC-012` Estados/Municípios, `EPIC-013` Saúde, `EPIC-014` Educação, `EPIC-015` Compras, etc.). Infra real provisionada: Cloud Storage, BigQuery, Cloud Run, IAM/WIF (sem chave estática). Infra planejada, não provisionada: Dataform (ADR-007 existe, não usado — o walking skeleton usa SQL puro via client Python, `ADR-052`), Pub/Sub+Dataflow, AlloyDB, Vertex AI/Gemini, Knowledge Graph/RAG completo. |
| PRD relevante | `PRD-001-landing-page-brasil-hoje.md` — escopo V1 já cobre: hero, cards de indicadores com fonte/data/unidade, séries históricas, desafios estruturais, cenários 2036 rotulados, fontes/metodologia, roadmap, acessibilidade básica. Fora de escopo V1: portal executivo autenticado, simuladores avançados completos, edição administrativa. |
| Backlog | `EPIC-002 — Landing & Brasil Hoje`: `STORY-002.01` (design system Brasil), `.02` (hero), `.03` (metric cards sourced), `.04` (historical timeline), `.05` (challenges), `.06` (2036 scenarios), `.07` (sources/methodology), `.08` (roadmap). |
| Regras inegociáveis relevantes | Nunca fabricar métrica oficial (`ADR-012`); observado/estimado/simulado visualmente distintos (`ADR-028`); nenhum valor hard-coded em bundle (já provado nas 3 fatias — teste e2e `test_no_debt_figure_hardcoded` como precedente a replicar). |

---

## 3. Discovery

| # | Pergunta | Resposta | Impacto no desenho |
|---|---|---|---|
| 1 | Como tratar os números fictícios do "Command Center" do mockup? | **Substituir por dado real disponível hoje** — não a visão aspiracional inteira, não rotular como mockup. | O painel de dados desta fatia mostra dívida/fiscal/INSS reais, não replica o layout exato do Command Center (índices/alertas/recomendações que não existem). |
| 2 | Manter a stack atual (Vite+TS sem framework) ou reconsiderar (Astro), dado que o `ADR-051` já previa isso? | **Migrar para Astro agora** — decisão do usuário, contra a recomendação inicial (que sugeria manter YAGNI). | Precisa de um ADR novo superando `ADR-051` (`/design`); build/deploy (`api-web.yml`, Dockerfile do `web/`) provavelmente precisam de ajuste — investigar no `/design`. |
| 3 | Escopo desta fatia: tudo de uma vez ou faseado? | **Faseado** — PR1 (estrutura Astro + dados reais) → PR2 (conteúdo estático com status real embutido). | Mesmo padrão de todas as fatias de dados anteriores (PR1/PR2), agora aplicado a uma feature de produto. |
| 4 | Grid de módulos, roadmap e arquitetura GCP — 100% estático ou com status real? | **Com status real** (as 3 seções) — não puramente editorial. | Cada card ganha um selo `real`/`parcial`/`planejado`, extraído de fatos reais (SHIPPED docs, Terraform), não fabricado. Portais e benefícios continuam puramente editoriais (não pedidos como "com status"). |
| 5 | Amostra visual disponível? | `docs/landpage.png` — único artefato visual, sem design system formal em ferramenta externa. | Todo detalhe de layout/cor/espaçamento vem da leitura direta da imagem, não de um Figma/tokens formais. |

---

## 4. Inventário de amostras

| Tipo | Disponível? | Uso previsto |
|---|---|---|
| Mockup visual completo | Sim — `docs/landpage.png`, fornecido pelo usuário nesta sessão. | Referência única de layout/seções/paleta para o `/design`. |
| Design system formal (tokens, Figma) | Não. | Extrair paleta/tipografia da imagem + do `styles.css` já existente (`--green`, etc.), documentar como decisão de `/design`, não inventar um sistema maior que o necessário. |
| Dado real para o painel substituto | Sim — 3 fatias já `SHIPPED` com endpoints reais (`/v1/metrics/{metric_id}[/national]`). | Painel de dados do PR1 consome esses endpoints diretamente, mesmo padrão já usado em `main.ts`/`inss.ts`/`fiscal.ts`. |
| Fatos reais para status de módulos/roadmap/arquitetura | Sim — `.claude/sdd/archive/*/SHIPPED_*.md`, `infra/terraform/*.tf`, `CLAUDE.md` "Estado atual". | Base para popular os selos de status do PR2 — nunca estimativa livre. |
| Código relacionado | Sim — `web/src/{main,inss,fiscal}.ts`, `web/index.html`, `web/src/styles.css`, `web/package.json`, `Dockerfile` do `web/` (usado por `api-web.yml`). | Base a migrar/estender para Astro, não greenfield. |

---

## 5. Abordagens exploradas

### Abordagem A — Migração para Astro, faseada em 2 PRs ⭐ Escolhida
- **O quê:** `/design` decide a estrutura de páginas/componentes Astro; PR1 migra a base (nav,
  hero, painel de dados reais funcionando de ponta a ponta, substituindo `main.ts`/`inss.ts`/
  `fiscal.ts` por componentes Astro equivalentes); PR2 adiciona as seções 100% de conteúdo
  (proposta, grid de módulos com status, portais, arquitetura GCP com status, roadmap com status,
  benefícios, rodapé).
- **Prós:** resolve a reconsideração de stack já prevista no `ADR-051` de uma vez, no momento em
  que a Landing realmente cresce; faseamento em 2 PRs mantém o padrão de revisão pequena já
  provado em 4 fatias anteriores; nenhum número fabricado (painel de dados real, status extraído
  de fato real).
- **Contras:** maior escopo de migração que "só adicionar seções" — build/deploy/testes e2e
  precisam ser confirmados funcionando com Astro antes do PR1 fechar.
- **Confiança:** 0.75 — decisão do usuário contra a recomendação inicial (YAGNI sugeria manter
  Vite+TS); migração de stack é sempre um risco técnico real, mitigado por já ter sido prevista
  e documentada como cláusula de reconsideração no próprio `ADR-051`.

### Abordagem B — Manter Vite+TS sem framework, só adicionar seções estáticas
- **O quê:** todas as ~10 seções do mockup como funções `render*()` adicionais em TypeScript
  puro, mesmo padrão de `renderInssModule`/`renderFiscalModule`.
- **Por que não escolhida:** rejeitada por decisão explícita do usuário — preferiu antecipar a
  migração de stack já prevista no `ADR-051`, em vez de continuar empilhando seções manuais.
- **Confiança:** 0.85 (tecnicamente mais simples e menor risco, mas não é a escolha do usuário).

### Abordagem C — Reproduzir o mockup literalmente, incluindo o Command Center fictício
- **O quê:** implementar os números do painel "Command Center" como estão na imagem.
- **Por que não escolhida:** violaria a regra inegociável de nunca fabricar métrica oficial
  (`ADR-012`) — rejeitada por decisão de integridade de dado, não de preferência técnica.
- **Confiança:** N/A (rejeitada por regra inegociável, não por trade-off).

---

## 6. Itens removidos / adiados (YAGNI)

| Item | Por que fora desta fatia | Vai para |
|---|---|---|
| Painel "Command Center" fiel ao mockup (On-Track Index, Policy Lab ativo, alertas/recomendações) | Métricas não existem de verdade (`EPIC-040`/`EPIC-023`/`EPIC-036`, não construídos); implementar violaria `ADR-012`. | Quando essas features existirem de verdade, com dado real. |
| Portal executivo autenticado, simuladores avançados, edição administrativa de métricas | Já fora de escopo V1 do `PRD-001` explicitamente. | Fases futuras do roadmap, PRDs próprios. |
| Roteamento client-side multi-página | O mockup é 1 página longa com âncoras de nav, não múltiplas páginas — não precisa de router. | Reavaliar se o produto crescer para múltiplas páginas de verdade (Portais completos, já cogitado no `ADR-051`). |
| Gráfico interativo do "Brasil On-Track Index" (mini-linha 2022-2036 do mockup) | Mesma razão do Command Center — a métrica em si não existe. | Junto com a feature que criar o índice de verdade. |
| Dark mode / internacionalização | Não pedido, não mencionado no mockup nem no PRD. | Reavaliar se houver pedido de produto. |
| Cenários 2036 detalhados (`STORY-002.06`) | O mockup fornecido não aprofunda essa seção especificamente; ficaria subespecificado sem mais discovery. | Fatia futura dedicada, ou incremento se o `/design` achar um encaixe natural de baixo custo. |

---

## 7. Requisitos-rascunho (para o `/define`)

### PR1 — estrutura Astro + dados reais
- **R1.** Migrar `web/` de Vite+TS puro para Astro, preservando o cliente OpenAPI gerado
  (`openapi-typescript`) e o padrão "nenhum valor hard-coded no bundle" (regra já testada via
  e2e nas 3 fatias anteriores).
- **R2.** Nav fixo com âncoras para as seções da página (Visão Geral, Módulos, Arquitetura,
  Roadmap, Portais, Contato).
- **R3.** Hero institucional (nome, tagline, proposta em 1 frase, CTAs) — conteúdo editorial.
- **R4.** Painel de dados reais substituindo o "Command Center" do mockup: dívida, receita/
  despesa/primário fiscal, INSS (quando houver dado) — cada número com classe `observed`
  (`ADR-028`) e link de fonte, mesmo padrão de `main.ts`/`inss.ts`/`fiscal.ts` hoje.
- **R5.** `Dockerfile`/`api-web.yml` continuam funcionando com a saída estática do Astro (ajuste
  se necessário — decisão de `/design`).
- **R6.** Testes e2e migrados/adaptados (`web/tests/e2e/*.spec.ts`) confirmando: nenhum valor
  hard-coded no bundle, os 3 conjuntos de dados reais renderizam ou degradam graciosamente.

### PR2 — conteúdo com status real
- **R7.** Seção "Proposta do projeto" (Integrar/Entender/Prever/Agir) — editorial, do mockup.
- **R8.** Grid de módulos ("O que a plataforma terá") — cada card com selo `real`/`parcial`/
  `planejado`, extraído de fato real (`SHIPPED` docs, backlog `EPIC-*`).
- **R9.** Grid de portais — editorial (nenhum dos portais existe como página real ainda; são
  descrições do que virá, sem link funcional para além da própria Landing).
- **R10.** Diagrama de arquitetura GCP — cada componente com selo `real`/`planejado`, extraído
  de `infra/terraform/*.tf` real.
- **R11.** Roadmap de 8 fases — cada fase com selo de progresso real (`concluída`/`em andamento`/
  `não iniciada`), extraído do histórico real de `SHIPPED` docs.
- **R12.** Grid de benefícios esperados — editorial, do mockup.
- **R13.** Rodapé com CTA — editorial, do mockup.
- **R14.** Nenhum selo de status (`real`/`parcial`/`planejado`/fases do roadmap) pode ser
  fabricado — todo selo rastreável a um fato real citável (SHIPPED doc, arquivo Terraform, ADR).

---

## 8. Decisões autônomas registradas

| Decisão | Motivo |
|---|---|
| Substituir o Command Center fictício por painel de dado real | Regra inegociável do `CLAUDE.md`/`ADR-012` — não fabricar métrica oficial. Decisão do usuário, não só de Claude. |
| Migrar para Astro (não manter Vite+TS) | Decisão explícita do usuário, contra a recomendação inicial de YAGNI — antecipa a reconsideração já prevista no `ADR-051`. |
| Faseamento em PR1 (estrutura+dados)/PR2 (conteúdo+status) | Mesmo padrão de revisão pequena já provado em 4 fatias anteriores; decisão do usuário. |
| Grid de módulos, roadmap e arquitetura com status real (não editorial puro) | Decisão explícita do usuário — mais fiel ao princípio de nunca fabricar/exagerar progresso do projeto. |
| Cenários 2036 (`STORY-002.06`) fora de escopo desta fatia | Mockup fornecido não aprofunda essa seção; evita subespecificar e inventar conteúdo no lugar do usuário. |

---

## 9. Questões abertas (resolver no `/define` ou `/design`)

1. **ADR novo superando `ADR-051`** — número exato (`ADR-058`, a confirmar no `/design` contra o
   estado real de `docs/adrs/` no momento da execução), conteúdo formalizando a escolha do Astro.
2. **Critério objetivo para os selos de status** (`real`/`parcial`/`planejado` dos módulos;
   `concluída`/`em andamento`/`não iniciada` do roadmap) — precisa de uma regra clara e citável
   (ex.: "módulo = real se tem ≥1 `metric_id` com dado real em Gold e endpoint público
   funcionando"), não um julgamento caso a caso sem critério. Decisão de `/define`/`/design`.
3. **Build/deploy do Astro** — `Dockerfile`/`api-web.yml` atuais assumem `vite build` gerando
   `dist/` estático; confirmar que o output do Astro (modo estático, sem SSR) é um substituto
   direto, ou se precisa de ajuste de pipeline. Investigação real no `/design`.
4. **Onde mora o `especie_codigo`/dado de INSS Mantidos "sem dado real"** no selo do módulo —
   confirmar que "parcial" (não "planejado") é a classificação certa para Previdência & INSS,
   dado que 2 dos 3 datasets têm dado real e 1 não.

---

## 10. Domínios de KB para a Fase Define

- **PRDs:** `PRD-001` (Landing Page & Brasil Hoje).
- **ADRs:** `ADR-051` (stack atual, a superar), `ADR-012` (nunca fabricar métrica), `ADR-028`
  (observado/estimado/simulado), `ADR-024`/`SPEC-026` (cliente TS gerado do OpenAPI), `ADR-040`
  (WIF, sem chave estática — para o diagrama de arquitetura).
- **Backlog:** `EPIC-002` (Landing & Brasil Hoje) — todas as 8 stories.
- **Precedente direto:** `.claude/sdd/archive/{MVP_WALKING_SKELETON,CI_ASSURANCE_GATES,INSS_BENEFICIOS,FISCAL_RECEITA_DESPESA,BIGQUERY_OPERATIONAL_STANDARDS}/` — fonte real para os selos de status do PR2.
- **Código:** `web/` inteiro (a migrar), `api/src/api/main.py` (endpoints já existentes, sem
  mudança esperada), `infra/terraform/*.tf` (fonte real para o selo de arquitetura).

---

## 11. Quality gate (Fase 0)

- [x] Mínimo de 3 perguntas de discovery feitas e respondidas (5 feitas)
- [x] Pergunta de amostras feita — `docs/landpage.png` é a amostra real
- [x] Pelo menos 2 abordagens exploradas com trade-offs (A, B, C)
- [x] Usuário confirmou explicitamente a abordagem escolhida (A) e o desenho emergente (checkpoint de validação)
- [x] YAGNI aplicado — seção de itens removidos preenchida (6 itens)
- [x] Mínimo de 2 validações incrementais concluídas (checkpoint do Command Center; checkpoint do desenho final faseado)
- [x] Domínios de KB identificados para o Define
- [x] Requisitos-rascunho prontos para o `/define` (R1–R14)

---

## 12. Handoff

Pronto para `/define .claude/sdd/features/BRAINSTORM_LANDING_PAGE_ASTRO.md`.
