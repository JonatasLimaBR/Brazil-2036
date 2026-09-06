# ADR-058 — Landing page migra para Astro, supera `ADR-051`

## Status
Accepted

## Contexto
Esta decisão é parte do baseline arquitetural do BRASIL 2036 e deve ser lida com o `CONTEXTO.md`.
`ADR-051` escolheu Vite + TypeScript sem framework para a Landing pública, com uma cláusula
explícita de reconsideração: "reconsiderar quando... a Landing exigir... múltiplas seções
interativas". O usuário forneceu um mockup completo (`docs/landpage.png`) pedindo a atualização
da Landing para refletir a visão de produto inteira: nav, hero, painel de dados, proposta, grid
de 15 módulos, grid de 8 portais, diagrama de 12 componentes de arquitetura, roadmap de 8 fases,
grid de 6 benefícios e rodapé — 10 seções, contra as 3 simples de hoje (card da dívida + 2
módulos). Esse é exatamente o gatilho que `ADR-051` já previa.

Achado real que também motiva esta fatia (`LANDING_PAGE_ASTRO`, `DESIGN §0`): parte do mockup
("Command Center" com índices/alertas fictícios) não pode ser implementada literalmente sem
violar a regra inegociável de nunca fabricar métrica oficial (`ADR-012`) — resolvido
substituindo por um painel de dados reais, não coberto por este ADR (é uma decisão de produto,
não de stack).

## Decision drivers
- os mesmos de `ADR-051`: segurança/auditabilidade, reprodutibilidade, escalabilidade, custo
  operacional, aderência ao GCP, clareza para portfólio e agentes de código;
- minimizar JavaScript enviado ao cliente para seções que não têm dado ao vivo (a maioria das
  10 seções novas é 100% estática).

## Alternativas consideradas
### A. Manter Vite + TypeScript sem framework, empilhando `render*()` manuais
Considerada; tecnicamente viável (mesmo padrão de `renderInssModule`/`renderFiscalModule` já
provado), mas o usuário optou por antecipar a migração já prevista no `ADR-051` em vez de
continuar empilhando seções manuais (`BRAINSTORM_LANDING_PAGE_ASTRO.md §5`, Abordagem B).

### B. Next.js
Já considerada e descartada em `ADR-051` por SSR/BFF desnecessário para uma landing estática;
nada mudou nesse racional.

### C. Astro (`output: "static"`, sem SSR)
Alternativa escolhida.

## Decisão
Migrar `web/` para **Astro**, modo `output: "static"` (o default do framework, sem SSR).
`astro.config.mjs` configura `vite: { envPrefix: ["VITE_"] }` para preservar a variável
`VITE_API_URL` já usada em `.github/workflows/api-web.yml`, sem renomear a variável de CI.
Seções sem dado ao vivo (proposta, grids de módulos/portais, arquitetura, roadmap, benefícios,
rodapé) são `.astro` puramente estáticos, sem JavaScript de cliente; só o painel de dados reais
(`DataPanel.astro`) usa um `<script>` client-side, reaproveitando a lógica de fetch já provada
(consolidada em `src/lib/metrics.ts`, antes espalhada em `main.ts`/`inss.ts`/`fiscal.ts`).

**Confirmado por pesquisa real (não suposição) antes de migrar:** a saída estática do Astro
(`dist/`) é um substituto direto da saída do Vite no `Dockerfile`/`nginx` já existentes — **zero
mudança de infraestrutura de deploy**.

## Por que
Resolve a reconsideração de stack já prevista no próprio `ADR-051`, no momento exato em que a
Landing cresce como a cláusula de reconsideração descrevia; ilhas de hidratação seletiva do
Astro (`client:load` só no painel de dados) mantêm o racional original de `ADR-051` (menor
payload de JS) mesmo com 10 seções, em vez de abandoná-lo.

## Consequências positivas
- Zero mudança de `Dockerfile`/`api-web.yml`/infraestrutura de deploy (confirmado, não suposto).
- Só a seção com dado real carrega JavaScript de fetch — as ~9 seções estáticas são HTML puro.
- `ADR-051` continua no repositório, íntegro, com nota de superseded (não apagado nem
  reescrito — `CLAUDE.md`: nunca substituir um ADR silenciosamente).

## Consequências negativas / custo aceito
- Novo toolchain (`astro check`, `.astro` components) a manter, substituindo o `tsc --noEmit`
  simples de antes.
- `web/package.json`/`tsconfig.json`/`astro.config.mjs` mudam de forma não trivial — mitigado
  por toda a suíte de testes (typecheck, build, e2e) confirmada verde contra a API real de
  produção antes do merge.

## Verificação
`npm run typecheck` (`astro check`), `npm run build` (gera `dist/` idêntico em formato ao
anterior), `npm run e2e` rodado localmente contra a API real de produção
(`https://br2036-api-gzt6fzwoda-rj.a.run.app`) — 4/4 passam, incluindo a asserção de "nenhum
valor hard-coded no bundle" (regex ajustado de `assets/` para `_astro/`, caminho real de saída
do Astro).

## Quando reconsiderar
Se a Landing precisar de SSR de verdade (conteúdo personalizado por usuário autenticado) ou de
roteamento client-side entre múltiplas páginas reais (não apenas âncoras numa página só) — nesse
ponto, Astro em modo `static` deixa de ser suficiente e a migração para SSR/Next.js volta à mesa.
