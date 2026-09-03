# DISCOVERY — MVP_WALKING_SKELETON (Tarefa 1 do PR1)

- **Data:** 2026-09-03
- **Objetivo:** resolver DEFINE A1/A2/A4 — achar e inspecionar o recurso real antes de escrever connector e contrato.
- **Método:** WebSearch + WebFetch sobre o Portal / Tesouro Transparente.

---

## 1. Recurso identificado

| Campo | Valor |
|---|---|
| Dataset (host) | Tesouro Transparente — CKAN: `divida-consolidada-estados` |
| CKAN dataset id | `01aa8c02-4f77-4fcf-a850-ff8f13decb00` |
| Página humana | `https://www.tesourotransparente.gov.br/ckan/dataset/divida-consolidada-estados` |
| Recurso alvo (CSV) | "Dívida Consolidada" — resource id `de4a234e-1712-4a50-8d31-ae4748a5f715` — 5,6 KiB |
| URL de download (estável) | `https://www.tesourotransparente.gov.br/ckan/dataset/01aa8c02-4f77-4fcf-a850-ff8f13decb00/resource/de4a234e-1712-4a50-8d31-ae4748a5f715/download/divida-consolidada-dos-estados---paf.csv` |
| Recurso companheiro | `metadados.pdf` — resource id `907dda46-d45b-4ae7-8420-76e7a313313d` (dicionário de dados) |
| Organização produtora | **COREM** — Tesouro Nacional / STN |
| Licença | **ODbL** — Open Data Commons Open Database License |
| Frequência de atualização | **Anual** |
| Cobertura temporal | 2015 → presente; amostra vai até **2022**; portal atualizado 2023-12-22 |
| Contexto | Estatísticas fiscais do Programa de Reestruturação e Ajuste Fiscal (PAF) |

## 2. Schema real do CSV

```
UF;ANO;VALOR
AC;2015;4.245.948.557,36
AC;2016;3.827.877.107,27
...
AL;2015;11.252.027.857,87
```

| Aspecto | Valor |
|---|---|
| Delimitador | `;` (ponto e vírgula) |
| Separador decimal | `,` (vírgula); milhar com `.` |
| Encoding | UTF-8 |
| `UF` | código de 2 letras (`AC`, `AL`, …, `DF`) — **não** nome de estado |
| `ANO` | ano `YYYY` — **grão anual, não data** |
| `VALOR` | BRL; **Dívida Consolidada (bruta)** do PAF — **não** Dívida Consolidada Líquida |
| Volume | ~216 linhas (27 UF + DF × ~8 anos) |

## 3. Divergências com DEFINE/DESIGN (exigem `/iterate`)

| # | DESIGN assumiu | Realidade | Ajuste |
|---|---|---|---|
| DV1 | `reference_date DATE` | grão anual (`ANO` inteiro) | Silver deriva `reference_date = DATE(ANO, 12, 31)` (fim do exercício fiscal); manter `reference_date DATE` na Gold/provenance para compatibilidade com `SPEC-007`. Adicionar coluna `reference_year INT` na Silver/Gold. |
| DV2 | `metric_id = 'divida_consolidada_liquida'` | CSV traz **Dívida Consolidada bruta** (PAF); DCL exigiria deduzir haveres (outra fonte) | `metric_id = 'divida_consolidada'`; rótulo do card = "Dívida Consolidada dos Estados (PAF)". DCL/RCL fica como trabalho futuro (fora do escopo da fatia — DEFINE fixou 1 dataset). |
| DV3 | de-para `nome do ente → state_ibge_code` | chave é `UF` de 2 letras | de-para = `UF (2 letras) → state_ibge_code (2 dígitos IBGE)`; arquivo `ingestion/reference/uf_ibge.csv` (27 UF + DF). Ex.: `AC→12`, `AL→27`, `DF→53`, `SP→35`. |

## 4. Residual

- **URL do catálogo no dados.gov.br não confirmada** — a API pública do Portal retornou HTTP 401 (exige chave). O dataset é catalogado pelo Tesouro Transparente (CKAN); é quase certo que há entrada espelhada no dados.gov.br.
  - Impacto: relevante para a atribuição no **2º Concurso de Reúso da CGU** (`CONTEXTO §4` — "informar URLs dos conjuntos utilizados", "dataset catalogado no Portal"), **não** para o código do connector.
  - Ação: usuário confirma a URL no Portal ou fornece chave de API; registrar em `dataset_registry.source_url` (catálogo) mantendo `resource_url` = URL do CKAN acima.

## 5. Impacto no contrato v1 (para o `/iterate` no DESIGN)

```yaml
dataset: divida_consolidada_estados
version: 1
source:
  catalog: dados.gov.br            # URL a confirmar (residual)
  resource_url: https://www.tesourotransparente.gov.br/ckan/.../divida-consolidada-dos-estados---paf.csv
  organization: COREM / STN
  license: ODbL
  update_frequency: annual
format: {type: csv, delimiter: ";", decimal: ",", thousands: ".", encoding: utf-8}
source_columns: [UF, ANO, VALOR]
keys: [state_ibge_code, reference_year]
required_fields:
  state_ibge_code: {type: STRING, nullable: false}   # via de-para UF→IBGE
  reference_year:  {type: INT64,  nullable: false}
  reference_date:  {type: DATE,   nullable: false}   # DATE(ANO,12,31)
  value:           {type: NUMERIC, nullable: false, min: 0}
  unit:            {type: STRING, nullable: false, allowed: [BRL]}
freshness: {max_age_days: 500}     # atualização anual
quality_rules:
  - completeness_27_uf_plus_df: "count(distinct state_ibge_code) = 28"
  - provenance_coverage: "toda linha de métrica tem linha em metric_provenance"
evolution_policy: additive_only
```

## 6. Confirmações que se mantêm

- Volume trivial (<10 KiB, ~216 linhas) — batch, execução manual. ✅ (DEFINE A2 parcial)
- Sem PII — só entes públicos. ✅
- Valor diretamente utilizável, sem derivação pesada. ✅ (DEFINE A2)
- Licença aberta (ODbL) compatível com reúso e com o concurso. ✅
