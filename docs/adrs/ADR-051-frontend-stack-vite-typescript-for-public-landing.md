# ADR-051 — Vite + TypeScript for the public Landing

## Status
Accepted

## Contexto
Esta decisão é parte do baseline arquitetural do BRASIL 2036 e deve ser lida com o `CONTEXTO.md`.
ADR-044 separou superfícies pública e autenticada sob um design system compartilhado, mas não
fixou a stack de frontend. A fatia `MVP_WALKING_SKELETON` (SPEC-033) precisa renderizar um card
público que busca o valor da métrica em runtime na API (nenhum número no bundle, ADR-012) e
consome o cliente TypeScript gerado do OpenAPI (ADR-024, SPEC-026). Os SLOs de LCP e
acessibilidade de PRD-001 valem desde o primeiro card.

## Decision drivers
- segurança e auditabilidade;
- reprodutibilidade;
- escalabilidade;
- custo operacional;
- aderência ao GCP;
- clareza para portfólio e agentes de código.

## Alternativas consideradas
### A. HTML + JavaScript sem build
Alternativa considerada e descartada: sem etapa de build não há como consumir o cliente
TypeScript gerado do OpenAPI de forma tipada, contrariando ADR-024/SPEC-026.

### B. Next.js
Alternativa considerada; SSR/BFF e superfície grande demais para uma landing estática. Pode ser
válida na fase de Portais completos, não na fatia inicial.

### C. Astro
Alternativa considerada; ótima para conteúdo estático, mas adiciona toolchain e ilhas de
hidratação para um único fetch. Reconsiderar quando a Landing tiver muitas seções (PRD-001 V1).

### D. Vite + TypeScript sem framework
Alternativa escolhida ou base para a decisão.

## Decisão
**Vite + TypeScript sem framework**, saída estática servida por imagem mínima no Cloud Run.
Cliente de API gerado com `openapi-typescript` a partir do `openapi.json` no CI.

## Por que
Menor superfície e menor payload de JavaScript para uma landing pública, favorecendo LCP; sem
custo de framework ou SSR; ainda TypeScript, então o cliente gerado é idiomático; build
reprodutível e servível por Cloud Run como estático.

## Consequências positivas
- comportamento mais explícito e testável;
- decisão documentada para novos desenvolvedores/agentes;
- redução de ambiguidade.

## Consequências negativas / custo aceito
Quando a Landing crescer para múltiplas seções interativas, é provável a migração para Astro ou
Next.js; a troca fica contida no diretório `web/`.

## Verificação
A decisão deve aparecer em SPECs, testes, CI ou políticas de repositório quando aplicável
(SPEC-033, workflow `api-web.yml`).

## Quando reconsiderar
Reconsiderar quando métricas operacionais, requisitos legais, custo, escala ou limitações de
plataforma demonstrarem que os decision drivers mudaram materialmente — em particular quando a
Landing exigir roteamento cliente, múltiplas seções interativas ou renderização no servidor.
