# DESIGN — LANDING_PAGE_ASTRO

## Metadados

- **Feature:** LANDING_PAGE_ASTRO
- **Status:** ✅ Shipped

> Shipped and archived 2026-09-07.
- **Fase:** 2 (Design)
- **Entrada:** `.claude/sdd/features/DEFINE_LANDING_PAGE_ASTRO.md` (Clarity 13/15)
- **Criado:** 2026-09-06
- **Idioma:** PT-BR
- **Branch:** a criar — `feature/landing-page-astro`
- **Confiança:** 0.8 — migração de stack é sempre incerteza técnica real; mitigada por
  confirmação real (pesquisa) de que a saída estática do Astro é compatível com o `Dockerfile`
  atual sem mudança, e por releitura completa e literal do mockup (não paráfrase).
- **Próximo passo:** `/build .claude/sdd/features/DESIGN_LANDING_PAGE_ASTRO.md`

> Nota: assets do plugin SDD ausentes — documento segue a lista de seções do skill `sdd-design`.

---

## 0. Descoberta real (tarefa 1 — resolve OQ1–OQ4 do DEFINE)

### 0.1 Compatibilidade de build/deploy (OQ4/A1 — resolvida)

`web/Dockerfile` hoje: `npm run build` → `dist/` → `nginx` estático. Astro (modo `static`, que é
o **default** do framework, sem SSR) também gera `dist/` estático — **nenhuma mudança de
`Dockerfile`/`api-web.yml` necessária**, resolve A1 do DEFINE como verdadeira. Único ajuste:
Astro só expõe ao client-side variáveis de ambiente prefixadas `PUBLIC_` por padrão; para manter
`VITE_API_URL` (nome já usado em `api-web.yml`, sem renomear a variável de CI), `astro.config.mjs`
configura `vite: { envPrefix: ["VITE_"] }` — confirmado via documentação real do Astro/Vite, não
suposição.

### 0.2 Texto literal do mockup (releitura completa de `docs/landpage.png`)

Releitura integral da imagem (não paráfrase da primeira leitura). Texto exato de cada seção:

- **Nav:** Visão Geral · Módulos · Arquitetura · Roadmap · Portais · Contato · [Ver Roadmap] · [Explorar Plataforma]
- **Hero:** "BRASIL 2036 — Nos Trilhos" / "Plataforma Nacional de Inteligência Econômica, Fiscal e Social" / H1 "Transformando dados públicos em decisões para o futuro do Brasil" / parágrafo + 5 badges ("IA + Dados Públicos", "GCP Native", "Multiagente", "Simulação 2036", "Landing Page desde o início").
- **Painel de dados (substitui "Command Center"):** ver `§0.3`.
- **Proposta do projeto (4 cards):** Integrar / Entender / Prever / Agir, com os textos exatos do mockup.
- **O que a plataforma terá (15 cards):** Macro Economic Twin, Fiscal & Debt, Previdência & INSS, Trabalho & Renda, Produtividade, Saúde, Educação, Estados & Municípios, Compras Públicas, Investimento Público, Tributação, Fraude & Anomalias, Policy Lab, Command Center, Agent Center.
- **Portais e Experiência (8 cards):** Portal Público, Portal Executivo, Portal Analítico, Portal INSS, Portal Estados e Municípios, Policy Lab, Agent Center, Administração da Plataforma.
- **Arquitetura GCP (12 componentes):** Cloud Storage, BigQuery, Dataform, Pub/Sub & Dataflow, AlloyDB & AI, Vertex AI/Gemini, Cloud Run + API Gateway, Knowledge Catalog, IAM & Segurança, Observabilidade (Monitoring), FinOps, MLOps/LLMOps. Legenda: "Lakehouse · IA · Knowledge Graph · RAG · Agentes sobre GCP".
- **Roadmap (8 fases):** textos completos em `§0.4`.
- **Benefícios esperados (6 cards):** Decisão orientada por dados, Sustentabilidade fiscal, Eficiência do INSS, Monitoramento municipal, Simulação de políticas públicas, Redução de riscos.
- **Rodapé CTA:** "O projeto começa com uma landing page e evolui para uma plataforma nacional de inteligência e simulação." + [Solicitar Demonstração] [Ver Arquitetura] + barra "Dados públicos · Inteligência econômica · GCP · IA aplicada ao setor público".

### 0.3 Painel de dados reais (substitui o Command Center fictício)

3 números reais disponíveis hoje via API de produção, confirmados por `curl` real nesta sessão:
`divida_consolidada` (`/v1/metrics/divida_consolidada`), `fiscal_receita`/`fiscal_despesa`/
`fiscal_primario` (`/v1/metrics/{id}/national`), `inss_beneficios_emitidos`/`_indeferidos`
(`/v1/metrics/{id}/national`, `inss_beneficios_mantidos` retorna 404 — sem dado real, degrada
graciosamente). Painel mostra os 3 grupos (Dívida, Fiscal, Previdência) reaproveitando
exatamente o padrão já provado (`main.ts`/`fiscal.ts`/`inss.ts`) — sem índice/alerta/
recomendação inventados.

### 0.4 Roadmap — texto completo e status real por fase

| Fase | Entregas centrais (texto do mockup) | Status real | Por quê |
|---|---|---|---|
| 1 — Landing Page & Marca | Naming/identidade visual; Landing page pública desde o início; Proposta e posicionamento; CTAs e contato; Roadmap de alto nível | **Em andamento** | Esta própria fatia; identidade visual (verde/amarelo/azul) já existe parcialmente em `styles.css`, landing pública já está no ar desde `MVP_WALKING_SKELETON`, mas incompleta até este PR fechar. |
| 2 — Fundação GCP | Landing zone/organização; IAM; segurança/redes/firewalls; IaC (Terraform); observabilidade/logging; ambientes dev/stg/prod | **Em andamento** | `bootstrap.sh`/WIF/Terraform reais (`ADR-040`), mas só ambiente `dev` existe — `stg`/`prod` não. |
| 3 — Dados Públicos | Ingestão de dados públicos; Cloud Storage/versionamento; BigQuery Bronze/Silver/Gold; Dataform/ELT; qualidade/validações; catálogo/governança | **Em andamento** | Ingestão, Storage e BigQuery Bronze/Silver/Gold são reais (3 fatias `SHIPPED`); Dataform nunca usado (`ADR-052` optou por SQL puro); catálogo é só a tabela `dataset_registry`, sem UI. |
| 4 — Núcleo Econômico | Macro Twin; DebtLab; INSS Twin; Labor Intelligence; Municipality Twin | **Não iniciada** | Temos dados brutos de dívida/INSS/fiscal, não os "Twins" funcionais (com simulação/risco/cenário) que a fase descreve — a fatia de dados é pré-requisito, não a entrega da fase. |
| 5 — Portais & Acessos | Portais público/executivo/analítico/INSS; Estados e Municípios; Administração; RBAC+ABAC; Multi-organização | **Não iniciada** | Só existe 1 landing pública, sem múltiplos portais nem RBAC/ABAC. |
| 6 — Inteligência Avançada | Forecasting; RAG/chat; Knowledge Graph; Causal AI; Monte Carlo | **Não iniciada** | Nenhum código de IA/simulação existe ainda. |
| 7 — Agentes & Simulação | Agentes especializados; orquestrador; copilotos; Policy Simulator; alertas proativos | **Não iniciada** | Nenhum agente em produção (`EPIC-026`). |
| 8 — Plataforma Completa | Command Center nacional; expansão; escala; APIs públicas; operação contínua | **Não iniciada** | Depende de todas as fases anteriores. |

### 0.5 Grid de módulos — status real (15 cards)

| Módulo | Status | Por quê |
|---|---|---|
| Fiscal & Debt | **Real** | `divida_consolidada` + `fiscal_receita`/`_despesa`/`_primario`, todos com dado real em Gold e endpoint público funcionando (`FISCAL_RECEITA_DESPESA` `SHIPPED`). |
| Previdência & INSS | **Parcial** | `inss_beneficios_emitidos` (1 mês real) e `_indeferidos` (37/38 meses real) têm dado; `_mantidos` não (`INSS_BENEFICIOS` `SHIPPED`, backfill fechado por decisão explícita). |
| Macro Economic Twin, Trabalho & Renda, Produtividade, Saúde, Educação, Estados & Municípios, Compras Públicas, Investimento Público, Tributação, Fraude & Anomalias, Policy Lab, Command Center, Agent Center (13 módulos) | **Planejado** | Nenhum tem `metric_id` com dado real em Gold hoje. |

### 0.6 Arquitetura GCP — status real (12 componentes)

| Componente | Status | Por quê |
|---|---|---|
| Cloud Storage | **Real** | Bucket RAW real (`brasil2036-dev-raw`), `infra/terraform/storage.tf`. |
| BigQuery | **Real** | `br2036_{control,bronze,silver,gold}`, uso extensivo real. |
| Cloud Run + API Gateway | **Real** (com nota) | Cloud Run real (`br2036-api`, `br2036-web`, `br2036-ingestion`); não há recurso formal de API Gateway provisionado — a URL HTTPS do próprio Cloud Run cumpre esse papel nesta fase. Nota explícita no componente, não card separado (o mockup já os funde em 1 card). |
| IAM & Segurança | **Real** | WIF, sem chave estática (`ADR-040`), real em Terraform. |
| Dataform | **Planejado** | `ADR-007` planeja, mas `ADR-052` optou por SQL puro via client Python — nunca provisionado. |
| Pub/Sub & Dataflow | **Planejado** | Sem recurso Terraform, sem uso. |
| AlloyDB & AI | **Planejado** | `ADR-004` planeja, não provisionado. |
| Vertex AI/Gemini | **Planejado** | Nenhum código de IA/agente em produção. |
| Knowledge Catalog | **Planejado** | `dataset_registry` é uma tabela de metadado interna, não a capacidade de catálogo/descoberta que o card descreve. |
| Observabilidade (Monitoring) | **Planejado** | Só logs básicos do Cloud Run, sem dashboard formal. |
| FinOps | **Parcial** | Cap de bytes por query real e implementado (`SPEC-034`/`ADR-057`); orçamento de projeto/billing export não implementado (`EPIC-042`). |
| MLOps/LLMOps | **Planejado** | Sem modelo/agente em produção. |

---

## 1. Grounding

| Padrão a reaproveitar | Fonte |
|---|---|
| Cliente OpenAPI gerado, fetch em tempo de request, sem hardcode | `web/src/{main,inss,fiscal}.ts` — mesmo padrão, portado para componentes/ilhas Astro. |
| `Dockerfile`/`api-web.yml` inalterados | `§0.1`. |
| e2e "sem valor hard-coded no bundle" | `web/tests/e2e/card.spec.ts::test_no_debt_figure_hardcoded` — mesmo teste, adaptado ao novo caminho de bundle do Astro. |
| Paleta verde/amarelo/azul | `web/src/styles.css` (`--green` já existe); estender com amarelo/azul reais da bandeira. |

---

## 2. Arquitetura

```text
┌──────────────────────────────────────────────────────────────────┐
│  web/ (Astro, output: static)                                    │
│                                                                    │
│  src/pages/index.astro  — página única, seções por âncora         │
│    ├─ <Nav />                                                     │
│    ├─ <Hero />                                                    │
│    ├─ <DataPanel client:load />  ── fetch real (D-ilha interativa)│
│    ├─ <Proposal />                                                │
│    ├─ <ModuleGrid statuses={moduleStatus} />  ── status estático  │
│    ├─ <PortalsGrid />                                             │
│    ├─ <Architecture statuses={archStatus} />  ── status estático  │
│    ├─ <Roadmap statuses={phaseStatus} />      ── status estático  │
│    ├─ <Benefits />                                                │
│    └─ <FooterCta />                                               │
│                                                                    │
│  src/data/status.ts  — as 3 tabelas do §0.4/0.5/0.6, com comentário│
│    apontando o SHIPPED/ADR/Terraform real por trás de cada selo   │
│                                                                    │
│  src/lib/metrics.ts  — cliente OpenAPI + fetch dos 3 grupos reais │
│    (mesma lógica de main.ts/inss.ts/fiscal.ts, portada)           │
└──────────────────────────┬─────────────────────────────────────────┘
                             │ npm run build → dist/ (idêntico ao Vite)
                             ▼
                    Dockerfile/nginx (inalterado, §0.1)
```

---

## 3. Decisões (ADRs inline)

### D1 — Migração para Astro (modo `static`), supera `ADR-051` explicitamente

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-06 |

**Contexto:** `ADR-051` escolheu Vite+TS sem framework, com cláusula explícita de reconsiderar
quando a Landing tivesse muitas seções interativas — exatamente o cenário desta fatia (10
seções, 15+8+12+8 cards). Decisão do usuário: migrar agora.

**Escolha:** Astro, `output: "static"` (default, sem SSR), `astro.config.mjs` com
`vite: { envPrefix: ["VITE_"] }` para preservar `VITE_API_URL` sem renomear a variável de CI
(`§0.1`, confirmado via documentação real).

**Racional:** confirmado por pesquisa real que a saída é um substituto direto do `dist/` do
Vite — migração sem custo de infraestrutura; Astro permite ilhas de hidratação seletiva
(`client:load`) só onde há fetch real (o painel de dados), mantendo as seções estáticas como
HTML puro sem JS de framework, alinhado ao próprio racional original do `ADR-051` (menor
payload de JS).

**Alternativas rejeitadas:** ver `BRAINSTORM §5` (Abordagem B — manter Vite+TS; Abordagem C —
reproduzir o Command Center fictício, rejeitada por regra inegociável).

**Consequências:** (+) resolve a reconsideração já prevista sem custo de deploy; (+) só a seção
com dado real carrega JS de fetch, o resto é HTML estático. (−) novo toolchain a aprender/manter;
(−) `ADR-051` precisa de nota de superseded (D2).

**Novo ADR:** `docs/adrs/ADR-058-landing-page-astro-supersedes-adr-051.md` (número confirmado
contra `docs/adrs/` no momento do build — próximo disponível após `ADR-057`).

### D2 — `ADR-051` ganha nota de "Superseded by ADR-058", não é apagado nem reescrito

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-06 |

**Contexto:** `CLAUDE.md` — "nunca substituir um ADR silenciosamente; supere-o com outro ADR".

**Escolha:** `ADR-051` permanece no repositório, íntegro, com uma linha adicionada logo abaixo do
título: "> **Superseded by `ADR-058`** (2026-09-06): a Landing cresceu para múltiplas seções,
gatilho que este ADR já prevẽ na seção 'Quando reconsiderar'."

**Racional:** preserva o histórico de decisão (por que Vite+TS fazia sentido em 2026-09-03) sem
apagar contexto; `ADR-058` referencia `ADR-051` de volta.

**Consequências:** (+) histórico de decisão auditável; nenhuma negativa relevante.

### D3 — Selos de status como dado estático versionado (`src/data/status.ts`), não fetch ao vivo

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-06 |

**Contexto:** módulos/fases/arquitetura mudam de status raramente (só quando uma feature nova é
`SHIPPED`) — não precisam de endpoint dedicado.

**Escolha:** `src/data/status.ts` exporta 3 constantes tipadas (`MODULE_STATUS`,
`ARCHITECTURE_STATUS`, `ROADMAP_STATUS`), cada entrada com `{ id, label, status, evidence }`,
onde `evidence` é uma string curta citando o fato real (ex.: `"FISCAL_RECEITA_DESPESA SHIPPED
2026-09-05"`) — os valores exatos de `§0.4/0.5/0.6`.

**Racional:** zero custo de API nova; a atualização deste arquivo passa a fazer parte do ritual
já existente de sincronizar `CLAUDE.md` a cada `/ship` (mesma disciplina, arquivo a mais).
`evidence` obrigatório em cada entrada é o mecanismo que impede um selo fabricado no futuro (fica
visível em code review se alguém tentar adicionar um status sem justificativa).

**Alternativas rejeitadas:**
1. *Endpoint de API dedicado para status* — rejeitado: over-engineering para dado que muda a
   cada poucos dias, no máximo.

**Consequências:** (+) sem infraestrutura nova; (+) `evidence` força rastreabilidade. (−) exige
disciplina humana/de agente para manter atualizado — mitigado por virar parte do ritual de
`/ship` já estabelecido.

### D4 — Painel de dados reais como ilha Astro (`client:load`), reaproveitando a lógica de fetch existente

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-06 |

**Contexto:** só esta seção precisa de fetch em tempo de execução; o resto da página é estático.

**Escolha:** `src/lib/metrics.ts` consolida a lógica hoje espalhada em `main.ts`/`inss.ts`/
`fiscal.ts` (fetch + formatação + graceful degradation) num módulo só, consumido por um
componente Astro com `client:load`.

**Consequências:** (+) 1 único lugar para a lógica de fetch, mais fácil de testar; (−) pequena
refatoração dos 3 arquivos existentes (não é reescrita — a lógica em si não muda).

---

## 4. Manifesto de arquivos

### PR1 — estrutura Astro + dados reais

| # | Arquivo | Ação | Propósito | Agente | Deps |
|---|---|---|---|---|---|
| 1 | `docs/adrs/ADR-058-landing-page-astro-supersedes-adr-051.md` | Create | Formaliza D1 | `architect` | — |
| 2 | `docs/adrs/ADR-051-frontend-stack-vite-typescript-for-public-landing.md` | Modify | +nota "Superseded by ADR-058" (D2) | `architect` | 1 |
| 3 | `web/package.json` | Modify | +`astro`, remove `vite` direto (Astro traz Vite embutido) | `python-developer` (frontend, `(general)`) | — |
| 4 | `web/astro.config.mjs` | Create | `output: "static"`, `vite.envPrefix: ["VITE_"]` (D1) | `(general)` | 3 |
| 5 | `web/src/pages/index.astro` | Create | Página única, monta as seções | `typescript-reviewer` | 4 |
| 6 | `web/src/components/Nav.astro` | Create | Nav com âncoras | `typescript-reviewer` | 5 |
| 7 | `web/src/components/Hero.astro` | Create | Hero + badges (texto literal `§0.2`) | `typescript-reviewer` | 5 |
| 8 | `web/src/lib/metrics.ts` | Create | Consolida fetch (D4), a partir de `main.ts`/`inss.ts`/`fiscal.ts` | `typescript-reviewer` | — |
| 9 | `web/src/components/DataPanel.astro` (+ script `client:load`) | Create | Painel de dados reais (`§0.3`) | `typescript-reviewer` | 8 |
| 10 | `web/src/main.ts`, `web/src/inss.ts`, `web/src/fiscal.ts` | Delete | Lógica migrada para `lib/metrics.ts` + `DataPanel.astro` | `typescript-reviewer` | 9 |
| 11 | `web/src/styles.css` → `web/src/styles/global.css` | Modify/Move | Paleta completa (verde/amarelo/azul), estende o já existente | `(general)` | — |
| 12 | `web/tests/e2e/card.spec.ts` | Modify | Adapta para a nova estrutura Astro; mantém a asserção "sem valor hard-coded" | `python-reviewer` | 5-10 |
| 13 | `web/tsconfig.json` | Modify | Ajusta `include`/`types` para Astro (`astro/tsconfigs/strict` como base) | `(general)` | 4 |
| 14 | `INDEX.md` | Modify | +ADR-058 | `(general)` | 1 |

### PR2 — conteúdo com status real

| # | Arquivo | Ação | Propósito | Agente | Deps |
|---|---|---|---|---|---|
| 15 | `web/src/data/status.ts` | Create | 3 constantes tipadas + `evidence` (D3, valores de `§0.4/0.5/0.6`) | `typescript-reviewer` | PR1 |
| 16 | `web/src/components/Proposal.astro` | Create | 4 cards (Integrar/Entender/Prever/Agir), texto literal | `typescript-reviewer` | 15 |
| 17 | `web/src/components/ModuleGrid.astro` | Create | 15 cards + selo de status (`MODULE_STATUS`) | `typescript-reviewer` | 15 |
| 18 | `web/src/components/PortalsGrid.astro` | Create | 8 cards, editorial | `typescript-reviewer` | 15 |
| 19 | `web/src/components/Architecture.astro` | Create | 12 componentes + selo (`ARCHITECTURE_STATUS`) | `typescript-reviewer` | 15 |
| 20 | `web/src/components/Roadmap.astro` | Create | 8 fases + selo (`ROADMAP_STATUS`) | `typescript-reviewer` | 15 |
| 21 | `web/src/components/Benefits.astro` | Create | 6 cards, editorial | `typescript-reviewer` | 15 |
| 22 | `web/src/components/FooterCta.astro` | Create | CTA final, editorial | `typescript-reviewer` | 15 |
| 23 | `web/src/pages/index.astro` | Modify | Monta as 6 seções novas | `typescript-reviewer` | 16-22 |
| 24 | `web/tests/e2e/card.spec.ts` | Modify | +teste: todo card de status tem `evidence` não-vazio (prova viva de C3/S3) | `python-reviewer` | 23 |

### Racional de agentes
Componentes visuais/conteúdo Astro/TS → `typescript-reviewer`; ADR → `architect`; testes e2e →
`python-reviewer` (mesmo padrão já usado no projeto para specs Playwright); itens de config sem
especialista dedicado → `(general)`.

### Independência
PR1 é autocontido (migra a estrutura + as 3 fatias de dados já existentes). PR2 depende de PR1
(precisa da estrutura Astro existir). Sem ciclo.

---

## 5. Padrões de código

### 5.1 `src/data/status.ts` — status com evidência obrigatória (D3)

```typescript
export type Status = "real" | "parcial" | "planejado";
export type PhaseStatus = "concluida" | "em_andamento" | "nao_iniciada";

export interface StatusEntry {
  id: string;
  label: string;
  status: Status;
  evidence: string; // nunca vazio -- aponta pro fato real (SHIPPED/ADR/Terraform)
}

export const MODULE_STATUS: StatusEntry[] = [
  { id: "fiscal-debt", label: "Fiscal & Debt", status: "real",
    evidence: "FISCAL_RECEITA_DESPESA SHIPPED 2026-09-05 -- divida+receita+despesa+primario reais" },
  { id: "previdencia-inss", label: "Previdência & INSS", status: "parcial",
    evidence: "INSS_BENEFICIOS SHIPPED -- emitidos/indeferidos reais, mantidos sem dado" },
  { id: "macro-twin", label: "Macro Economic Twin", status: "planejado",
    evidence: "EPIC-003, nenhum metric_id real em Gold ainda" },
  // ... demais 12 módulos, todos "planejado" com evidence apontando o EPIC
];
```

### 5.2 `DataPanel.astro` — reaproveita o padrão de fetch já provado

```astro
---
// server-side: nada a fazer, o fetch acontece no client (dado muda em runtime)
---
<section id="dados-reais" class="data-panel" aria-live="polite" aria-busy="true">
  <p class="loading">Carregando…</p>
</section>
<script>
  import { renderMetricsPanel } from "../lib/metrics";
  void renderMetricsPanel();
</script>
```

---

## 6. Estratégia de testes

| Tipo | Escopo | Ferramenta |
|---|---|---|
| Typecheck | `astro check` (equivalente ao `tsc --noEmit` para `.astro`) | CI (`web-check`, ajustar comando) |
| Build | `npm run build` gera `dist/` servível | CI (`web-check`) |
| e2e — sem regressão | Dívida/INSS/fiscal renderizam ou degradam como antes | Playwright, adapta `card.spec.ts` |
| e2e — sem hardcode | Bundle final não contém valores literais conhecidos | Playwright, mesmo teste das 3 fatias |
| e2e — status rastreável (novo) | Todo `StatusEntry` renderizado tem `evidence` não-vazio no DOM (ex.: `data-evidence` attribute) ou pelo menos presente no código-fonte, verificado por teste unitário simples de `status.ts` | Playwright + teste de módulo TS |

Cobre AT1–AT9 do DEFINE.

---

## 7. Pipeline Architecture (contexto DE)

Não aplicável — feature de frontend, sem pipeline de dado novo. Reaproveita os 3 endpoints já
existentes sem mudança.

---

## 8. Quality gate (Fase 2)

- [x] Descoberta real feita — releitura completa e literal do mockup, compatibilidade de build confirmada por pesquisa real (`§0`)
- [x] ASCII diagram criado e claro (`§2`)
- [x] Pelo menos 1 decisão com racional completo (4 decisões, D1-D4)
- [x] Manifesto de arquivos completo (24 itens, PR1+PR2)
- [x] Agente atribuído a cada arquivo
- [x] Padrões de código sintaticamente corretos, prontos para copiar-adaptar
- [x] Estratégia de testes cobre os acceptance tests do DEFINE (AT1-AT9)
- [x] Sem dependência circular na arquitetura
- [x] Nenhum selo de status fabricado — cada um tem `evidence` real (`§0.4/0.5/0.6`)
- [x] DEFINE status → `✅ Complete (Designed)`

---

## 9. Handoff

Pronto para `/build .claude/sdd/features/DESIGN_LANDING_PAGE_ASTRO.md`.

---

## 10. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-06 | 1.0 | Criação a partir de `DEFINE_LANDING_PAGE_ASTRO.md`. Descoberta real (§0): releitura completa do mockup (texto literal de todas as 10 seções), status real de 15 módulos/12 componentes de arquitetura/8 fases do roadmap extraído de fatos reais (SHIPPED docs, Terraform), compatibilidade de build Astro/Dockerfile confirmada por pesquisa real. 4 decisões inline (D1-D4). Manifesto 24 itens. Status → Ready for Build. | /design (Claude Sonnet 5) |
