# ADR-059 — DebtLab: fonte de dado, localização do engine e persistência de cenário

## Status
Accepted

## Contexto
Esta decisão é parte do baseline arquitetural do BRASIL 2036 e deve ser lida com o `CONTEXTO.md`.
`DEBTLAB_SIMULATOR` é o primeiro simulador determinístico do projeto (`SIM-002`, `SPEC-010`,
`PRD-004`) — as 6 features anteriores só ingeriram dado observado, nenhuma provou o padrão
"núcleo determinístico, borda probabilística" (`ADR-013`/`ADR-042`).

Descoberta real no `/design` (`DESIGN_DEBTLAB_SIMULATOR.md §0`), não suposição:

1. **Fonte de dado.** `SIM-002` pede "base debt/GDP" nacional. O projeto não tinha PIB real
   (`EPIC-008` nunca construído), e a única dívida real existente (`divida_consolidada`,
   `MVP_WALKING_SKELETON`) é outro conceito — dívida das 27 UFs sob o PAF, só 2022, não a dívida
   bruta do governo geral que a razão dívida/PIB exige. Confirmado por chamada real à API pública
   do BCB SGS: série 4380 (PIB mensal) e série 13762 (Dívida Bruta do Governo Geral, % PIB,
   metodologia 2008+) retornam dado real, mensal, até 07/2026 (82,51% na última leitura).
   `docs/sources/SOURCE-INDEX.csv` já lista o BCB como fonte P0 para "Macro/monetário".
2. **API 100% somente-leitura até aqui.** `infra/terraform/cloud_run_services.tf`: a service
   account `api-runtime` tinha `display_name = "Metrics API runtime (read-only on Gold)"` e só
   `roles/bigquery.dataViewer` no dataset `gold` — nenhuma permissão de escrita, nenhum acesso ao
   dataset `control`. `main.py` só permitia `allow_methods=["GET"]` no CORS.
3. **`ADR-004` (AlloyDB) nunca provisionado.** Nenhum recurso Terraform existe para AlloyDB em
   nenhuma das 6 features shipadas — confirmado por grep. Provisionar agora, sem approval
   workflow/checkpoint real que justifique, contradiria o driver de custo do `ADR-002`
   (serverless-first).

## Decision drivers
- usar a métrica certa para "base debt/GDP" (nacional, não a PAF por UF);
- reaproveitar infraestrutura já provisionada sempre que suficiente, antes de provisionar algo
  novo (`ADR-002`);
- least privilege ao conceder a primeira permissão de escrita da API;
- não fabricar nenhum valor — base real, premissas sempre do usuário, saída sempre `SIMULATED`
  (`ADR-028`).

## Alternativas consideradas

### A. Reaproveitar `divida_consolidada` como base do simulador
Considerada e descartada: é uma métrica diferente (dívida estadual sob o PAF, não a dívida bruta
do governo geral). Usá-la seria responder a pergunta errada, não uma simplificação aceitável.

### B. IBGE Contas Nacionais/SIDRA como fonte de PIB
Considerada: série trimestral, mais granular para PIB real, mas sem uma série de dívida/PIB
equivalente pronta — exigiria combinar 2 fontes diferentes sem ganho claro para o V1.

### C. Provisionar AlloyDB agora para persistência de cenário (honrar `ADR-004` à risca)
Considerada e descartada: custo fixo de infraestrutura nova sem approval workflow/checkpoint real
que o justifique hoje — contradiria o próprio driver de custo do `ADR-002`.

### D. BCB SGS (séries 4380 + 13762) como fonte; engine em `api/`; persistência em
`br2036_control` (BigQuery)
Alternativa escolhida.

## Decisão
- **Fonte de dado:** BCB SGS, séries 4380 (`pib_mensal`) e 13762 (`divida_bruta_pib`) — API
  pública, sem autenticação, confirmada real. Cada série mantém seu próprio conector
  (`BcbSgsConnector`, parametrizado por código de série) e seu próprio conjunto Bronze/Silver/Gold
  — não um recurso combinado, para que a provenance de cada `metric_id` cite a URL real da sua
  própria série, não uma URL compartilhada emprestada da outra.
- **Fórmula:** equação padrão de sustentabilidade fiscal —
  `razão_t = razão_(t-1) × (1+juros)/(1+crescimento) − primário_%PIB_t` — em vez de reconstruir
  dívida em R$ absoluto, evitando projetar PIB em R$ para todo o horizonte.
- **Localização do engine:** `api/src/api/simulators/{debtlab,monte_carlo}.py` — computação
  síncrona disparada por requisição HTTP, sem envolver `ingestion/`/RAW/GCS.
- **Persistência de cenário:** `br2036_control.debtlab_scenarios` (BigQuery), não AlloyDB. A
  service account `api-runtime` ganha `roles/bigquery.dataEditor` escopado só ao dataset
  `control` (não projeto inteiro) — primeira permissão de escrita da API, least-privilege como o
  `ingestion_job` já pratica. CORS ganha `POST` (antes só `GET`).
- **Estrutura de linha:** `deterministic_trajectory`/`percentiles`/`assumptions` são colunas
  `STRING` com JSON serializado, não `ARRAY<STRUCT>` — evita expandir a abstração de query
  parametrizada (`RunQuery`) para tipos complexos por causa de 1 tabela consumida só pela própria
  API.

## Por que
Usa a métrica nacional correta em vez de forçar uma métrica existente (estadual/PAF) a servir um
propósito para o qual não foi feita; reaproveita 100% da infraestrutura já provisionada
(BigQuery), evitando o primeiro recurso não-serverless do projeto sem justificativa de custo real;
mantém a API pública sem autenticação (RBAC é fatia futura da mesma sequência combinada) mas
restringe a nova permissão de escrita ao mínimo necessário.

## Consequências positivas
- Base do simulador é dado real, nacional, mensal, oficial — nenhum valor fabricado ou métrica
  errada.
- Zero infraestrutura nova além de 1 IAM binding escopado — `br2036_control` já existe e já é
  descrito como "Registry, reference tables and run bookkeeping".
- `config.metric_tables` genérico já serve `pib_mensal`/`divida_bruta_pib` via
  `/v1/metrics/{metric_id}/national` sem nenhum código novo de leitura.
- `ADR-004` permanece válido para quando approval workflow/checkpoint de agente virarem reais —
  esta decisão não o supera, só adia sua aplicação.

## Consequências negativas / custo aceito
- BigQuery não é feito para muitas escritas pequenas/transacionais (cotas de DML) — aceitável no
  volume esperado do V1 (API pública sem RBAC ainda, mitigado por limites defensivos em
  `n_iterations`/`horizon_years`, não por rate-limiting completo, que é escopo de uma fatia
  futura de RBAC/ABAC).
- `debtlab_scenarios` não é nativamente consultável via `UNNEST` (campos JSON-como-STRING) — só a
  própria API consome essa tabela hoje; se um consumo analítico direto surgir, precisará de
  `PARSE_JSON`/`JSON_EXTRACT`.

## Verificação
`ingestion/tests/test_bcb_sgs_connector.py` (fetch/parse/validate/checkpoint do conector),
`api/tests/test_debtlab_engine.py` (fórmula contra casos calculados à mão),
`api/tests/test_monte_carlo.py` (reprodutibilidade via seed fixo),
`api/tests/test_debtlab_endpoint.py` (contrato do endpoint, `data_class=simulated` sempre
presente, sem rota de "publicar"). Conferência manual da razão dívida/PIB do mês mais recente
contra a série 13762 real, mesmo padrão de `FISCAL_RECEITA_DESPESA`.

## Quando reconsiderar
Se um approval workflow ou checkpoint de agente real (`ADR-019`/`ADR-020`/`ADR-021`) passar a
existir, reavaliar se `debtlab_scenarios` (e futuras tabelas operacionais análogas) devem migrar
para AlloyDB, conforme `ADR-004` já previa. Se um segundo simulador precisar de dado que
`divida_consolidada` já cobre corretamente, reavaliar se a distinção feita aqui ainda se aplica.
