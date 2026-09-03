# ADR-053 — Cloud Run services and the WIF bootstrap live outside Terraform

## Status
Accepted

## Contexto
Esta decisão é parte do baseline arquitetural do BRASIL 2036 e deve ser lida com o `CONTEXTO.md`.
ADR-039 estabelece Terraform como fonte de mudança de infra. Ao executar a fatia
`MVP_WALKING_SKELETON` (SPEC-033) surgiram dois casos de dependência circular que impedem
o Terraform de criar o recurso na primeira aplicação:

1. **Workload Identity Federation.** O `terraform apply` no GitHub Actions só autentica *depois*
   que o pool/provider WIF e a service account de deploy existem. Não há identidade federada
   antes disso.
2. **Serviços Cloud Run (`br2036-api`, `br2036-web`).** Um serviço precisa de uma imagem
   existente no Artifact Registry no momento da criação; a imagem só é construída depois que
   o Artifact Registry (criado pelo Terraform) existe. Além disso, o serviço `web` precisa da
   **URL do serviço `api`**, que só existe após o deploy do `api`.

O revisor independente do `/verify-spec` de `SPEC-033` (2026-09-03) registrou essas duas
deviações contra o MUST "infrastructure is created only by Terraform".

## Decision drivers
- segurança e auditabilidade;
- reprodutibilidade;
- escalabilidade;
- custo operacional;
- aderência ao GCP;
- clareza para portfólio e agentes de código.

## Alternativas consideradas
### A. Forçar tudo no Terraform com múltiplas passagens de `apply`
Considerada e descartada: exige orquestração frágil (apply parcial → build → apply do resto),
imagem placeholder + `terraform_data`/`null_resource` para disparar builds, e ainda assim o
`plan` mostraria mudança de imagem a cada commit. Aumenta complexidade sem ganho de controle.

### B. Provisionar via CLI num script à parte
Considerada; um `bootstrap.sh` único para o WIF (roda uma vez, por humano com Billing Admin)
e o deploy dos serviços Cloud Run no workflow `api-web.yml` via `gcloud run deploy` (idempotente).

### C. Terraform para tudo que não tem dependência circular; CLI só para os dois casos acima
Alternativa escolhida.

## Decisão
- **WIF pool/provider + service account `tf-deployer`**: criados por `scripts/bootstrap.sh`,
  execução única e manual. O provider é travado ao repositório
  (`attribute-condition = "assertion.repository == 'JonatasLimaBR/Brazil-2036'"`).
- **Serviços Cloud Run `br2036-api` e `br2036-web`**: criados e atualizados por
  `.github/workflows/api-web.yml` via `gcloud run deploy`, ambos `--allow-unauthenticated`
  (portal público — ADR-044). A imagem carrega o SHA do commit; o `web` recebe `VITE_API_URL`
  (a URL do `api`) como build-arg.
- **Terraform continua dono de todo o resto**, incluindo a **identidade e o IAM** dos serviços:
  a service account `api-runtime` e seus grants (`bigquery.jobUser` + `bigquery.dataViewer`
  restrito ao dataset `br2036_gold`). O `api-web.yml` anexa essa SA ao serviço `api`
  (`--service-account api-runtime@…`) e espera a SA existir (poll) antes do deploy.

## Exposição pública declarada
Conforme AT8 de `SPEC-033` ("o `plan` não declara exposição pública fora de um ADR"), esta ADR
declara explicitamente: **`br2036-api` e `br2036-web` são publicamente invocáveis
(`allUsers` → `roles/run.invoker`)**. `api` é read-only sobre `br2036_gold` e serve apenas
dados abertos; `web` serve conteúdo estático. Nenhum outro recurso é público.

## Por que
Elimina orquestração frágil de multi-apply; mantém o Terraform como fonte de verdade para
tudo que ele *pode* criar de forma limpa; concentra a exceção em dois pontos auditáveis e
documentados.

## Consequências positivas
- comportamento mais explícito e testável;
- decisão documentada para novos desenvolvedores/agentes;
- redução de ambiguidade;
- `terraform plan` permanece um diff confiável para a infra que ele governa.

## Consequências negativas / custo aceito
- A criação/exposição dos serviços Cloud Run não aparece no `terraform plan` — mitigado por
  esta ADR e pela revisão do `api-web.yml` no PR.
- O `bootstrap.sh` é um passo manual fora do fluxo GitOps — aceito, roda uma vez por ambiente.

## Verificação
A decisão deve aparecer em SPECs, testes, CI ou políticas de repositório quando aplicável —
`SPEC-033` (nota sobre serviços/WIF), `scripts/bootstrap.sh`, `.github/workflows/api-web.yml`,
`infra/terraform/cloud_run_services.tf`.

## Quando reconsiderar
Reconsiderar quando: (a) houver mais de dois serviços Cloud Run e a divergência ficar cara de
manter; (b) o Terraform/provider suportar criação de serviço sem imagem pré-existente de forma
limpa; ou (c) uma política exigir que 100% da exposição pública seja visível no `plan`.
