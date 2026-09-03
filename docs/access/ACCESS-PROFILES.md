# Perfis de Acesso

## Public
Portal público, dados PUBLIC, cenários publicados; sem export restrito ou administração.

## Viewer
Leitura autenticada conforme organização/domínio.

## Analyst
Consulta, filtros, exports permitidos, agentes read-only.

## Economist
Analytical access + forecasts autorizados; sem publicar automaticamente.

## Simulator
Pode RUN_SIMULATION e criar scenario DRAFT.

## Executive/Manager
Command Center, alerts, comparisons; approvals somente se policy permitir.

## Researcher
Dados/metodologia/export para pesquisa conforme classificação.

## Data Steward
Source metadata, contracts, quality decisions, quarantine review.

## Data Engineer
Pipelines, schemas e data ops; produção via PR/CI.

## ML Engineer
Model training/eval/registry; promotion exige gate/approval.

## Agent Manager
Configuração de agents/prompts/tools dentro de policy; sem IAM.

## Organization Admin
Users/workspaces da própria organização.

## Platform Admin
Administração da plataforma; ações críticas auditadas.

## Security Admin
Security policy/IAM approval; four-eyes em ações definidas.

## Auditor/Compliance
Leitura de audit/provenance/security evidence; sem alteração.

## API Consumer/Developer
Uso de APIs/SDKs conforme quota/scope.
