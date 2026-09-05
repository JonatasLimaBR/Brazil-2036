# DESIGN — INSS_BENEFICIOS

## Metadados

- **Feature:** INSS_BENEFICIOS
- **Status:** 🔶 PR1+PR2 Built, backfill real pendente
- **Fase:** 2 (Design)
- **Entrada:** `.claude/sdd/features/DEFINE_INSS_BENEFICIOS.md` (Clarity 14/15)
- **Criado:** 2026-09-04
- **Idioma:** PT-BR
- **Branch:** a criar — `feature/inss-beneficios`
- **Confiança:** 0.85 — sem `kb/` do plugin; padrões vêm do código já existente
  (`connectors/base.py`, `pipeline.py`, `bronze.py`, `bigquery_io.py`) + descoberta real dos 3
  recursos (não suposição).
- **Próximo passo:** `/build .claude/sdd/features/DESIGN_INSS_BENEFICIOS.md`

> Nota: assets do plugin SDD ausentes — documento segue a lista de seções do skill `sdd-design`.

---

## 0. Descoberta real (tarefa 1 — resolve OQ1–OQ5 do DEFINE)

A descoberta via `dados.gov.br` (portal público, SPA) **bloqueou toda chamada programática**
(HTTP 401 em `package_show`, `package_search` e até a página do dataset, com ou sem User-Agent
de navegador) — provavelmente um WAF/anti-bot, não autenticação CKAN real. Como no MVP
(`divida_estados`, servido por `tesourotransparente.gov.br`, não por `dados.gov.br` diretamente),
o recurso real vive no **portal CKAN da própria agência**: `dadosabertos.inss.gov.br`, que
respondeu normalmente. `dados.gov.br` continua sendo só o catálogo (ADR-008); `source_url`
aponta para lá, `resource_url` real aponta para o portal do INSS.

Achados que **revogam suposições do Brainstorm/DEFINE**:

| Suposição original | Realidade descoberta |
|---|---|
| 3 datasets pequenos, agregáveis direto | **Microdado por despacho de benefício** — `Emitidos`: 1 linha por evento de pagamento, ~811 MB comprimido / **~7,4 GB/mês** descomprimido. `Mantidos Ativos`: 1,2 GB comprimido/mês. Ordens de grandeza acima da dívida (27 linhas). |
| "Mantidos" = 1 arquivo/mês | É **3 sub-arquivos/mês** (Ativos / Suspensos / Cessados) — 108 recursos no total. |
| "Indeferidos" = CSV (conforme `SOURCE-INDEX.csv`) | É **XLSX**, ~67 MB/mês — formato de origem diferente dos outros 2. |
| Dicionário de espécies como recurso à parte (A2) | **Não existe recurso separado** — cada linha já traz `especie` (código) **e** `especie_codigo_nome` (descrição) juntos. **R3 do DEFINE cai** — simplifica o desenho. |
| Janela fechada Jun/2023–Jun/2025 (A6) | **Rótulo do catálogo está desatualizado** — dado é publicado continuamente (visto até Julho/2026 no momento da descoberta). Atualização mensal contínua, não recorte fechado. |
| `uf` = sigla (como a dívida) | `uf` vem como **nome completo, maiúsculo, sem acento** (`"SAO PAULO"`) — não bate direto com `uf_ibge.state_name` (`"São Paulo"`, acentuado). Precisa de normalização. |
| URL de arquivo previsível por convenção | Convenção de nome **mudou no meio da janela** (`D.SDA.PDA.003.EMI.*` até 2025 → `D.DLK.FRM.000.DADOSABERTOS.*` a partir de jul/2026). **Nunca construir URL por convenção** — sempre listar via `package_show`. |

**Decisão de escopo (confirmada com o usuário):** ingerir o **máximo de histórico disponível**
dos 3 datasets (todos os meses publicados em cada portal CKAN — não só o mês mais recente).
Isso muda a arquitetura do pipeline: `pipeline.run()` (MVP) processa **1 recurso, 1 vez, tabela
inteira reescrita a cada run** — suficiente para a dívida (1 arquivo contém todos os anos). Para
INSS, cada mês é um recurso separado publicado ao longo de anos — o pipeline precisa
**acumular** meses sem reprocessar/perder os anteriores. Ver §3 D1/D3.

Colunas reais confirmadas (`Emitidos`, header real do CSV):
`despacho;sexo_recebedor;clientela;tipo_beneficio;uf;meio_pagamento;banco;municipio;
municipio_resid;vl_liquido;ramo_atividade;Dt_Inicio_Validade;especie;especie_codigo_nome`
— sem CPF/nome/data de nascimento do beneficiário (não é PII direto), mas é granularidade de
evento individual — reforça C3 do DEFINE (saída pública só agregada).

---

## 1. Grounding

| Fonte | O que fixa |
|---|---|
| `DEFINE_INSS_BENEFICIOS.md` | Requisitos G1–G13, AT1–AT10, contrato de dados, constraints C1–C9. |
| `ingestion/src/ingestion/connectors/base.py` | `Connector` Protocol (`discover`→1 `ResourceRef`, `download`, `validate`, `checkpoint`) — **reaproveitado sem mudar assinatura** (cada conector INSS ainda descobre 1 recurso por instância; a iteração sobre meses vive fora, no orquestrador de backfill). |
| `ingestion/src/ingestion/pipeline.py` | `run()` de recurso único, `CREATE OR REPLACE TABLE` cheio em Bronze/Silver/Gold — **precisa virar escrita por partição** para acumular meses (D3). |
| `ingestion/src/ingestion/bronze.py` | `LOAD DATA OVERWRITE ... FROM FILES(format='CSV', uris=[...])` — padrão de carga nativa do BigQuery, já prova que arquivos grandes não passam pela memória do Python no load em si (só o download passa). |
| `ingestion/src/ingestion/bigquery_io.py` | `BigQueryClient` é só `.query(sql)` — toda carga é SQL (`LOAD DATA`), sem API de job dedicada. XLSX precisa virar CSV **antes** de chegar aqui (D6). |
| `ingestion/reference/uf_ibge.csv` | `uf,state_ibge_code,state_name` — `state_name` acentuado (`"São Paulo"`); INSS manda nome sem acento maiúsculo — precisa de coluna normalizada (D4). |
| `SPEC-007` | Formato de `metric_provenance` — 1 linha por linha de métrica; aqui, por (UF, espécie[, status], mês). |
| `ADR-011` | Chave territorial IBGE — mantida; UF aqui, não município (C6 do DEFINE). |
| `RISK-CONTROL-TEST-MATRIX` (R-012) | Custo de BigQuery — com volume real de dezenas/centenas de GB, vira risco de produção, não só de CI (nota em §8). |

---

## 2. Arquitetura

### 2.1 Visão geral

```text
┌───────────────────────────────────────────────────────────────────────────────────────┐
│  dadosabertos.inss.gov.br (CKAN da agência)                                            │
│    package_show(slug) → lista de recursos (1 por mês[, por sub-status])                │
└───────────────────────────────────────┬─────────────────────────────────────────────────┘
                                          │  ckan.list_resources(slug)  (novo helper)
                                          ▼
┌───────────────────────────────────────────────────────────────────────────────────────┐
│  backfill.py (novo orquestrador, um por dataset: emitidos | mantidos | indeferidos)     │
│    for resource in ckan.list_resources(slug):                                          │
│        if registry.already_ingested(dataset_id, resource.id): continue  # resumível     │
│        connector = InssXConnector(resource_ref=resource)  # Connector Protocol, 1 recurso│
│        pipeline.run(config, connector=connector, reference_period=resource.period)      │
└───────────────────────────────────────┬─────────────────────────────────────────────────┘
                                          │  pipeline.run() — MESMA função do MVP, reaproveitada
                                          ▼
┌───────────────────────────────────────────────────────────────────────────────────────┐
│  pipeline.run() (modificado — escrita por partição, D3)                                 │
│    registry.upsert (1 linha por recurso processado)                                     │
│    connector.download → RAW imutável (gs://…/inss/<dataset>/<sha256>.<ext>)             │
│    [XLSX apenas] converte local para CSV antes do load (D6)                             │
│    bronze.load_partition(reference_month) — LOAD DATA OVERWRITE <table>$<partition>     │
│    contract.check_bronze_schema                                                         │
│    silver: normaliza UF (nome→código, D4), espécie (já vem no dado), status (Mantidos)  │
│      → escreve só a partição do mês (MERGE ou DELETE+INSERT por reference_date)         │
│    gold: agrega GROUP BY uf, especie[, status], mês → escreve só a partição do mês       │
│    provenance.write_from_gold (escopo = este reference_date, não MAX global)            │
│    contract.check_gold                                                                  │
└───────────────────────────────────────┬─────────────────────────────────────────────────┘
                                          ▼
                    gold_inss_beneficios_{emitidos,mantidos,indeferidos}
                    (grão: UF × espécie [× status_manutencao] × mês)
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    ▼                                             ▼
        api/ — extensão de /v1/metrics (G7, PR2)         web/ — módulo M03 (G8, PR2)
        BigQueryRepo.latest_metric_period(metric_id,       3 números (mês mais recente),
        uf|BR, especie, mês) + soma nacional opcional       cada um com fonte + observed
```

### 2.2 Componentes

| # | Componente | Papel |
|---|---|---|
| C1 | `ingestion/src/ingestion/ckan.py` | Helper genérico: `list_resources(base_url, package_id) -> list[CkanResource]` — chama `package_show`, extrai nome/formato/URL/data por recurso. Reusável para qualquer dataset CKAN futuro (Tesouro, IBGE, etc.), não específico de INSS. |
| C2 | `connectors/inss_emitidos.py`, `inss_mantidos.py`, `inss_indeferidos.py` | Cada um implementa o `Connector` Protocol existente **sem mudar a interface** — cada instância já nasce apontando para 1 `ResourceRef` (1 mês, passado no construtor pelo orquestrador). `Mantidos` aceita um `status_manutencao` extra no construtor (ativo/suspenso/cessado). `Indeferidos` faz a leitura XLSX (via `openpyxl`, modo `read_only` — streaming, não carrega tudo em memória) e escreve um CSV local equivalente antes de devolver o `DownloadResult`. |
| C3 | `backfill.py` | Novo — não existia no MVP. Um `run_backfill(dataset, config)` por dataset: lista recursos via C1, filtra os já ingeridos (consulta `dataset_registry` por `resource_id`/hash — resumível, idempotente), instancia o conector certo por recurso, chama `pipeline.run()` (inalterado na assinatura) uma vez por recurso. Loga progresso; continua após falha isolada de 1 mês (não aborta o backfill inteiro). |
| C4 | `pipeline.run()` (modificado) | Ganha um parâmetro `reference_period: date` (mês de referência do recurso sendo processado) usado para escopar as escritas de Bronze/Silver/Gold/provenance à partição certa, em vez de reescrever a tabela inteira. Assinatura pública (`connector`, `storage_client`, `bq_client`) **não muda** — só adiciona o escopo de partição. |
| C5 | `bronze.load_partition()` | Variante de `bronze.load()`: `LOAD DATA OVERWRITE <table>$<YYYYMM>` (decorador de partição do BigQuery) em vez de `CREATE OR REPLACE TABLE` cheio — idempotente por mês, não apaga meses já carregados. |
| C6 | SQL Silver/Gold por dataset | 3 pares de arquivo (`silver/inss_beneficios_{emitidos,mantidos,indeferidos}.sql`, `gold/gold_inss_beneficios_{...}.sql`) — cada um faz `DELETE WHERE reference_date = @period; INSERT INTO ... SELECT ... GROUP BY uf, especie[, status]` (idempotente por partição, acumula histórico). |
| C7 | `uf_ibge.csv` (+1 coluna) | `state_name_normalized` = `UPPER(unaccent(state_name))`, pré-computada no CSV de referência — join direto contra o `uf` já normalizado do INSS, sem função SQL de-accent em runtime. |
| C8 | 3 contratos de dados | `NOT NULL` em `state_ibge_code`, `especie_codigo`, `reference_date`; `value >= 0`/`count >= 0`; mesmo padrão de `divida_consolidada_estados.yaml`. |
| C9 | `api/bigquery_repo.py` (estendido) | Nova query parametrizada por `(metric_id, uf|'BR', especie, mês)` — aditiva, não quebra a rota existente `(metric_id, state, MAX(ano))` da dívida (C9 do DEFINE). |
| C10 | `web/` módulo M03 | 1 componente novo consumindo os 3 `metric_id` via a API estendida. |

### 2.3 Pontos de integração

| Dependência | Uso | Falha |
|---|---|---|
| `dadosabertos.inss.gov.br` (CKAN da agência) | `package_show` para listar recursos reais | portal fora do ar → `backfill.py` falha limpo, resumível na próxima execução (idempotente por recurso já processado) |
| `armazenamento-dadosabertos.s3.sa-east-1.amazonaws.com` | download efetivo dos arquivos (S3 do INSS, fora do CKAN) | mesma retry/backoff já existente em `retry_with_backoff` |
| BigQuery | `LOAD DATA OVERWRITE <table>$<partition>` por mês; `PARTITION BY reference_date, CLUSTER BY state_ibge_code, especie_codigo` | partição isolada — falha em 1 mês não corrompe os demais |
| `openpyxl` (nova dependência) | leitura streaming do XLSX de Indeferidos | arquivo corrompido → `validate()` do conector falha antes do load |

---

## 3. Decisões (ADRs inline)

### D1 — Backfill total via orquestrador externo, `pipeline.run()` reaproveitado sem mudar assinatura

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-04 |

**Contexto:** o usuário confirmou ingerir o máximo de histórico disponível (37–108 recursos por
dataset), não só o mês mais recente. `pipeline.run()` do MVP processa 1 recurso por chamada.

**Escolha:** um novo módulo `backfill.py` lista os recursos reais via CKAN (D2) e chama
`pipeline.run()` **uma vez por recurso**, sequencialmente, pulando recursos já registrados em
`dataset_registry` (resumível — uma execução interrompida retoma sem reprocessar o que já
passou). `pipeline.run()` em si não muda de assinatura pública — só ganha escrita por partição
(D3) para não se autodestruir a cada chamada subsequente.

**Racional:** zero risco à função já testada e provada em produção (MVP); a complexidade nova
(iteração, resumo, backfill) fica isolada num módulo novo, testável à parte.

**Alternativas rejeitadas:**
1. *Mudar `discover()` para retornar `list[ResourceRef]` e `pipeline.run()` para iterar
   internamente* — rejeitado: quebra a assinatura testada do MVP: qualquer regressão ali afeta
   também a dívida em produção.
2. *Só o mês mais recente, backfill como job separado futuro* — rejeitado nesta rodada: o
   usuário pediu explicitamente o máximo de dados agora.

**Consequências:** (+) reaproveita 100% do pipeline provado; (+) resumível/idempotente por
natureza. (−) backfill de ~183 recursos ao todo é uma execução longa (estimativa: dezenas de GB
por download + load; ver risco de tempo/custo em §8); (−) precisa de escrita por partição
funcionando corretamente antes do backfill rodar (dependência de D3).

### D2 — Descoberta via CKAN da agência (`dadosabertos.inss.gov.br`), nunca URL por convenção

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-04 |

**Contexto:** `dados.gov.br` bloqueia chamada programática (401 mesmo em rota de API/HTML,
provável anti-bot). O portal da agência (mesmo padrão do Tesouro na fatia #1) respondeu normal.
A convenção de nome de arquivo **mudou no meio da janela de dados** (`D.SDA.PDA.003.EMI.*` →
`D.DLK.FRM.000.DADOSABERTOS.*`), provada ao vivo na descoberta.

**Escolha:** `ckan.list_resources()` sempre consulta `package_show` do portal da agência
(`dadosabertos.inss.gov.br`) para obter a lista de recursos reais (nome, formato, URL, data) —
nunca constrói uma URL de arquivo por convenção de nome/data.

**Racional:** a mudança de convenção observada ao vivo prova que hardcoded pattern quebraria
silenciosamente assim que a agência mudasse o nome de novo. `dataset_registry.source_url`
continua apontando para `dados.gov.br` (catálogo, ADR-008); `resource_url` real vem do CKAN da
agência.

**Alternativas rejeitadas:** *Hardcode de padrão de nome por mês* — rejeitado, já provado frágil.

**Consequências:** (+) resiliente a mudança de convenção; (−) 1 chamada de API extra por dataset
antes de iniciar o backfill (custo desprezível).

### D3 — Escrita por partição (não `CREATE OR REPLACE TABLE` cheio) em Bronze/Silver/Gold

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-04 |

**Contexto:** o MVP reescreve a tabela inteira a cada run porque a dívida é 1 arquivo com todos
os anos. INSS é 1 arquivo por mês — reescrever a tabela inteira a cada mês apagaria os meses já
carregados nos runs anteriores do backfill.

**Escolha:** `bronze.load_partition()` usa `LOAD DATA OVERWRITE <table>$<YYYYMM>` (decorador de
partição nativo do BigQuery — sobrescreve só aquela partição). Silver/Gold usam
`DELETE FROM target WHERE reference_date = @period; INSERT INTO target SELECT ...` dentro do
mesmo escopo de mês. Tabelas particionadas por `reference_date` (truncado ao mês) e clusterizadas
por `state_ibge_code, especie_codigo` (mesma convenção do `debt_state.sql` existente,
`PARTITION BY ... CLUSTER BY ...`).

**Racional:** idempotente por partição (rerodar um mês não duplica nem corrompe outros); mantém
o padrão `LOAD DATA`/SQL puro já usado no MVP, sem introduzir API de job nova.

**Alternativas rejeitadas:**
1. *`CREATE OR REPLACE TABLE` reprocessando tudo a cada run* — rejeitado: exigiria reprocessar
   ~183 arquivos a cada execução, custo e tempo inviáveis para manutenção contínua.
2. *`MERGE` em vez de `DELETE+INSERT`* — considerado equivalente; `DELETE+INSERT` escolhido por
   ser mais simples de raciocinar sobre idempotência por partição neste primeiro incremento.

**Consequências:** (+) acumula histórico corretamente; (+) reprocessar 1 mês é seguro e barato.
(−) `pipeline.run()` ganha um parâmetro novo (`reference_period`) — muda o corpo da função, não
a assinatura pública dos objetos que ela recebe.

### D4 — Normalização de UF por nome (não código) via coluna auxiliar no `uf_ibge.csv`

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-04 |

**Contexto:** o campo `uf` do INSS vem como nome completo sem acento, maiúsculo
(`"MATO GROSSO DO SUL"`); `uf_ibge.state_name` está acentuado (`"Mato Grosso do Sul"`).

**Escolha:** adiciona coluna `state_name_normalized` (= nome sem acento, maiúsculo) ao
`uf_ibge.csv` de referência, pré-computada (não função SQL em runtime). Silver faz
`JOIN uf_ibge ON u.state_name_normalized = UPPER(b.uf)`.

**Racional:** mesma tabela de-para já existente e já provada (ADR-011); 1 coluna a mais é mais
simples e mais barato que uma função de-accent do BigQuery em toda query.

**Alternativas rejeitadas:** *`NORMALIZE(x, NFD)` + regex remove diacríticos em SQL* —
funcionaria, mas roda em toda linha de toda query; pré-computar 27 linhas uma vez é mais barato e
mais fácil de auditar.

**Consequências:** (+) join simples e barato; (−) `uf_ibge.csv` precisa ser mantido junto se a
agência mudar a grafia (baixo risco — nomes de estado não mudam).

### D5 — Sem tabela de dicionário de espécies (revoga R3 do DEFINE)

| Atributo | Valor |
|---|---|
| Status | Accepted — supersede parcial de `DEFINE_INSS_BENEFICIOS.md` R3 |
| Data | 2026-09-04 |

**Contexto:** o DEFINE previa uma tabela de-para de espécie (R3), assumindo um recurso de
dicionário separado (`SPEC-011`: "dictionaries when available"). A descoberta real mostrou que
`especie` (código) e `especie_codigo_nome` (descrição) já vêm juntos em cada linha do dado.

**Escolha:** Silver usa `especie` + `especie_codigo_nome` diretamente da fonte — sem tabela de
dicionário separada, sem join extra.

**Racional:** dado já se autodescreve; construir uma tabela de-para redundante violaria "nunca
inventar requisito" — não há requisito real de dicionário quando o dado já carrega a descrição.

**Consequências:** (+) simplifica o desenho (menos 1 tabela `control`, menos 1 join); (−) se a
mesma `especie` tiver descrições ligeiramente diferentes entre arquivos/meses (variação de
grafia), a Silver precisa escolher uma (`ANY_VALUE` ou a mais recente) — checado no contrato.

### D6 — Indeferidos (XLSX) convertido para CSV local antes do `LOAD DATA`

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-04 |

**Contexto:** BigQuery `LOAD DATA FROM FILES` não aceita XLSX como formato de origem. O
`BigQueryClient` do projeto é deliberadamente mínimo (`.query(sql)` só, sem API de job).

**Escolha:** `InssIndeferidosConnector.download()` baixa o XLSX original (grava em RAW,
imutável, sem alteração), depois converte para CSV local (`openpyxl`, modo `read_only`,
streaming linha a linha — não carrega o arquivo inteiro em memória) antes de devolver o
`DownloadResult`. O CSV convertido segue o mesmo caminho de `write_raw`/`bronze.load_partition`
que os outros 2 datasets — **sem estender `BigQueryClient`**.

**Racional:** mantém consistência total de padrão de carga (só `LOAD DATA FROM FILES(CSV)` em
todo o pipeline); RAW continua guardando o artefato original real (XLSX), não o convertido —
honra "RAW imutável" com os bytes que a agência realmente publicou.

**Alternativas rejeitadas:** *Estender `BigQueryClient` com upload via API de job (aceita XLSX
via engine externa, ou Parquet)* — rejeitado: mais superfície nova por um único dataset menor
(67 MB/mês, o menor dos 3).

**Consequências:** (+) zero mudança na camada BigQuery; (−) `openpyxl` vira dependência nova do
`ingestion/pyproject.toml`.

### D7 — `Mantidos`: 1 tabela Gold com dimensão `status_manutencao`, não 3 tabelas

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-04 |

**Contexto:** a descoberta mostrou que "Mantidos" é publicado como 3 sub-arquivos por mês
(Ativos/Suspensos/Cessados). O Brainstorm/DEFINE já haviam decidido 3 tabelas Gold **por
dataset** (Emitidos/Mantidos/Indeferidos) — essa decisão continua valendo; a pergunta nova é
como tratar os 3 sub-estados **dentro** de Mantidos.

**Escolha:** `gold_inss_beneficios_mantidos` grão UF × espécie × **`status_manutencao`**
(ativo/suspenso/cessado) × mês — 1 tabela, não 3, porque ativo/suspenso/cessado são estados do
**mesmo** tipo de evento (benefício mantido), não semânticas distintas como emitido vs.
indeferido eram.

**Racional:** consistente com C5 do DEFINE (3 Gold separadas por dataset semanticamente
distinto) sem multiplicar por sub-estado, que é só mais uma dimensão, não outro dataset.

**Consequências:** (+) 1 tabela a menos para manter; (−) toda query no card/API precisa lembrar
de filtrar/agrupar por `status_manutencao`.

### D8 — Download em memória aceito (sem streaming de upload), Cloud Run Job dimensionado

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-04 |

**Contexto:** `pipeline.run()` hoje faz `payload = Path(local).read_bytes()` (arquivo inteiro em
memória) antes de `write_raw`. O maior arquivo real (Mantidos Ativos) é 1,2 GB comprimido.

**Escolha:** aceitar o padrão atual (buffer em memória) e dimensionar o Cloud Run Job do INSS
com memória suficiente (proposto: 8 GiB) em vez de reescrever `write_raw`/`download` para
streaming.

**Racional:** YAGNI — reescrever para streaming é mais código e mais risco por um problema que
uma configuração de recurso já resolve; 8 GiB cobre o maior arquivo real conhecido com folga.

**Alternativas rejeitadas:** *Streaming real (chunked upload)* — mais robusto a arquivos futuros
maiores, mas escopo maior; vira item de follow-up se um arquivo futuro estourar a memória
configurada.

**Consequências:** (+) menor mudança de código; (−) mais memória de Cloud Run Job = mais custo
por execução (ainda assim, execuções não são 24/7 — só durante o backfill/runs mensais).

---

## 4. Manifesto de arquivos

### PR1 — espinha de dados (3 datasets, histórico completo)

| # | Arquivo | Ação | Propósito | Agente | Deps |
|---|---|---|---|---|---|
| 1 | `docs/adrs/ADR-055-inss-incremental-partitioned-ingestion.md` | Create | Formaliza D1+D3 (backfill + escrita por partição) | `architect` | — |
| 2 | `ingestion/src/ingestion/ckan.py` | Create | `list_resources(base_url, package_id)` genérico (D2) | `python-developer` | — |
| 3 | `ingestion/tests/test_ckan.py` | Create | Unit do lister (mock HTTP) | `python-reviewer` | 2 |
| 4 | `ingestion/reference/uf_ibge.csv` | Modify | +coluna `state_name_normalized` (D4) | `python-developer` | — |
| 5 | `ingestion/src/ingestion/connectors/inss_emitidos.py` | Create | `Connector` para 1 mês de Emitidos (ZIP→CSV) | `ai-data-engineer-gcp` | — |
| 6 | `ingestion/src/ingestion/connectors/inss_mantidos.py` | Create | `Connector` para 1 mês × 1 status de Mantidos | `ai-data-engineer-gcp` | — |
| 7 | `ingestion/src/ingestion/connectors/inss_indeferidos.py` | Create | `Connector` XLSX→CSV local (D6) | `ai-data-engineer-gcp` | — |
| 8 | `ingestion/tests/test_connector.py` | Modify | +3 suites de teste (download/validate de cada) | `python-reviewer` | 5,6,7 |
| 9 | `ingestion/src/ingestion/bronze.py` | Modify | +`load_partition()` (D3) | `python-developer` | — |
| 10 | `ingestion/src/ingestion/pipeline.py` | Modify | +`reference_period`, escritas por partição (D1/D3) | `python-developer` | 9 |
| 11 | `ingestion/tests/test_pipeline.py` | Modify | cobre múltiplas chamadas acumulando partições | `python-reviewer` | 10 |
| 12 | `ingestion/src/ingestion/backfill.py` | Create | orquestrador resumível (D1) | `python-developer` | 2,5,6,7,10 |
| 13 | `ingestion/tests/test_backfill.py` | Create | unit — resume corretamente, pula já ingeridos | `python-reviewer` | 12 |
| 14 | `ingestion/contracts/inss_beneficios_emitidos.yaml` | Create | schema + `NOT NULL` + `value >= 0` | `data-contracts-engineer` | — |
| 15 | `ingestion/contracts/inss_beneficios_mantidos.yaml` | Create | idem + `status_manutencao` | `data-contracts-engineer` | — |
| 16 | `ingestion/contracts/inss_beneficios_indeferidos.yaml` | Create | idem | `data-contracts-engineer` | — |
| 17 | `ingestion/sql/silver/inss_beneficios_emitidos.sql` | Create | normaliza UF (D4), grão UF×espécie×mês, escrita por partição (D3) | `sql-optimizer` | 4 |
| 18 | `ingestion/sql/gold/gold_inss_beneficios_emitidos.sql` | Create | agrega GROUP BY, partição por mês | `sql-optimizer` | 17 |
| 19 | `ingestion/sql/silver/inss_beneficios_mantidos.sql` | Create | idem + `status_manutencao` (D7) | `sql-optimizer` | 4 |
| 20 | `ingestion/sql/gold/gold_inss_beneficios_mantidos.sql` | Create | idem | `sql-optimizer` | 19 |
| 21 | `ingestion/sql/silver/inss_beneficios_indeferidos.sql` | Create | idem | `sql-optimizer` | 4 |
| 22 | `ingestion/sql/gold/gold_inss_beneficios_indeferidos.sql` | Create | idem | `sql-optimizer` | 21 |
| 23 | `ingestion/config/inss_emitidos.yaml`, `inss_mantidos.yaml`, `inss_indeferidos.yaml` | Create | 1 config por dataset (dataset_id, tabelas, contract_path) | `(general)` | — |
| 24 | `ingestion/pyproject.toml` | Modify | +`openpyxl` (D6) | `python-developer` | — |
| 25 | `ingestion/tests/integration/fixtures/inss_{emitidos,mantidos,indeferidos}_sample.{csv,xlsx}` | Create | fixtures pequenas (5–10 linhas cada) | `(general)` | — |
| 26 | `ingestion/tests/integration/test_pipeline_inss_bigquery.py` | Create | `@pytest.mark.integration` — 1 dos 3 datasets contra BQ real (cobre G6/AT9) | `data-quality-analyst` | 10,25 |
| 27 | `infra/terraform/cloud_run.tf` (ou `cloud_run_services.tf`) | Modify | memória do Job INSS (D8, proposto 8 GiB), timeout maior (backfill é longo) | `ci-cd-specialist` | — |
| 28 | `backlog/BACKLOG-MESTRE.md` | Modify | +`STORY-010.03 — benefícios indeferidos` (G11) | `(general)` | — |
| 29 | `INDEX.md` | Modify | +ADR-055, +contratos, +SQL novos | `(general)` | 1,14,15,16 |

### PR2 — apresentação

| # | Arquivo | Ação | Propósito | Agente | Deps |
|---|---|---|---|---|---|
| 30 | `api/src/api/bigquery_repo.py` | Modify | +`latest_metric_period(metric_id, uf\|'BR', especie, mês)` — aditivo, não quebra a rota da dívida (C9) | `python-developer` | PR1 completo |
| 31 | `api/src/api/models.py` | Modify | +campos `especie`/`reference_month` no response model (opcionais, não quebram o schema da dívida) | `python-developer` | 30 |
| 32 | `api/src/api/main.py` | Modify | rota estendida ou nova (`/v1/metrics/{metric_id}` aceita `especie`/`status` opcionais) — decidir formato exato no build a partir do padrão FastAPI existente | `python-developer` | 30,31 |
| 33 | `api/tests/test_bigquery_repo.py`, `test_endpoints.py` | Modify | +casos INSS; confirma rota da dívida continua passando (regressão) | `python-reviewer` | 30-32 |
| 34 | `web/src/` módulo M03 (novo componente) | Create | 3 números (emitidos/mantidos/indeferidos), classe `observed`, link fonte | `typescript-reviewer` | 32 |
| 35 | `web/` — regenerar cliente OpenAPI | Modify | client TS a partir do `openapi.json` atualizado | `(general)` | 32 |
| 36 | `ingestion/tests/integration/` ou `api/tests/` — e2e leve (G12, COULE) | Create | confirma os 3 números renderizam | `python-reviewer` | 34 |

### Racional de agentes
- Conectores GCP/dados → `ai-data-engineer-gcp`; SQL de agregação → `sql-optimizer`; contratos →
  `data-contracts-engineer`; pipeline/orquestração Python → `python-developer`; revisão →
  `python-reviewer`; Terraform → `ci-cd-specialist`; API → `python-developer`; frontend →
  `typescript-reviewer`; ADR/SPEC → `architect`.

### Independência
- PR1 é autocontido (não depende de PR2). PR2 depende de PR1 estar mergeado (a Gold precisa
  existir para a API ler). Sem ciclo: `ckan` → conectores → `pipeline` → `backfill` → SQL → API
  → web. `backfill.py` é o único módulo genuinamente novo na orquestração; tudo mais estende
  arquivos existentes de forma aditiva.

---

## 5. Padrões de código

### 5.1 `ckan.py` — lister genérico

```python
# ingestion/src/ingestion/ckan.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class HttpGet(Protocol):
    def get(self, url: str, timeout: float) -> "HttpResponseLike": ...


class HttpResponseLike(Protocol):
    status_code: int

    def json(self) -> dict: ...
    def raise_for_status(self) -> None: ...


@dataclass(frozen=True)
class CkanResource:
    resource_id: str
    name: str
    format: str
    url: str
    last_modified: str | None


def list_resources(
    session: HttpGet, *, base_url: str, package_id: str, timeout: float = 30.0
) -> list[CkanResource]:
    url = f"{base_url.rstrip('/')}/api/3/action/package_show?id={package_id}"
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    body = response.json()
    if not body.get("success"):
        raise RuntimeError(f"CKAN package_show failed for {package_id!r}")
    resources = body["result"]["resources"]
    return [
        CkanResource(
            resource_id=r["id"],
            name=r["name"],
            format=r["format"],
            url=r["url"],
            last_modified=r.get("last_modified") or r.get("created"),
        )
        for r in resources
    ]
```

### 5.2 `pipeline.run()` — trecho da mudança (escopo por partição)

```python
# ingestion/src/ingestion/pipeline.py (trecho modificado)
def run(
    config: Config,
    *,
    connector: Connector,
    storage_client: StorageClient,
    bq_client: BigQueryClient,
    reference_period: date,          # NOVO — mês do recurso sendo processado
    sql_dir: Path | None = None,
) -> RunResult:
    ...
    load = bronze.load_partition(          # antes: bronze.load(...)
        bq_client,
        project=config.gcp_project,
        dataset_bronze=config.bq_dataset_bronze,
        table=config.bronze_table,
        partition=reference_period,        # ex.: date(2026, 6, 1)
        raw_uri=raw_object.uri,
        source_uri=config.resource_url,
        row_hash=raw_object.content_sha256,
    )
    ...
    placeholders = {**config.placeholders(), "reference_period": reference_period.isoformat()}
    run_sql(bq_client, render_file(sql_dir / "silver" / f"{config.silver_model}.sql", placeholders))
    run_sql(bq_client, render_file(sql_dir / "gold" / f"{config.gold_model}.sql", placeholders))
    # provenance.write_from_gold passa reference_period em vez de MAX(reference_year)
```

### 5.3 SQL Silver — normalização + escrita por partição (Emitidos)

```sql
-- ingestion/sql/silver/inss_beneficios_emitidos.sql
DELETE FROM `${project}.${bq_dataset_silver}.${silver_table}`
WHERE reference_date = DATE('${reference_period}');

INSERT INTO `${project}.${bq_dataset_silver}.${silver_table}`
SELECT
  u.state_ibge_code,
  b.especie AS especie_codigo,
  b.especie_codigo_nome AS especie_nome,
  DATE('${reference_period}') AS reference_date,
  CAST(REPLACE(b.vl_liquido, ',', '.') AS NUMERIC) AS value,
  1 AS event_count,
  b._row_hash
FROM `${project}.${bq_dataset_bronze}.${bronze_table}` AS b
JOIN `${project}.${bq_dataset_control}.${uf_ibge_table}` AS u
  ON u.state_name_normalized = UPPER(b.uf);
```

### 5.4 SQL Gold — agregação UF × espécie × mês

```sql
-- ingestion/sql/gold/gold_inss_beneficios_emitidos.sql
DELETE FROM `${project}.${bq_dataset_gold}.${gold_table}`
WHERE reference_date = DATE('${reference_period}');

INSERT INTO `${project}.${bq_dataset_gold}.${gold_table}`
SELECT
  state_ibge_code,
  especie_codigo,
  especie_nome,
  reference_date,
  'inss_beneficios_emitidos' AS metric_id,
  SUM(value) AS value,
  'BRL' AS unit,
  SUM(event_count) AS count
FROM `${project}.${bq_dataset_silver}.${silver_table}`
WHERE reference_date = DATE('${reference_period}')
GROUP BY state_ibge_code, especie_codigo, especie_nome, reference_date;
```

### 5.5 `bronze.load_partition()`

```python
# ingestion/src/ingestion/bronze.py (nova função, load() existente inalterada)
def load_partition(
    client: BigQueryClient,
    *,
    project: str,
    dataset_bronze: str,
    table: str,
    partition: date,
    raw_uri: str,
    source_uri: str,
    row_hash: str,
) -> BronzeLoad:
    staging = _fqtn(project, dataset_bronze, f"{table}_stg")
    target = _fqtn(project, dataset_bronze, table)
    decorator = f"{table}${partition.strftime('%Y%m')}"
    target_partition = _fqtn(project, dataset_bronze, decorator)

    run_sql(client, f"LOAD DATA OVERWRITE {staging} (...) FROM FILES(...)")
    run_sql(
        client,
        f"LOAD DATA OVERWRITE {target_partition} "
        f"FROM FILES(format='CSV', ...) "  # ou INSERT a partir do staging já tipado
    )
    ...
```

### 5.6 `InssIndeferidosConnector.download()` — XLSX→CSV local

```python
# ingestion/src/ingestion/connectors/inss_indeferidos.py (trecho)
import csv
import openpyxl

def _xlsx_to_csv(xlsx_path: str, csv_path: str) -> None:
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb.active
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, delimiter=";")
        for row in ws.iter_rows(values_only=True):
            writer.writerow(row)
    wb.close()
```

---

## 6. Estratégia de testes

| AT (DEFINE) | Como verificar |
|---|---|
| AT1 descoberta/registro | `test_ckan.py` (mock HTTP, valida parsing de `package_show`); execução real contra `dadosabertos.inss.gov.br` no `integration`. |
| AT2 conector ZIP | `test_connector.py::test_inss_emitidos_*` — fixture pequena simulando o ZIP real. |
| AT3 conectores CSV/XLSX | idem para Mantidos (CSV) e Indeferidos (XLSX→CSV, valida conversão). |
| AT4 grão correto | `test_pipeline.py` — 2 chamadas de `run()` com `reference_period` diferentes acumulam 2 meses sem se apagarem. |
| AT5 contrato pega violação | fixture com coluna faltando → `contract.check_bronze_schema` falha, quarentena. |
| AT6 provenance completa | `test_pipeline_inss_bigquery.py` — 100% das linhas Gold com `metric_provenance` correspondente. |
| AT7 API no grão novo | `test_bigquery_repo.py::test_latest_metric_period` + `test_endpoints.py` — chamada com `especie`/mês retorna valor + provenance; chamada da dívida (sem esses parâmetros) continua igual (regressão). |
| AT8 módulo sem hardcode | teste e2e leve (item 36) — inspeciona que o DOM não contém o número literal, só via `fetch`. |
| AT9 CI ritual | gate `integration` do `ci.yml` já existente cobre 1 dos 3 datasets via fixture — zero mudança de infraestrutura de CI. |
| AT10 lineage fecha | query de linhagem cruzando `registry → RAW → Bronze(partição) → Silver(partição) → Gold(partição) → provenance`, para ≥ 1 UF×espécie×mês de cada dataset. |
| Backfill resumível | `test_backfill.py` — simula falha no meio da lista, reexecução pula os já concluídos. |

**Fixtures:** cada dataset ganha uma fixture pequena (5–10 linhas) no formato real (CSV para
Emitidos/Mantidos, XLSX para Indeferidos) — mesmo espírito de `divida_sample.csv`. O `integration`
gate do `ci.yml` roda contra **1 dos 3** (Emitidos, por ser o de maior risco de formato/volume);
os outros 2 ficam cobertos por unit + o próprio backfill real (fora do CI) no ambiente de build.

---

## 7. Pipeline Architecture (contexto DE)

### 7.1 DAG por recurso (1 mês, repetido pelo backfill)

```text
ckan.list_resources(dataset_slug)
        │
        ▼  (pula os já em dataset_registry)
connector = InssXConnector(resource_ref)
        │
download → RAW imutável (gs://…/inss/<dataset>/<sha256>.<ext>)
        │
[XLSX apenas] converte para CSV local
        │
bronze.load_partition(reference_period)  — LOAD DATA OVERWRITE <table>$<YYYYMM>
        │
contract.check_bronze_schema
        │
silver: DELETE+INSERT partição do mês — normaliza UF (D4), mantém espécie como veio (D5)
        │
gold: DELETE+INSERT partição do mês — GROUP BY uf, especie[, status], mês
        │
provenance.write_from_gold(reference_period)
        │
contract.check_gold
        │
        ▼
próximo recurso da lista (backfill.py continua)
```

### 7.2 Partição / incremental / evolução

- Bronze/Silver/Gold particionados por `reference_date` (mês, truncado ao dia 1), clusterizados
  por `state_ibge_code, especie_codigo` — mesma convenção `PARTITION BY ... CLUSTER BY ...` já
  usada em `debt_state.sql`.
- Incremental por natureza: cada execução do backfill processa 1 recurso = 1 mês = 1 partição.
  Reprocessar um mês é seguro (idempotente, `DELETE+INSERT` escopado).
- Evolução de schema: se a agência adicionar/remover uma coluna, `contract.check_bronze_schema`
  já pega isso (mesmo mecanismo do MVP) e quarentena o mês problemático sem afetar os demais.

### 7.3 Data quality gates

| Gate | Regra | Falha ⇒ |
|---|---|---|
| Schema origem | colunas esperadas por dataset (contrato YAML) | mês quarentenado, backfill continua nos demais |
| Territorial | todo `uf` normalizado bate em `uf_ibge.state_name_normalized` | Silver falha, contrato aponta o valor não mapeado |
| Completude | `value`/`count >= 0`; `NOT NULL` em chaves | contrato falha |
| Provenance | 100% cobertura por partição processada | `contract.check_gold` falha |
| Lineage | query de linhagem fecha por UF×espécie×mês | `/verify-spec` AT10 |

### 7.4 Risco de custo/tempo (nota para o BUILD_REPORT)

Histórico completo estimado: Emitidos ~37 meses × ~800 MB comprimido (~30 GB), Mantidos ~36
meses × 3 sub-arquivos (Ativos maior, ~1,2 GB/mês — ordem de 60–90 GB no total), Indeferidos ~38
meses × 67 MB (~2,5 GB) — **~100–130 GB comprimidos ao todo**, provavelmente ~700 GB–1 TB
descomprimido antes da agregação. Armazenamento GCS/BigQuery nesse volume é barato (poucos
dólares/mês), mas o **tempo de execução do backfill** (download + extração + load sequencial de
~183 recursos) é a variável de risco real — deve ser medido no primeiro run real e reportado no
`BUILD_REPORT`, com paralelização como follow-up se o tempo sequencial for proibitivo.

---

## 8. Quality gate (Fase 2)

- [x] Padrões carregados do código real existente (sem `kb/`); confiança 0.85.
- [x] Diagrama ASCII (§2.1) + DAG por recurso (§7.1).
- [x] ≥ 1 decisão com racional completo — D1–D8 (oito decisões inline).
- [x] Manifesto completo — 36 itens entre PR1 e PR2.
- [x] Agente por arquivo (§4).
- [x] Padrões de código prontos para copiar (§5.1–5.6).
- [x] Estratégia de testes cobre AT1–AT10 + backfill resumível (§6).
- [x] Sem dependência de código quebrando unidades já em produção — `pipeline.run()` ganha
      parâmetro, não muda contrato dos objetos injetados; rota da dívida na API preservada (C9).
- [x] Sem ciclo (`ckan` → conectores → `pipeline` → `backfill` → SQL → API → web).
- [x] Descoberta real (tarefa 1) resolveu OQ1, OQ3, OQ4, OQ5 do DEFINE com dados reais, não
      suposição — revoga R3 (dicionário) via D5, registrado como supersede parcial.
- [x] Status do DEFINE → `✅ Complete (Designed)`.

---

## 9. Handoff

Pronto para **`/build .claude/sdd/features/DESIGN_INSS_BENEFICIOS.md`** na branch
`feature/inss-beneficios`.

Ordem sugerida: docs (1) → `ckan.py`+teste (2,3) → `uf_ibge.csv` (4) → 3 conectores+testes
(5–8) → `bronze.load_partition`+`pipeline.run` modificado+testes (9–11) → `backfill.py`+teste
(12,13) → 3 contratos (14–16) → 6 SQL Silver/Gold (17–22) → 3 configs (23) → `pyproject`+openpyxl
(24) → fixtures+teste de integração (25,26) → Terraform (27) → backlog/INDEX (28,29) → **rodar o
backfill real, medir tempo/custo, registrar no BUILD_REPORT** → PR2: API (30–33) → web (34–36).

---

## 10. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-04 | 1.0 | Criação a partir de `DEFINE_INSS_BENEFICIOS.md`. Descoberta real (§0) revogou suposições do Brainstorm/DEFINE (volume, formato, dicionário, janela temporal, URL). D1–D8 (oito decisões inline). Manifesto 36 itens. Status → Ready for Build. | /design (Claude Sonnet 5) |
| 2026-09-04 | 1.1 | PR1 construído (29 dos 36 itens). Build encontrou e corrigiu 1 risco crítico não antecipado no D3 (tabelas compartilhadas `dataset_registry`/`metric_provenance`) e 2 bugs de escopo em SQL (filtro de período ausente; DELETE sem escopo por `source_uri` para Mantidos). Ver `BUILD_REPORT_INSS_BENEFICIOS.md` §4. PR2 pendente. Status → 🔶 PR1 Built. | /build (Claude Sonnet 5) |
| 2026-09-04 | 1.2 | PR1 mergeado, provado ao vivo contra BigQuery real. PR2 construído: R10/OQ1/OQ2 resolvidas de forma mais simples que o esboço original (agregado nacional, não grão UF×espécie completo — YAGNI, achado #10 do BUILD_REPORT). Só o backfill real falta. Status → 🔶 PR1+PR2 Built. | /build (Claude Sonnet 5) |
