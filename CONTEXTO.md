# CONTEXTO.md — BRASIL 2036 — NOS TRILHOS
Versão: 5.0
Idioma deste arquivo: PT-BR
Função: memória canônica do produto e contexto de handoff para pessoas e agentes de código.

---

## 0. COMO USAR ESTE ARQUIVO

Este documento reúne as decisões e o contexto acumulado do projeto BRASIL 2036 desde o início da concepção.
Ele não substitui PRDs, SPECs ou ADRs. A hierarquia é:

1. `CONTEXTO.md` — visão integral e memória do projeto.
2. `docs/discovery/` — jornadas, riscos, limites e métricas antes do código.
3. `docs/prd/` — problema, público, V1, fora de escopo e sucesso.
4. `docs/adrs/` — decisões arquiteturais, alternativas descartadas e consequências.
5. `docs/specs/` — comportamento implementável sem ambiguidade.
6. `docs/risks/` — risco → controle → teste.
7. `tests/` — prova automatizada do contrato.
8. Código — implementação, nunca fonte primária de intenção.

Regra central:
> Discovery define risco e valor. PRD define o problema. ADR registra a decisão. SPEC elimina ambiguidade. Teste prova o contrato. Código implementa. Eval bloqueia regressão.

---

# 1. IDENTIDADE

Nome: **BRASIL 2036 — Nos Trilhos**

Subtítulo:
**Plataforma Nacional de Inteligência Econômica, Fiscal e Social**

Slogans avaliados:
- Dados públicos transformados em inteligência para o futuro do Brasil.
- Dados que explicam o presente. Inteligência que ajuda a construir 2036.

Posicionamento:
Plataforma de dados + modelos + conhecimento + simulação + agentes para explicar o Brasil atual, reconstruir a trajetória histórica, projetar cenários e apoiar decisões baseadas em evidências.

O produto não é partidário e não apresenta cenários como promessas políticas.

---

# 2. PROBLEMA

O Brasil publica grande quantidade de dados públicos, porém esses dados:
- estão distribuídos por muitos órgãos;
- têm formatos diferentes;
- possuem diferentes periodicidades;
- usam conceitos e chaves heterogêneas;
- nem sempre têm metadados suficientes;
- são difíceis de cruzar em análises multidisciplinares;
- raramente têm provenance ponta a ponta até o indicador final.

Perguntas nacionais importantes atravessam vários domínios.

Exemplo:
"Qual o impacto do envelhecimento populacional sobre benefícios do INSS, resultado fiscal, dívida pública, emprego e crescimento até 2036?"

Para responder com qualidade são necessários:
demografia + emprego + salários + formalização + Previdência + receita + despesa + juros + PIB + dívida.

BRASIL 2036 existe para integrar essas dimensões.

---

# 3. OBJETIVOS

1. Explicar a situação econômica, fiscal e social presente.
2. Mostrar como o país chegou ao estado atual.
3. Integrar dados abertos oficiais.
4. Criar indicadores canônicos e rastreáveis.
5. Projetar tendências e incertezas.
6. Simular políticas e choques.
7. Analisar relações causais quando metodologicamente defensável.
8. Criar Digital Twins nacionais, estaduais e municipais.
9. Oferecer copilotos e agentes especializados, sempre fundamentados em dados/tools.
10. Aumentar transparência e reutilização de dados abertos.
11. Permitir API e ecossistema para pesquisa, governo e empresas.
12. Medir impacto do próprio reúso de dados abertos.

---

# 4. ADEQUAÇÃO AO 2º CONCURSO DE REÚSO DE DADOS ABERTOS DA CGU — 2026

A iniciativa foi adaptada para ser submetida ao 2º Concurso de Reúso de Dados Abertos da CGU.

Requisitos relevantes confirmados:
- inscrições: 29/06/2026 a 11/09/2026;
- pelo menos um dataset precisa estar catalogado no Portal Brasileiro de Dados Abertos;
- submissão tem duas etapas: formulário e publicação/homologação do reúso no Portal;
- deve informar URLs dos conjuntos utilizados;
- exemplos aceitos incluem apps, modelos de IA, plataformas, painéis, produtos e ferramentas.

Critérios de julgamento publicados:
- Apresentação — peso 2
- Inovação — peso 2
- Transparência e controle social — peso 2
- Foco em pessoas/impacto — peso 2
- Duas ou mais fontes abertas — peso 1
- Uso de ferramentas tecnológicas — peso 1
- Inclusividade — peso 1

Estratégia BRASIL 2036 para pontuação:
- apresentação: landing interativa, mapas, séries, simuladores;
- inovação: Digital Twin + Policy Lab + agentes + provenance;
- transparência: fonte, metodologia, lineage e Trust Score;
- impacto: cidadão, gestor, pesquisador, estados e municípios;
- múltiplas fontes: dados.gov.br + IBGE + BCB + Tesouro + INSS etc.;
- tecnologia: GCP, BigQuery, Vertex AI, agents;
- inclusividade: portal público, acessibilidade, linguagem simples.

---

# 5. PAPEL DO DADOS.GOV.BR

O Portal Brasileiro de Dados Abertos NÃO será tratado apenas como uma fonte de dados.

Ele é o **hub nacional de discovery/catalogação**.

Arquitetura:
dados.gov.br
→ Open Data Discovery Engine
→ Dataset Registry
→ classificação
→ Resource Resolver
→ Adaptive Connectors
→ GCS RAW
→ BigQuery Bronze
→ Silver
→ Gold
→ Semantic Layer / Models / Graph / RAG
→ módulos
→ simuladores
→ agentes
→ portais.

Importante:
o Portal pode catalogar recursos hospedados pelo órgão produtor. O sistema separa:
- metadata discovery;
- resource discovery;
- ingestion do recurso real.

---

# 6. FONTES PRIORITÁRIAS

P0:
- Portal Brasileiro de Dados Abertos
- IBGE
- Banco Central
- Tesouro Nacional
- INSS / Previdência
- SICONFI
- CAGED
- PNCP
- Transferegov

P1:
- RAIS
- DATASUS
- INEP
- ComexStat
- IPEA
- Receita Federal
- BNDES
- ANEEL
- ANP
- ONS
- transportes/agências
- TSE quando houver módulo eleitoral futuro

Datasets concretos identificados no Portal:
1. Benefícios Emitidos — INSS
2. Benefícios mantidos — Plano de Dados Abertos Jun/2023 a Jun/2027
3. Benefícios indeferidos — INSS
4. Glossários dos Arquivos de Benefícios
5. Dívida Consolidada dos Estados e do Distrito Federal
6. Estoque do Tesouro Direto

Evitar depender como núcleo de fontes indisponíveis/descontinuadas.

---

# 7. OPEN DATA HUB

Componentes obrigatórios:
- Dataset Discovery
- Dataset Registry
- Resource Resolver
- Adaptive Connector Framework
- Format Detector
- Data Contract
- Schema Drift Quarantine
- Data Trust Score
- Source Health
- Provenance
- Open Data Control Center
- semantic catalog
- discovery agent
- Open Data Impact metrics

`br2036_control.dataset_registry`:
- dataset_id
- dataset_name
- organization
- organization_id
- theme
- tags
- source_catalog
- source_url
- resource_id
- resource_name
- resource_url
- resource_format
- update_frequency
- last_catalog_update
- last_resource_update
- license
- br2036_domain
- br2036_module
- ingestion_status
- quality_score
- active

Data Trust Score deve combinar:
- freshness
- completeness
- availability
- documentation
- consistency

Dado de qualidade baixa não entra automaticamente em modelos de produção.

---

# 8. PRINCÍPIOS DE DADOS

BigQuery = verdade quantitativa analítica.
AlloyDB = estado operacional, memória transacional, approval/checkpoints e RAG relacional/vetorial quando adequado.
Graph layer = relações/ontologia.
Gemini/Vertex AI = reasoning, síntese e orquestração.
Cloud Storage = RAW imutável.
Dataform = transformação e testes SQL-first.
Knowledge Catalog = metadata, contexto, lineage e descoberta governada.

Regra:
> LLM nunca inventa número. LLM chama ferramenta/modelo.

Toda resposta quantitativa deve possuir:
- value
- unit
- source
- reference_date
- model
- model_version
- scenario
- confidence
- assumptions

---

# 9. ARQUITETURA GCP

Princípio: serverless-first.

Serviços:
- Cloud Storage
- BigQuery
- Dataform
- Cloud Run
- Cloud Run Jobs
- Cloud Scheduler
- Workflows
- Pub/Sub
- Dataflow quando streaming for necessário
- AlloyDB AI
- Vertex AI
- Gemini
- Agent Engine / capacidades agentic
- Knowledge Catalog
- API Gateway
- Identity Platform / OIDC / SAML
- IAM
- KMS
- Secret Manager
- Cloud Armor
- VPC/PSC
- Cloud Monitoring
- Cloud Logging
- Trace/Error Reporting

GKE não entra na V1 sem necessidade comprovada.

Projetos/ambientes:
- shared
- network
- security
- data-dev/stg/prod
- ai-dev/stg/prod
- app-dev/stg/prod
- observability

---

# 10. DATA PLATFORM

Cloud Storage:
- landing
- raw
- curated
- documents
- model-artifacts
- archive

BigQuery:
- control
- bronze
- silver
- gold
- macro
- fiscal
- inss
- labor
- municipal
- state
- health
- education
- tax
- procurement
- infrastructure
- social
- semantic
- features
- forecast
- simulation
- policy
- graph
- agents
- audit

Chave territorial principal:
`municipality_ibge_code`

Gold products:
- gold_brazil_current
- gold_macro_monthly
- gold_fiscal_current
- gold_debt_trajectory
- gold_inss_current
- gold_inss_projection
- gold_labor_current
- gold_state_profile
- gold_municipality_profile
- gold_public_procurement
- gold_brazil_on_track

---

# 11. MÓDULOS DO PRODUTO

## M01 Macro Economic Twin
PIB, inflação, Selic, câmbio, consumo, investimento, crédito, comércio, produtividade.

## M02 Fiscal & DebtLab
Receitas, despesas, primário, dívida, juros, trajetória e sustentabilidade.

Equação-base de dívida:
d[t+1] = ((1+r)/(1+g))*d[t] - pb[t]

## M03 Previdência & INSS
Benefícios, contribuintes, receitas, despesas, déficit, demografia, indeferimentos, territorialidade e projeção.
É módulo integrado, não produto separado.

Loop causal:
demografia → beneficiários → despesa RGPS → primário → financiamento → dívida → juros → investimento → PIB.

## M04 Trabalho & Renda
Emprego, admissões, desligamentos, salários, formalização, CNAE, habilidades.

## M05 Produtividade & Competitividade
Produtividade, capital, educação, tecnologia, investimento.

## M06 Saúde
Capacidade, internações, estabelecimentos, epidemiologia, demanda.

## M07 Educação & Capital Humano
Matrícula, desempenho, escolaridade, técnico, superior.

## M08 Estados & Municípios
27 State Twins + caminho para 5.570 Municipal Twins.

## M09 Investimento Público / Infraestrutura
Projetos, execução, ROI, oportunidade e gargalos.

## M10 Compras Públicas
Contratos, fornecedores, preços, concentração, eficiência.

## M11 Tributação
Arrecadação, base econômica, efeitos de reforma.

## M12 Social
Renda, desigualdade, pobreza e benefícios.

## M13 Fraud & Anomaly Intelligence
Gera sinais e priorização de revisão. Nunca acusa ou pune automaticamente.

## M14 Policy Lab
Cenários, Monte Carlo, causal, sliders e comparison.

## M15 Brasil 2036 Command Center
On-Track Index, Risk Radar, Early Warning, cenários, recomendações.

## M16 Agent Center
Agentes, tools, traces, versions, evals, permissions.

## M17 Admin Center
Users, Organizations, Roles, Sources, Pipelines, Quality, Models, Agents, Prompts, APIs, Security, Costs, Audit, Feature Flags.

## M18 Open Data Impact
Datasets reutilizados, órgãos conectados, consultas, simulações, indicadores derivados e usuários.

---

# 12. SIMULADORES

SIM-001 Macroeconômico 2036
SIM-002 DebtLab / Dívida Pública
SIM-003 Fiscal
SIM-004 Previdência / RGPS
SIM-005 Demográfico
SIM-006 Formaliza Brasil
SIM-007 Trabalho & Renda
SIM-008 Produtividade
SIM-009 Investimento Público Optimizer
SIM-010 Infraestrutura
SIM-011 Municipal Fiscal Doctor
SIM-012 State Fiscal Twin
SIM-013 Tributário
SIM-014 Reforma Tributária / Split Payment
SIM-015 Saúde / Capacity
SIM-016 Educação / Capital Humano
SIM-017 Compras Públicas / Eficiência
SIM-018 Choques Externos
SIM-019 Monte Carlo Global
SIM-020 Policy Simulator
SIM-021 Policy Optimizer
SIM-022 Opportunity Cost AI
SIM-023 Brasil On-Track Simulator
SIM-024 Early Warning Stress Simulator

Todos os simuladores:
- executam fora do LLM;
- persistem parâmetros;
- persistem model version;
- marcam saída como SIMULATED;
- guardam premissas;
- suportam reprodutibilidade;
- não publicam automaticamente.

---

# 13. ANALYTICS, FORECAST E CAUSAL

Forecast champion/challenger:
- Naive
- ARIMA
- ARIMA-XREG
- TimesFM
- XGBoost/custom
- Vertex AI custom model quando necessário

Métricas:
- MAE
- MAPE
- RMSE
- Bias

Causal:
- Difference-in-Differences
- Synthetic Control
- Double ML
- Causal Forest
- IV quando pressupostos forem defensáveis

Monte Carlo:
P10/P25/P50/P75/P90 e probabilidades.

Policy Optimizer:
otimização multiobjetivo com pesos e restrições declarados.
Nunca apresenta "melhor política" sem explicitar função objetivo e pesos.

---

# 14. KNOWLEDGE / RAG / ONTOLOGIA

Documentos:
- leis
- decretos
- portarias
- notas técnicas
- relatórios
- DOU
- TCU
- BCB
- Tesouro
- IPEA
- PPA
- LDO
- LOA

Entidades:
Country, Region, State, Municipality, Company, GovernmentBody, Program, Policy, Contract, Benefit, Indicator, Dataset.

Relações:
BELONGS_TO, FUNDS, RECEIVES, CONTRACTS, PAYS, CONTRIBUTES_TO, IMPACTS, DEPENDS_ON, SOURCE_OF.

RAG híbrido:
lexical + vector + metadata filters.
Nunca vector-only por padrão para conteúdo legal/fiscal.

---

# 15. PORTAIS

## Público
Sem login: Brasil Hoje, histórico, indicadores, mapas, fontes, metodologia, cenários públicos, roadmap.

## Executivo
On-Track, riscos, alertas, cenários, recomendações.

## Analítico
Filtros, séries, comparação, exportação, exploração de datasets.

## INSS
Benefícios, receitas/despesas, demografia, indeferimentos, projeções.

## Estados
Perfis e Digital Twins.

## Municípios
Perfis e Digital Twins progressivos.

## Policy Lab
Simulações e comparison.

## Agent Center
Conversas, tools, traces e capability info.

## Developer/API
OpenAPI, exemplos, SDKs e data products.

## Admin
Controle completo da plataforma.

---

# 16. LANDING PAGE — PRIMEIRA ENTREGA

Não é apenas marketing; é a primeira versão do Portal Público.

Seções:
1. Hero
2. Brasil Hoje
3. Como chegamos aqui?
4. Desafios estruturais
5. O que acontece se nada mudar?
6. Cenário "Nos Trilhos"
7. Como chegar lá?
8. Módulos
9. Digital Twins
10. Policy Lab
11. IA/Agentes
12. Arquitetura GCP
13. Dados e fontes
14. Roadmap
15. Metodologia
16. Governança, transparência, neutralidade
17. CTA

Cada métrica:
- valor
- fonte
- data
- unidade
- metodologia
- update timestamp

Nunca hard-code de indicador atual para produção.

Identidade visual:
verde/amarelo/azul/branco; institucional, não partidária.

---

# 17. PERFIS E ACESSOS

RBAC + ABAC.

Perfis:
- Public
- Viewer
- Analyst
- Economist
- Simulator
- Executive/Manager
- Researcher
- Data Steward
- Data Engineer
- ML Engineer
- Agent Manager
- Organization Admin
- Platform Admin
- Security Admin
- Auditor/Compliance
- API Consumer/Developer

Atributos:
- organization
- domain
- data classification
- environment
- requested action

Capabilities:
VIEW_DATA
EXPORT_DATA
RUN_FORECAST
RUN_SIMULATION
CREATE_SCENARIO
USE_AGENT
MANAGE_AGENT
MANAGE_MODEL
ADMIN_USERS
PUBLISH_SCENARIO
MANAGE_SECURITY

MFA obrigatório para perfis privilegiados.

---

# 18. AGENTES DO PRODUTO

Brasil2036 Orchestrator
- Macro Agent
- Fiscal Agent
- Debt Agent
- INSS Agent
- Labor Agent
- Municipal Agent
- Health Agent
- Education Agent
- Tax Agent
- Procurement Agent
- Infrastructure Agent
- Forecast Agent
- Causal Agent
- Policy Agent
- Open Data Discovery Agent

Começar com um Data Analyst Agent + poucos especialistas no MVP.

Tools:
- query_bigquery
- get_metric
- search_documents
- search_graph
- run_forecast
- run_causal_analysis
- run_simulation
- get_provenance

---

# 19. BENCHMARK AGENTIC — "VENDINHA"

Referência fornecida:
Vendinha — Agente de Vendas de Ponta a Ponta.

O que absorver:
1. separar agentes por permissão, não por prompt;
2. agente read-only simplesmente não recebe write tools;
3. ação irreversível pausa workflow;
4. aprovação é estado persistido, não mero modal de UI;
5. observabilidade desde as primeiras specs;
6. PII mascarada antes do tracing;
7. FastAPI → Pydantic → OpenAPI → TypeScript client;
8. harness versionado;
9. `CLAUDE.md` enxuto;
10. skills vendorizadas e pinadas;
11. `/verificar-spec` executado em sessão nova;
12. reviewer não corrige o que revisa;
13. evals bloqueiam merge;
14. risco sem teste automatizado não é requisito de verdade.

Não copiar automaticamente:
- LangGraph
- Qdrant
- React/Vite
- Langfuse
- Postgres como warehouse

Tecnologia só entra por ADR.

---

# 20. SECURITY BY ARCHITECTURE

Princípio:
> Capability proibida não é descrita no prompt; ela não existe no toolset.

Classes:
LEVEL 0 READ
LEVEL 1 COMPUTE
LEVEL 2 DRAFT
LEVEL 3 PUBLISH
LEVEL 4 PRIVILEGED
LEVEL 5 SECURITY

READ:
consultar métricas, documentos, graph.

COMPUTE:
forecast, causal, Monte Carlo, simulação.

DRAFT:
draft scenario, report, alert.

PUBLISH:
publicar cenário/indicador.

PRIVILEGED:
promover modelo, alterar Gold, ativar source.

SECURITY:
IAM, RBAC, policies.

Níveis 3+ exigem approval.
Nível 5 exige four-eyes.

INSS Agent nunca recebe:
- cancel_benefit
- deny_benefit
- block_person
- modify_citizen_record

Fraud Agent nunca recebe:
- punish
- block
- accuse
- deny_payment

---

# 21. APPROVAL E CHECKPOINTS

Estado persistido:
- agent_run
- agent_checkpoint
- approval_request
- approval_decision
- action_request
- action_execution

Fluxo:
Agent → action request → risk evaluation → PAUSED → persist checkpoint → approval queue → APPROVE/REJECT → resume/terminate.

Sem `APPROVED` persistido, não há aresta para execução.

Four-eyes:
solicitante não aprova própria ação crítica.

---

# 22. OBSERVABILIDADE AGENTIC

Desde o primeiro agente.

Trace:
- trace_id
- session_id
- agent_run_id
- organization_id
- agent_name
- agent_version
- model
- prompt_version
- tool
- tool_input_hash
- tool_output_hash
- latency
- tokens
- cost
- approval_state
- errors

PII Redaction acontece antes do trace.

Redaction:
CPF, email, telefone, endereço, secrets, tokens e identificadores sensíveis.

---

# 23. HARNESS DE CÓDIGO

Harness principal: **Claude Code**.

Todos os arquivos orientados ao agente de código ficam em inglês:
- `CLAUDE.md`
- `AGENTS.md`
- `.claude/commands/*`
- `.claude/skills/*`
- reviewer policies
- coding-agent references

`CONTEXTO.md`, PRDs, ADRs e SPECs de produto continuam em PT-BR para o portfólio e equipe.

Princípios:
- context versionado;
- commands versionados;
- skills vendorizadas e pinadas;
- author/reviewer separados;
- reviewer read-only;
- main protegida;
- PR-only;
- CI bloqueante.

---

# 24. PROCESSO VISÍVEL

Branch:
main protegida
feature/*
fix/*
docs/*
chore/*

Sem direct push em main.

Commits:
Conventional Commits.

PR template contém:
- problema
- PRD
- SPEC
- ADRs
- riscos
- alterações
- testes
- evidências

CODEOWNERS para:
- terraform
- security
- agents
- models
- ADRs

Pipeline:
format
→ lint
→ typecheck
→ unit
→ integration
→ data contracts
→ security
→ terraform validate/plan
→ agent evals
→ spec verifier
→ human review
→ merge

Falhou gate obrigatório = merge bloqueado.

---

# 25. REVIEWER INDEPENDENTE

`/verify-spec` (English agent command) roda em contexto novo.

Reviewer CAN:
- read
- search
- run tests
- inspect logs
- emit verdict

Reviewer CANNOT:
- edit
- patch
- commit
- push
- deploy

Se corrigiu, virou autor.

Fluxo:
Author → implementation → PR → Reviewer → FAIL/PASS.
FAIL retorna ao Author.
Nova revisão deve ser independente.

---

# 26. RISK → CONTROL → TEST

Exemplos:
LLM inventa métrica → metric tool only → grounded metric eval.
Agent write indevido → capability absence → permission test.
Publish sem approval → persistent gate → integration test.
PII em trace → redaction before trace → privacy test.
Schema drift → data contract/quarantine → contract test.
Resposta sem fonte → provenance mandatory → answer eval.
Model degradation → champion/challenger → model gate.
Reviewer altera código → read-only harness → reviewer permission test.

Regra:
> todo risco alto precisa de pelo menos um controle e um teste automatizado.

---

# 27. MVP

Landing pública
+ Brasil Hoje
+ Open Data Hub básico
+ datasets reais
+ Macro
+ Fiscal
+ DebtLab
+ INSS
+ Estados
+ 1 forecast
+ 1 simulador fiscal
+ 1 simulador previdenciário
+ RAG
+ Copilot
+ Admin mínimo
+ RBAC
+ audit
+ provenance
+ quality
+ CI/CD
+ observabilidade.

Fora do MVP:
- ações reais sobre cidadãos;
- cancelamento/concessão autônoma;
- fraude operacional;
- todos os 5.570 twins completos;
- todos os 24 simuladores;
- todos os agentes;
- modelos "oficiais definitivos";
- produção sem human review.

---

# 28. ROADMAP CONSOLIDADO

Fase 0 — Discovery & Risk Design
Fase 1 — Marca + Landing
Fase 2 — GCP Foundation
Fase 3 — Open Data Hub
Fase 4 — Lakehouse
Fase 5 — Data Trust/Governance
Fase 6 — MVP Econômico
Fase 7 — Digital Twins
Fase 8 — Intelligence
Fase 9 — Knowledge
Fase 10 — Policy Lab
Fase 11 — Agentic AI
Fase 12 — Portais completos
Fase 13 — Command Center
Fase 14 — APIs/Ecossistema
Fase 15 — Escala Nacional

---

# 29. INDICADORES E BRASIL ON-TRACK

Índice composto com:
Fiscal
Debt
Growth
Productivity
Employment
Pension
Infrastructure
Education
Social
Competitiveness

Pesos públicos e versionados.
Sensitivity analysis obrigatória.
É um índice derivado, não fato oficial.

Early Warning:
verde/amarelo/laranja/vermelho para fiscal, dívida, inflação, emprego, Previdência, municípios, receita, saúde e infraestrutura.

---

# 30. MONETIZAÇÃO / SUSTENTABILIDADE

Nunca vender dados públicos brutos como diferencial.

Valor:
integração, qualidade, derived metrics, models, simulation, automation, provenance e workflows.

Opções:
- public free tier;
- SaaS para estados/municípios;
- white-label;
- Enterprise Intelligence;
- APIs/data products;
- Policy Simulation as a Service;
- GovMarket/procurement intelligence;
- infrastructure intelligence;
- research/media widgets;
- consultoria/estudos;
- treinamento/ecossistema.

Para concurso CGU: impacto público é prioridade; monetização é evolução.

---

# 31. KPIs

Dados:
datasets integrados, freshness, quality, availability.

Produto:
usuários, consultas, dashboards, simulações, exports.

IA:
groundedness, tool selection, citation correctness, SQL correctness, hallucination, latency, cost.

Impacto:
tempo economizado, datasets reutilizados, órgãos conectados, municípios analisados, decisões apoiadas, riscos detectados.

Open Data Impact:
datasets reused, related datasets, organizations connected, consultations, simulations, derived indicators, users.

---

# 32. RESPONSIBLE AI E SEGURANÇA

Human-in-the-loop.
Traceability.
Transparency.
Fairness.
Privacy.
Audit.
Uncertainty.
No automated punitive action.
No official claim from generative output without source.
No secret in repository.
ADC/Workload Identity em vez de chaves estáticas.
MFA e least privilege.
Row/column/table/dataset security em BigQuery.

---

# 33. DEVKIT GCP + CLAUDE CODE

Local:
- git
- Python
- Node
- gcloud
- Terraform
- Claude Code
- optional Cursor

GCP authentication:
- `gcloud init`
- `gcloud auth application-default login`

CI:
Workload Identity Federation.
No long-lived service account key.

BigQuery MCP pode ser usado read-only/controlled conforme suporte e permissões.

---

# 34. REGRAS PARA NOVOS DESENVOLVEDORES/AGENTES

Nunca:
- inventar requisito;
- inventar dado;
- confundir estimativa com observado;
- alterar Gold manualmente;
- adicionar write tool para "facilitar";
- fazer direct deploy em PROD;
- bypass de CI;
- editar SPEC para fazer teste passar;
- reviewer corrigir;
- remover audit;
- hard-code secrets;
- registrar PII bruta em trace.

Sempre:
- identificar PRD/SPEC/ADR;
- escrever/atualizar teste;
- preservar provenance;
- respeitar tool capability;
- gerar evidência no PR;
- registrar nova decisão arquitetural em ADR quando necessário.

---

# 35. ESTADO DO PACOTE

Este pacote deve ser tratado como baseline completo para:
- GitHub;
- Claude Code;
- Cursor;
- implantação GCP;
- documentação de portfólio;
- preparação para o concurso;
- continuação do desenvolvimento.

Nada neste arquivo significa que todos os módulos já estão implementados. Ele documenta o escopo e a intenção acumulada.
