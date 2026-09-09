# BRAINSTORM — LANDING_PAGE_TABS

- **Feature:** LANDING_PAGE_TABS
- **Status:** ✅ Complete (Defined)

- **Fase:** 0 (Brainstorm)
- **Criado:** 2026-09-09
- **Idioma:** PT-BR (alinhado a `docs/discovery/`)
- **Próximo passo:** `/define .claude/sdd/features/BRAINSTORM_LANDING_PAGE_TABS.md`

> Nota: assets do plugin SDD ausentes — documento segue a lista de seções do skill `sdd-brainstorm`,
> mesmo padrão dos brainstorms anteriores.

---

## 1. Ideia

Pedido explícito do usuário: *"leia [Brasil_2036.pdf] e crie uma aba principal home. com estes
dados. na landpage. as demais informações deve ficar em outras abas."* O usuário forneceu
`Brasil_2036.pdf` (6 páginas) — um documento de contextualização/pitch da iniciativa, complementar
ao `CONTEXTO.md` já existente. Muito do conteúdo do PDF já existe na landing page shipada
(`LANDING_PAGE_ASTRO`) como seções de scroll único em `web/src/pages/index.astro` (Hero, DataPanel,
Proposal, ModuleGrid, PortalsGrid, Architecture, Roadmap, Benefits).

**Achado real que moldou a descoberta:** os 7 indicadores fiscais/macro da p.2 do PDF ("BRASIL HOJE
— CONTEXTO ECONÔMICO E FISCAL" — PIB projeção 2026, IPCA projeção 2026, Dívida Bruta/PIB 2026 e
2027, déficit primário, receita líquida, despesa total) citam fonte real (SPE/MF — Boletim
Macrofiscal jul/2026; Prisma Fiscal ago/2026), mas são de uma fonte **diferente** da que o projeto
já ingere via pipeline (`fiscal_receita`/`despesa`/`primario` vêm do Tesouro/"Resultado do Tesouro
Nacional"; `divida_bruta_pib` vem do BCB SGS série 13762 — valores observados mensais, não as
projeções do MF para 2026/2027). O `DataPanel.astro` já existente mostra 100% dado real via API do
próprio projeto — misturar os 2 conjuntos sem distinção violaria a disciplina "nunca fabricar"
(`ADR-012`) por confundir 2 fontes/naturezas de número diferentes como se fossem a mesma coisa. O
próprio PDF já reconhece isso: "Os valores abaixo são referências de agosto de 2026 e, no produto,
serão atualizados automaticamente pelas fontes oficiais" — ou seja, mesmo o documento-fonte trata
esses 7 números como referência estática por enquanto, não como dado vivo.

---

## 2. Contexto técnico

| Aspecto | Observação |
|---|---|
| **Landing atual** | `web/src/pages/index.astro` — 1 página Astro estática (`output: "static"`), scroll único, 8 componentes (`Hero`, `DataPanel`, `Proposal`, `ModuleGrid`, `PortalsGrid`, `Architecture`, `Roadmap`, `Benefits`), shipada em `LANDING_PAGE_ASTRO`. |
| **Mecanismo de evidência já existente** | `web/src/data/status.ts` — 15 entradas de módulo + 12 de arquitetura + 8 fases de roadmap, cada uma com `status` (`real`/`parcial`/`planejado` ou `concluida`/`em_andamento`/`nao_iniciada`) + `evidence` (citação real obrigatória, testada por e2e). Conteúdo puramente narrativo (Proposal, Benefits, os 7 cards fiscais novos) não passa por esse mecanismo — não são "status de entrega", são fatos/proposta/citação direta. |
| **`DataPanel.astro`** | Já busca dado real via `web/src/lib/metrics.ts` contra os endpoints `/v1/metrics/*`/`/v1/simulations/debtlab/*` já em produção — não precisa mudar, só migrar de posição (scroll único → dentro de uma aba). |
| **Conteúdo novo do PDF sem equivalente atual** | 3 cenários de referência (Estresse/Tendencial/"Brasil nos Trilhos", p.3); seção "Acessos, segurança e governança" mais detalhada (RBAC+ABAC, MFA/SSO, auditoria, governança de IA, p.4); "Evolução da landing page" em 5 versões (p.5); "Expectativas com a iniciativa" + "Questão central do Brasil 2036" (p.6). |

---

## 3. Discovery

| # | Pergunta | Resposta | Impacto no desenho |
|---|---|---|---|
| 1 | O que exatamente são "estes dados" que vão na Home? | **P.1 (proposta) + p.2 (os 7 cards fiscais)** — confere exatamente com o que o próprio PDF descreve como a v1 da landing ("Marca + proposta + Brasil Hoje..."). | Home fica pequena e focada — não é o PDF inteiro. |
| 2 | Como tratar a tensão entre os 7 números do PDF (fonte real, não ingerida) e o `DataPanel` (dado real já ingerido)? | **Cards estáticos curados na Home**, citando a fonte exata do PDF + a mesma ressalva de atualização futura; `DataPanel` continua mostrando os dados reais já ingeridos, em outra aba, sem misturar os 2 conjuntos. | Home tem 2 tipos de "real" claramente rotulados e nunca combinados na mesma UI. |
| 3 | Como agrupar as 6 seções que saem da Home (`DataPanel`, `ModuleGrid`, `PortalsGrid`, `Architecture`, `Roadmap`, `Benefits`) nas "demais abas"? | **5 abas temáticas** (Home; Dados Reais; Módulos & Portais; Arquitetura & Roadmap; Sobre) — agrupamento por tema relacionado, menos cliques que 1 aba por componente. | Manifesto de arquivos menor; navegação mais simples. |
| 4 | Onde entra o conteúdo novo do PDF sem equivalente atual (cenários, acessos/governança, evolução da landing, questão central)? | **Incorporado dentro das abas temáticas já definidas** — cenários em "Módulos & Portais" (perto do DebtLab/Policy Lab); evolução da landing + questão central em "Arquitetura & Roadmap"; acessos/governança expande a seção de arquitetura existente. Nenhuma aba nova só pra isso. | Sem aba extra; conteúdo novo vira mais texto dentro das abas já desenhadas. |
| 5 | Mecanismo técnico das abas? | **Client-side, 1 página só**, JS mínimo pra mostrar/esconder cada aba, hash na URL (`#home`, `#dados`, etc.) pra deep-link. | Mantém `output: "static"`, 1 build, mesmo modelo de hospedagem — sem migrar pra multi-rota. |

---

## 4. Inventário de amostras

| Tipo | Disponível? | Uso previsto |
|---|---|---|
| Conteúdo real da Home (p.1+p.2) | Sim — `Brasil_2036.pdf`, lido nesta sessão, texto extraído integralmente | Proposta (p.1) + os 7 cards fiscais com valores/fontes exatos (p.2), reproduzidos literalmente, não parafraseados/estimados. |
| Conteúdo real das demais abas | Sim — 6 componentes Astro já existentes, código real no repo | Migração de posição, não de conteúdo — sem reescrever o que já existe. |
| Conteúdo novo (cenários/acessos/evolução/questão central) | Sim — texto real do PDF, páginas 3-6 | Incorporado como texto adicional dentro das abas já desenhadas (`§3` item 4). |
| Precedente de UI com abas no projeto | Não — landing atual é scroll único, sem precedente de navegação por abas. | Padrão novo de CSS/JS a desenhar no `/design`, sem KB específico de "abas" no projeto ainda. |

---

## 5. Abordagens exploradas

### Abordagem A — Home focada (p.1+p.2) + 4 abas temáticas + abas client-side numa página só ⭐ Escolhida
- **O quê:** `index.astro` ganha uma barra de abas (`Home`/`Dados Reais`/`Módulos & Portais`/
  `Arquitetura & Roadmap`/`Sobre`), JS mínimo alterna `hidden`/visível por aba, hash na URL sincroniza
  com a aba ativa. Home = `Hero`/`Proposal` (adaptados) + novo componente de cards fiscais
  estáticos citando o PDF. As 6 seções existentes migram de posição, sem reescrita de conteúdo. O
  conteúdo novo do PDF (cenários, acessos/governança, evolução da landing, questão central) vira
  texto adicional dentro das 2 abas temáticas certas.
- **Prós:** escopo pequeno e claro (migração de posição + 1 seção nova pequena); mantém
  `output: "static"`/1 build/mesmo hosting; resolve a tensão de fonte de dado de forma explícita
  (2 rótulos de proveniência, nunca misturados); reaproveita 100% do mecanismo de evidência já
  existente pro que já é badge-ado.
- **Contras:** é a 1ª vez que a landing tem navegação por abas — nenhum precedente de CSS/JS/teste
  e2e no projeto pra esse padrão especificamente.
- **Confiança:** 0.85 — cada decisão foi validada explicitamente com o usuário nesta sessão, sem
  suposição; a única incerteza técnica real é o padrão de abas em si, que o `/design` resolve.

### Abordagem B — PDF inteiro na Home, resto fica "demais abas" genéricas
- **Por que não escolhida:** rejeitada explicitamente pelo usuário na 1ª pergunta de descoberta —
  a Home ficaria grande demais e duplicaria conteúdo que já tem lugar certo nas abas temáticas.
- **Confiança:** 0.5 (mais simples de decidir, mas não é o que o usuário quer).

### Abordagem C — Misturar `DataPanel` (dado real do pipeline) com os 7 cards do PDF na mesma seção
- **Por que não escolhida:** rejeitada explicitamente na 2ª pergunta de descoberta — misturaria 2
  fontes/naturezas de número diferentes (projeção do MF vs. observado do pipeline do projeto) na
  mesma UI sem distinção clara, risco real de confundir o usuário final sobre o que é o quê.
- **Confiança:** 0.4 (tecnicamente mais simples, mas risco real de credibilidade pro produto).

### Abordagem D — 1 rota Astro por aba (multi-página)
- **Por que não escolhida:** rejeitada explicitamente na pergunta de mecanismo técnico — mudaria o
  modelo de URL/navegação da landing já shipada sem necessidade real nesta fatia.
- **Confiança:** 0.7 (melhor pra SEO por página no longo prazo, mas não é a escolha do usuário agora).

---

## 6. Itens removidos / adiados (YAGNI)

| Item | Por que fora desta fatia | Vai para |
|---|---|---|
| Migrar pra rotas Astro multi-página | Rejeitado explicitamente — abas client-side numa página só é suficiente e mais simples. | Reavaliar se SEO por página virar prioridade real no futuro. |
| Conectar os 7 cards fiscais a uma API/pipeline real (SPE/MF/Prisma Fiscal) | Fora do pedido desta fatia (conteúdo/UI, não ingestão de dado novo); ingerir uma fonte nova exigiria descoberta real própria (formato do Boletim Macrofiscal/Prisma Fiscal, direito de uso), fora do escopo de "ler o PDF e reorganizar a landing". | `EPIC-008`/fatia de dado futura, se houver demanda real de manter os 7 números vivos. |
| Aba nova só para cenários/evolução da landing/questão central | Rejeitado explicitamente — conteúdo novo entra dentro das abas temáticas já desenhadas, não em abas extras. | Reavaliar se o conteúdo crescer o suficiente pra justificar uma aba própria. |
| Reescrever/expandir o conteúdo das 6 seções existentes | Fora de escopo — esta fatia é reposicionamento estrutural (abas), não reescrita de conteúdo já shipado. | Fatia futura de conteúdo, se pedida. |

---

## 7. Requisitos-rascunho (para o `/define`)

- **R1.** Barra de abas nova em `index.astro` (`Home`/`Dados Reais`/`Módulos & Portais`/
  `Arquitetura & Roadmap`/`Sobre`), JS mínimo (sem framework novo), hash na URL sincronizado com a
  aba ativa, aba padrão = Home.
- **R2.** Componente novo (`FiscalSnapshot.astro` ou equivalente) com os 7 cards fiscais/macro da
  p.2 do PDF, valores e citações reproduzidos literalmente (PIB +2,3%; IPCA 5,1%; Dívida
  Bruta/PIB 83,0% [2026] e 86,77% [2027]; déficit primário R$59,145bi; receita líquida R$2,574tri;
  despesa total R$2,624tri), cada card citando a fonte real exata (Boletim Macrofiscal jul/2026 ou
  Prisma Fiscal ago/2026) + a ressalva "referência de agosto/2026, atualização automática futura"
  (texto do próprio PDF, não parafraseado a ponto de perder o sentido).
- **R3.** `Hero`/`Proposal` migram pra dentro da aba Home, adaptados ao layout de abas (sem
  reescrever o texto).
- **R4.** `DataPanel` migra pra aba "Dados Reais", sem mudança de comportamento (continua buscando
  dado real via API).
- **R5.** `ModuleGrid`+`PortalsGrid` migram pra aba "Módulos & Portais"; texto dos 3 cenários de
  referência (Estresse/Tendencial/Brasil nos Trilhos, p.3 do PDF) incorporado nessa aba.
- **R6.** `Architecture`+`Roadmap` migram pra aba "Arquitetura & Roadmap"; seção de Acessos/
  Governança (RBAC+ABAC, MFA/SSO, auditoria, governança de IA, p.4) expande a seção de arquitetura;
  "Evolução da landing page" (5 versões, p.5) + "Questão central do Brasil 2036" (p.6) incorporados
  nessa aba.
- **R7.** `Benefits` migra pra aba "Sobre"; "Expectativas com a iniciativa" (p.6) incorporado nessa
  aba.
- **R8.** Nenhum número dos 7 cards fiscais (R2) pode ser citado como vindo de `metric_provenance`/
  do pipeline do projeto — rótulo de fonte explicitamente distinto do `DataPanel` (`ADR-012`).
- **R9.** e2e: navegação entre as 5 abas funciona (clique + hash direto na URL); todo selo/evidência
  já testado hoje (`status.ts`) continua passando sem alteração de comportamento.
- **R10.** Sem regressão visual/de conteúdo nas 6 seções migradas — mesmo texto, mesmos dados,
  só posição diferente.

---

## 8. Decisões autônomas registradas

| Decisão | Motivo |
|---|---|
| Nome da feature: `LANDING_PAGE_TABS` | Reflete a mudança estrutural real (navegação por abas), não o documento-fonte (`Brasil_2036.pdf` é insumo, não a entrega). |
| Próximo ADR livre: nenhum previsto ainda | Esta fatia é reposicionamento de UI/conteúdo, não uma decisão arquitetural nova que precise de ADR — `/design` confirma se algo emergir (ex.: padrão de abas) que mereça registro. |

---

## 9. Questões abertas (resolver no `/define` ou `/design`)

1. **Texto exato dos cards fiscais** — reproduzir literalmente o texto do PDF ou adaptar
   levemente pro tom da landing (mantendo valor+fonte intactos)? `/design` decide o texto final.
2. **Onde visualmente a barra de abas fica** (abaixo do `Nav` existente, substituindo-o, ou
   integrada)? `/design`.
3. **Acessibilidade das abas** (ARIA roles, navegação por teclado) — `/design` confirma o padrão.
4. **Se algum item do `status.ts` precisa de entrada nova** por causa do conteúdo incorporado
   (cenários, acessos/governança) — `/design` confirma se é caso de badge ou só texto narrativo.

---

## 10. Domínios de KB para a Fase Define

- **Precedente direto:** `web/src/pages/index.astro`, `web/src/components/*.astro` (todos os 8
  componentes existentes), `web/src/data/status.ts` (mecanismo de evidência), `web/src/lib/
  metrics.ts` (dado real do `DataPanel`), `web/src/styles/global.css`.
- **ADRs:** `ADR-058` (Astro supersede Vite/TS), `ADR-012` (nunca fabricar — motiva R8), `ADR-041`
  (Landing é produto de Fase 1).
- **Arquivo-fonte:** `Brasil_2036.pdf` (fornecido pelo usuário, texto extraído integralmente nesta
  sessão).

---

## 11. Quality gate (Fase 0)

- [x] Mínimo de 3 perguntas de discovery feitas e respondidas (5 feitas)
- [x] Pergunta de amostras feita — PDF real já lido e conteúdo confirmado disponível
- [x] Pelo menos 2 abordagens exploradas com trade-offs (A, B, C, D)
- [x] Usuário confirmou explicitamente a abordagem escolhida (A) em múltiplos checkpoints
- [x] YAGNI aplicado — seção de itens removidos preenchida (4 itens)
- [x] Mínimo de 2 validações incrementais concluídas (checkpoint de agrupamento de abas; checkpoint
  de confirmação do desenho consolidado completo)
- [x] Domínios de KB identificados para o Define
- [x] Requisitos-rascunho prontos para o `/define` (R1–R10)

---

## 12. Handoff

Pronto para `/define .claude/sdd/features/BRAINSTORM_LANDING_PAGE_TABS.md`.
