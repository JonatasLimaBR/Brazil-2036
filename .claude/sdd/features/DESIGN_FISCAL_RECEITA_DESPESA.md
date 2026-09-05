# DESIGN — FISCAL_RECEITA_DESPESA

## Metadados

- **Feature:** FISCAL_RECEITA_DESPESA
- **Status:** ✅ Complete (Built)
- **Fase:** 2 (Design)
- **Entrada:** `.claude/sdd/features/DEFINE_FISCAL_RECEITA_DESPESA.md` (Clarity 14/15)
- **Criado:** 2026-09-05
- **Idioma:** PT-BR
- **Branch:** a criar — `feature/fiscal-receita-despesa`
- **Confiança:** 0.85 — sem `kb/` do plugin; padrões vêm do código já existente
  (`connectors/base.py`, `pipeline.py`, `pipeline_incremental.py`, `bronze.py`, `contract.py`,
  `provenance.py`) + descoberta real do recurso (arquivo baixado e inspecionado, não suposição).
- **Próximo passo:** `/build .claude/sdd/features/DESIGN_FISCAL_RECEITA_DESPESA.md`

> Nota: assets do plugin SDD ausentes — documento segue a lista de seções do skill `sdd-design`.

---

## 0. Descoberta real (tarefa 1 — resolve OQ1–OQ5 do DEFINE)

Diferente das 2 fatias anteriores, aqui a fonte real **não era conhecida no Brainstorm/Define**.
Descoberta feita nesta sessão de `/design`, com download e inspeção real do arquivo (não suposição
de schema):

- **Organização candidata descartada:** SICONFI (API REST/JSON, `apidatalake.tesouro.gov.br`,
  parametrizada por `id_ente`/IBGE, formato RREO/RGF por ente) — integração de forma totalmente
  diferente dos 3 conectores já existentes (todos file-based via CKAN), e o RREO é por ente
  (relevante para `EPIC-012`, estados/municípios), não para o governo central consolidado que
  este `EPIC-009` pede.
- **Fonte escolhida:** **Tesouro Transparente / CKAN**, dataset **"Resultado do Tesouro Nacional —
  Série Histórica"** (slug `resultado-do-tesouro-nacional`, `package_id`
  `ab56485b-9c40-4efb-8563-9ce3e1973c4b`, organização CESEF, licença **ODbL** — mesma licença do
  dataset da dívida). Mesmo portal/plataforma da fatia #1 (`divida_estados.py` já sabe falar CKAN).
- **Recurso real baixado e inspecionado:** "Resultado do Tesouro Nacional - Série Histórica -
  Mensal", XLSX, **4.301.280 bytes** (tamanho batendo exatamente com o anunciado pelo CKAN),
  atualizado mensalmente **no mesmo objeto** (nome de arquivo muda por mês —
  `seriehistoricajul26.xlsx` — mas o `resource_id` do CKAN, `527ccdb1-...`, é estável; o conector
  deve resolver a URL atual via `resource_show`, nunca por convenção de nome de arquivo — mesmo
  princípio já provado no D2 do INSS).
- **Estrutura real (não documentação, arquivo aberto de verdade):** 27 abas, cada uma uma tabela
  numerada do relatório oficial "RTN". A aba **"1.2" — "Resultado Primário do Governo Central -
  Brasil - Mensal"** é uma tabela **larga**: 1 linha por rubrica hierárquica (`1. RECEITA TOTAL`,
  `1.1 Receita Administrada pela RFB`, ... até `10. RESULTADO NOMINAL`), **356 colunas**, uma por
  mês, de **1997-01 a 2026-07**, valores em **R$ Milhões, valores correntes**.
- **3 linhas de interesse confirmadas por inspeção real (valor de jul/2026, R$ milhões):**
  - `1. RECEITA TOTAL` = 275.883,96
  - `3. RECEITA LÍQUIDA (1-2)` = 226.305,45 (após transferências por repartição de receita)
  - `4. DESPESA TOTAL` = 215.522,02
  - `5. RESULTADO PRIMÁRIO GOVERNO CENTRAL - ACIMA DA LINHA (3 - 4)` = 10.783,43 —
    **confirmado por conta**: 226.305,45 − 215.522,02 = 10.783,43. A fonte já publica o resultado
    primário pronto; não precisamos calculá-lo (resolve OQ3 na direção mais simples).
- **Achado crítico (não assumir "sem risco" — confirmado por inspeção real de 356 meses):**
  **135 dos 356 meses (38%) têm resultado primário negativo** (déficit), incluindo meses recentes
  (2025-11, 2026-02, 2026-03, 2026-05, 2026-06 — todos negativos, valores de dezenas de bilhões).
  `ingestion/src/ingestion/contract.py::check_gold_period` hoje **rejeita incondicionalmente
  qualquer valor negativo** (`if any(_as_decimal(r.get(value_field)) < 0 ...)`) — reusar esse
  check sem ajuste **quarentenaria ~38% dos dados legítimos**, incluindo os meses mais recentes.
  Ver D10.
- **OQ4 (nomenclatura) resolvida:** `metric_id`s = `fiscal_receita`, `fiscal_despesa`,
  `fiscal_primario` — nomes genéricos o bastante (o rótulo exato "Receita Líquida" vs "Receita
  Total" vira decisão de mapeamento de linha, D4, não de nome de métrica).
- **OQ5 (cap de bytes por query):** o dataset final é pequeno (356 meses × 3 métricas = 1.068
  linhas Gold no máximo) — risco residual do `CI_ASSURANCE_GATES` (`R-012`) não piora nesta
  fatia; não precisa de ação nova.

---

## 1. Grounding

| Padrão a reaproveitar | Fonte |
|---|---|
| `connectors/base.py` (`Connector` protocol: `discover/download/validate/checkpoint`) | `MVP_WALKING_SKELETON` |
| Conector CKAN + XLSX→CSV via `openpyxl` (mesmo formato de origem) | `inss_indeferidos.py` |
| `bronze.load()` (CREATE OR REPLACE — seguro aqui, tabela exclusiva desta fatia, não compartilhada) | `pipeline.py` (MVP) |
| `registry.upsert_dataset_registry()` (MERGE, já seguro para tabelas compartilhadas) | correção crítica do INSS |
| `provenance.write_from_gold()` (já seguro; estendido nesta fatia — D9) | correção crítica do INSS |
| `contract.check_gold_period()` (já genérico por `key_fields`; estendido nesta fatia — D10) | INSS |
| `Config.metric_tables` + `GET /v1/metrics/{metric_id}/national` (já genérico por `metric_id`) | INSS PR2 |
| Padrão de teste e2e do módulo M03, incluindo a lição do achado ao vivo pós-merge (escopar seletores CSS a um container, não a classe global) | `INSS_BENEFICIOS` + fix `#14` |

---

## 2. Arquitetura

```text
┌──────────────────────────────────────────────────────────────────────────┐
│  Tesouro Transparente (CKAN) — dataset "resultado-do-tesouro-nacional"    │
│  resource_id 527ccdb1-... (URL muda de nome por mês, id estável)         │
└───────────────────────────────┬────────────────────────────────────────┘
                                 │ resource_show (D1) → URL atual → download
                                 ▼
                    ┌────────────────────────┐
                    │ FiscalUniaoConnector    │  (D3/D4/D5/D6/D7)
                    │ discover/download/      │
                    │ validate/checkpoint     │
                    └───────────┬────────────┘
                                 │ payload = XLSX original (bytes)
                                 ▼
                    ┌────────────────────────┐
                    │ GCS RAW (imutável)      │  D6: bytes originais do XLSX,
                    │ gs://.../fiscal_uniao/  │  SHA-256 do conteúdo real
                    └───────────┬────────────┘
                                 │ parse local (openpyxl, aba "1.2",
                                 │ pivota wide→long, 3 linhas × 356 meses)
                                 ▼
                    ┌────────────────────────┐
                    │ pipeline_wide_series.py │  (D8 — módulo novo)
                    │ run() 1x por execução   │
                    └───────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                   ▼
        Bronze (whole-table    Silver (pivota,   Gold: gold_fiscal_uniao
        load, tabela exclusiva  converte unidade  (metric_id, reference_date,
        desta fatia — CREATE    R$ milhões→R$,    value, unit='BRL',
        OR REPLACE é seguro)    D7)               data_class='observed')  (D2)
                                                        │
                                                        ▼
                                          metric_provenance (D9: escopo por
                                          metric_id inteiro, sem filtro de
                                          data — série recomputada por run)
                                                        │
                                                        ▼
                              Config.metric_tables: fiscal_receita/
                              fiscal_despesa/fiscal_primario → gold_fiscal_uniao
                              (D11 — SEM mudar main.py/bigquery_repo.py)
                                                        │
                                                        ▼
                              GET /v1/metrics/{metric_id}/national (já existe)
                                                        │
                                                        ▼
                              web/src/fiscal.ts — módulo M02 na Landing
```

---

## 3. Decisões (ADRs inline)

### D1 — Fonte real: "Resultado do Tesouro Nacional" (RTN), não SICONFI/RREO

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-05 |

**Contexto:** o DEFINE deixou a fonte em aberto (`OQ1`) por decisão explícita do usuário. Duas
candidatas: SICONFI (API REST por ente) e Tesouro Transparente/CKAN (arquivos, mesmo portal da
fatia #1).

**Escolha:** dataset RTN do Tesouro Transparente/CKAN — arquivo real baixado e inspecionado
(`§0`), contém receita, despesa e resultado primário do Governo Central consolidado, mensal,
desde 1997, licença ODbL.

**Racional:** reaproveita a mesma integração CKAN já provada (`divida_estados.py`); dado
consolidado nacional bate exatamente com o grão "total agregado" já fixado no DEFINE (`C6`); a
alternativa SICONFI exigiria um conector de API REST paginada por ente — uma forma de integração
nunca antes usada no projeto, e mais adequada a uma fatia futura por UF/município (`EPIC-012`).

**Alternativas rejeitadas:**
1. *SICONFI/RREO* — rejeitada: forma de integração nova (REST/JSON por `id_ente`), e o grão por
   ente é mais relevante a um domínio diferente (`EPIC-012`).
2. *Fixar a fonte sem descoberta real* — já rejeitada no Brainstorm (Abordagem C).

**Consequências:** (+) reaproveita 100% o padrão CKAN já revisado; (+) 1 único arquivo cobre
receita, despesa e primário, evitando 2-3 conectores. (−) o arquivo é grande (27 abas, ~200
linhas cada) — o parser precisa localizar a aba/linha certa por rótulo, não por posição fixa
ingênua (mitigado: rótulos como `"1. RECEITA TOTAL"` são estáveis há décadas no mesmo relatório
oficial; validar isso é parte do contrato, D-abaixo).

### D2 — 1 tabela Gold (`gold_fiscal_uniao`) com 3 `metric_id`s, não 3 tabelas separadas

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-05 |

**Contexto:** o DEFINE (`C5`) fixou "2 tabelas Gold separadas" seguindo o precedente do INSS (não
fundir datasets semanticamente distintos). A descoberta real muda a premissa: aqui, receita,
despesa e primário **não são 3 datasets/arquivos/schemas diferentes** — são 3 linhas da **mesma**
tabela, do **mesmo** arquivo, no **mesmo** grão (mês), relacionadas por uma equação
(`primário = receita − despesa`) que a própria fonte publica.

**Escolha:** **1 tabela Gold** (`gold_fiscal_uniao`), schema idêntico ao já usado em
`gold_debt_state_current`/`gold_inss_*` (`metric_id, reference_date, value, unit, data_class`),
com 3 valores de `metric_id`: `fiscal_receita`, `fiscal_despesa`, `fiscal_primario`.

**Racional:** o motivo original de não fundir (semânticas de dataset distintas) não se aplica
aqui — são 3 métricas de uma mesma série oficial. `Config.metric_tables` já é
`Mapping[str, str]` (metric_id → tabela): mapear as 3 chaves para a mesma tabela funciona sem
qualquer mudança em `bigquery_repo.py`/`main.py` (D11), porque a query final sempre filtra por
`metric_id`.

**Alternativas rejeitadas:**
1. *3 tabelas separadas (seguir C5 do DEFINE ao pé da letra)* — rejeitada após a descoberta real:
   mais 2 arquivos SQL/contrato sem ganho de isolamento, já que as 3 métricas nunca variam
   independentemente (vêm do mesmo download).

**Consequências:** (+) menos arquivos, mesmo schema genérico já usado 2x; (+) uma consulta
`WHERE metric_id IN (...)` já traz as 3 métricas juntas se o produto precisar no futuro. (−)
revisão explícita de uma decisão do DEFINE — registrada aqui como refinamento pós-descoberta, não
como mudança de requisito (o requisito — G3, 2 tabelas — vira G3-refinado; documentado na revision
history do DEFINE ao fim deste ciclo).

### D3 — 1 conector, pivota 3 linhas da aba "1.2" de wide para long

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-05 |

**Contexto:** `OQ2`/`A5` do DEFINE perguntavam se 1 ou 2 conectores seriam necessários.

**Escolha:** `FiscalUniaoConnector` (1 só) baixa o XLSX, abre com `openpyxl` (`read_only=True`,
`data_only=True`), localiza a aba `"1.2"` e as 3 linhas por rótulo (não por índice fixo — rótulos
como chave de busca, tolerante a uma linha a mais/menos ter sido inserida entre as versões
mensais do arquivo), e escreve um CSV intermediário longo:
`metric_id, reference_date, value_brl_millions` (356 × 3 = 1.068 linhas).

**Racional:** confirma `A5` (1 recurso basta); reaproveita o padrão XLSX→CSV via `openpyxl` já
testado em produção (`inss_indeferidos.py`), só trocando "linha de tabela = 1 registro" por
"célula de uma linha-alvo × coluna de mês = 1 registro" (pivot).

**Alternativas rejeitadas:**
1. *Carregar a aba inteira (todas as ~200 linhas) para o Bronze e pivotar em SQL* — rejeitada:
   traria dezenas de rubricas irrelevantes (ex. "IPI - Fumo") para dentro do Bronze/contrato sem
   necessidade; mais superfície de contrato para manter.

**Consequências:** (+) Bronze/contrato enxutos, só as 3 métricas que o produto usa; (−) se um
rótulo mudar de texto entre uma versão do arquivo e outra, o parser falha alto e visível (fail
loud) em vez de silenciosamente pegar a linha errada — comportamento desejado, tratado como
"schema drift" pelo contrato (mesmo espírito do `check_bronze_schema` já existente).

### D4 — `fiscal_receita` = Receita Líquida (linha "3."), não Receita Total (linha "1.")

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-05 |

**Contexto:** a fonte publica `1. RECEITA TOTAL` (bruta) e `3. RECEITA LÍQUIDA (1-2)` (após
transferências por repartição de receita a estados/municípios). O `5. RESULTADO PRIMÁRIO` já
publicado é `3 − 4` (Líquida menos Despesa Total), não `1 − 4`.

**Escolha:** `fiscal_receita` mapeia para a linha `3. RECEITA LÍQUIDA (1-2)`.

**Racional:** se `fiscal_receita` usasse a Receita Total (linha 1), `fiscal_receita −
fiscal_despesa` **não bateria** com `fiscal_primario` publicado — dois números de "resultado"
divergentes no mesmo produto é exatamente o tipo de inconsistência que `ADR-012` (nunca deixar
fabricar/confundir uma métrica oficial) quer evitar, mesmo sem LLM envolvido. O módulo M02 rotula
explicitamente "Receita líquida" (não só "Receita"), para não sugerir que é a arrecadação bruta.

**Alternativas rejeitadas:**
1. *Receita Total (linha 1), mais intuitiva para leigo* — rejeitada: quebra a consistência
   aritmética com o primário publicado; um usuário que somasse os 2 números do módulo teria uma
   conta que não fecha com o 3º número mostrado.

**Consequências:** (+) os 3 números do módulo M02 sempre se conciliam entre si; (−) rótulo
"Receita líquida" é menos familiar que "Receita" simples — mitigado com um tooltip/nota de
provenance apontando a linha exata da fonte oficial.

### D5 — Resultado primário ingerido direto da fonte, não recalculado por nós

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-05 |

**Contexto:** o DEFINE (`G10`) previa resultado primário como métrica **derivada**
(`receita − despesa`), SHOULD, condicionada aos 2 grãos baterem. A descoberta real mostra que a
fonte já publica a linha `5. RESULTADO PRIMÁRIO ... (3-4)` pronta — e que ela pode divergir de um
recálculo simplista por causa da linha `6. AJUSTES METODOLÓGICOS` (existe na tabela, ainda que
vazia nos meses recentes inspecionados).

**Escolha:** `fiscal_primario` é ingerido diretamente da linha 5 publicada, não recalculado em
SQL/Python a partir de `fiscal_receita`/`fiscal_despesa`.

**Racional:** mais fiel à fonte oficial (nunca fabricar um número que a própria fonte já
publica); resolve `OQ3` na direção mais simples (sem rota de API dedicada, sem cálculo
client-side); e — por vir do mesmo arquivo/linha-grão — `A1` (grãos precisam bater) fica
automaticamente satisfeita, então esta meta sobe de **SHOULD condicional para MUST direto**.

**Alternativas rejeitadas:**
1. *Calcular no cliente web (`receita − despesa`)* — rejeitada: arrisca divergir do número oficial
   por causa de ajustes metodológicos não capturados nos 2 valores base.

**Consequências:** (+) mais simples que o previsto no DEFINE; (+) sempre consistente com a fonte
oficial. (−) nenhuma relevante identificada.

### D6 — RAW preserva o XLSX original bit-a-bit

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-05 |

**Contexto:** achado **W1** do `/verify-spec` do INSS: `InssIndeferidosConnector` gravava em RAW
o CSV convertido, não os bytes originais do XLSX — aceito como desvio de baixa prioridade, mas
registrado como algo a evitar quando evitável.

**Escolha:** `write_raw()` recebe os bytes originais do XLSX (não uma conversão); o parse
(pivot wide→long) acontece **depois**, em memória, só para alimentar o Bronze — nunca substitui o
que vai para RAW.

**Racional:** o arquivo tem só 4,3 MB (não há motivo de memória/custo para não preservar o
original, ao contrário do XLSX multi-arquivo do INSS); corrige preventivamente o mesmo padrão de
desvio já visto uma vez.

**Consequências:** (+) RAW imutável e auditável fiel ao artefato real da fonte; nenhuma
contrapartida relevante dado o tamanho pequeno do arquivo.

### D7 — Unidade convertida de R$ Milhões (fonte) para R$ (reais) na Silver

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-05 |

**Contexto:** a fonte publica em "R$ Milhões" (ex.: `275883.96` = R$ 275.883.960.000,00). O
`MetricResponse`/`NationalMetricResponse` existentes usam `unit: "BRL"` sem sufixo de escala; o
formatter do web (`Intl.NumberFormat('pt-BR', {style:'currency', currency:'BRL'})`) já assume
valor em reais, não em milhões.

**Escolha:** `sql/silver/fiscal_uniao.sql` multiplica o valor por 1.000.000 ao promover
Bronze→Silver; `unit` gravado como `"BRL"`, igual às 2 fatias anteriores.

**Racional:** evita introduzir uma unidade nova (`"BRL_MM"`) que exigiria mudar o formatter do
frontend e o contrato de resposta da API — mudança de superfície pública desnecessária para um
ajuste que cabe inteiramente dentro do pipeline de ingestão.

**Consequências:** (+) nenhuma mudança de contrato de API/frontend; (−) nenhuma relevante.

### D8 — Novo módulo `pipeline_wide_series.py` (nem `pipeline.py` nem `pipeline_incremental.py`)

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-05 |

**Contexto:** `pipeline.py` (MVP) é hardcoded ao dataset da dívida (nomes de SQL fixos,
`reference_year` anual, checagem de território). `pipeline_incremental.py` (INSS) assume
"1 chamada = 1 recurso novo a ser baixado e escrito numa partição de mês" — o modelo certo quando
cada mês é um arquivo CKAN separado e imutável. Aqui, **1 único download já contém os 356 meses**,
e a fonte **sobrescreve o mesmo arquivo todo mês** (não é imutável por natureza) — nem o padrão
"1 arquivo = todo o histórico, nunca muda" (dívida) nem "1 arquivo por período, imutável" (INSS)
descreve exatamente essa forma.

**Escolha:** `pipeline_wide_series.py` — módulo novo, específico para "1 download = série larga
completa, recomputada inteira a cada execução": baixa 1x, grava RAW 1x (D6), carrega Bronze como
tabela inteira (`bronze.load()`, CREATE OR REPLACE — seguro aqui porque a tabela é exclusiva desta
fatia, não compartilhada), roda Silver/Gold pivotando as 3 métricas × todos os períodos presentes
no arquivo numa passada, e escreve provenance para os 3 `metric_id`s de uma vez (D9).

**Racional:** mesma filosofia usada para criar `pipeline_incremental.py` no INSS — quando a forma
do dado não cabe no módulo existente, criar um módulo novo dedicado em vez de forçar uma
abstração incorreta; `pipeline.py`/`pipeline_incremental.py` continuam intocados, sem risco de
regressão nas 2 fatias anteriores.

**Alternativas rejeitadas:**
1. *Forçar em `pipeline_incremental.py`, chamando `run()` 356 vezes (1 por mês)* — rejeitada:
   rebaixaria 356 downloads do mesmo arquivo de 4,3 MB por execução (desperdício), e o modelo de
   "1 chamada = 1 recurso" do `Connector` não descreve "1 recurso já baixado, N períodos dentro
   dele".

**Consequências:** (+) cada módulo de pipeline continua simples e correto para a forma de dado
que resolve; (−) 3º módulo de orquestração no `ingestion/`, mais uma coisa a entender — mitigado
por ser pequeno e por reaproveitar `bronze.load`/`registry`/`provenance`/`contract` como os
outros 2.

### D9 — `provenance.write_from_gold` ganha `reference_date: dt.date | None = None`

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-05 |

**Contexto:** a assinatura atual exige uma `reference_date` (escopo `DELETE`+`INSERT` por
`metric_id, reference_date`) — correto para "1 execução = 1 período novo" (dívida: 1
ano/execução; INSS: 1 mês/execução). Aqui, **1 execução recomputa os 356 meses inteiros** de uma
vez — não há um único período para escopar.

**Escolha:** `reference_date` vira `dt.date | None = None`; quando `None`, o escopo do
`DELETE`+`INSERT` é `WHERE metric_id = @metric_id` (sem filtro de data) — a provenance inteira
daquele `metric_id` é substituída atomicamente a cada execução, coerente com "a série inteira é
recomputada a cada run".

**Racional:** extensão aditiva — o parâmetro tem default `None`? **Não**: para não mudar
silenciosamente o comportamento de quem já chama a função sem pensar no novo parâmetro, `None`
só é usado quando **passado explicitamente**; chamadas existentes (dívida, INSS) continuam
passando uma `reference_date` real e mantêm exatamente o comportamento atual (escopo por
metric_id + 1 data), verificado por teste de regressão.

**Alternativas rejeitadas:**
1. *Uma função nova `write_from_gold_full_series()` em vez de estender a existente* — rejeitada:
   duplicaria toda a lógica de `DELETE`+`INSERT`+`SELECT COUNT` só para trocar a cláusula `WHERE`;
   o parâmetro opcional é a mudança mínima.

**Consequências:** (+) reaproveita 100% a lógica já provada e testada; (−) a função ganha 1
branch condicional a mais — mitigado com teste explícito para os 2 caminhos (`None` e com data).

### D10 — **CRÍTICO**: `contract.check_gold_period` ganha `allow_negative: bool = False`

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-05 |

**Contexto:** achado da descoberta real (`§0`): **135 dos 356 meses reais (38%) de resultado
primário são negativos**, incluindo os meses mais recentes disponíveis (2025-11 a 2026-06).
`check_gold_period` hoje **rejeita incondicionalmente qualquer valor negativo**
(`if any(_as_decimal(r.get(value_field)) < 0 ...): violations.append(...)`), com `raise_if_broken`
levando a `Quarantined` — se não corrigido, **qualquer execução real que inclua um mês de déficit
primário quarentenaria a carga inteira daquele mês**, o que descreve boa parte da série histórica
E os meses mais recentes.

**Escolha:** `check_gold_period(..., allow_negative: bool = False)` — default `False` preserva o
comportamento atual para a dívida e o INSS (nenhum dos dois tem valores legitimamente negativos);
o pipeline desta fatia passa `allow_negative=True` **só ao validar `fiscal_primario`**
(receita/despesa continuam validadas com o default `False` — ambas são sempre ≥ 0 na fonte real,
confirmado por inspeção).

**Racional:** este é o achado crítico desta fatia, análogo ao `CREATE OR REPLACE` em tabela
compartilhada do INSS — encontrado por inspeção de dado real *antes* de escrever qualquer linha
de conector, não depois de uma carga real falhar em produção. Sem essa correção, o `/build` teria
uma ilusão de "funciona" contra meses de superávit e quebraria silenciosamente (ou
ruidosamente, em quarentena) assim que tocasse um mês de déficit real — o que descreve boa parte
da série e os meses mais recentes disponíveis.

**Alternativas rejeitadas:**
1. *Não usar `check_gold_period` para `fiscal_primario`, pular a validação de contrato pra essa
   métrica* — rejeitada: perderia a checagem de nulos/cobertura de provenance também, não só a de
   sinal.
2. *Validar `fiscal_primario` numa chamada separada de `check_gold_period` com `key_fields`/
   `value_field` diferentes* — desnecessário, um parâmetro booleano resolve com o mínimo de
   mudança de superfície.

**Consequências:** (+) a série histórica real (incluindo déficits, comuns na história fiscal do
Brasil) carrega sem falso-positivo de quarentena; (+) receita/despesa continuam protegidas contra
valor negativo de verdade (que seria, de fato, um sinal de erro de schema/parse). (−) nenhuma
relevante — é uma correção pura, sem trade-off.

### D11 — `Config.metric_tables` ganha as 3 entradas, sem mudar `main.py`/`bigquery_repo.py`

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-05 |

**Contexto:** achado técnico do Brainstorm/DEFINE (`A2`): `GET /v1/metrics/{metric_id}/national`
+ `Config.metric_tables` já são genéricos por `metric_id` desde o PR2 do INSS.

**Escolha:** `api/src/api/config.yaml` ganha `fiscal_receita`, `fiscal_despesa`,
`fiscal_primario` → `gold_fiscal_uniao` (as 3 apontando para a **mesma** tabela, D2). Nenhuma
mudança em `main.py`/`bigquery_repo.py`/`models.py` é necessária — confirmado por leitura do
código atual (`api/src/api/main.py::get_national_metric`, `Config.metric_tables:
Mapping[str, str]`).

**Racional:** confirma `A2` como verdadeira — ao contrário do achado técnico do INSS (que exigiu
trabalho real de API), aqui o reuso é genuinamente gratuito, por já ter sido generalizado na
fatia anterior.

**Consequências:** (+) PR2 desta fatia fica pequeno: 1 mudança de config YAML + módulo web +
testes de regressão; nenhuma contrapartida.

---

## 4. Manifesto de arquivos

### PR1 — espinha de dados

| # | Arquivo | Ação | Propósito | Agente | Deps |
|---|---|---|---|---|---|
| 1 | `docs/adrs/ADR-056-fiscal-uniao-wide-series-ingestion.md` | Create | Formaliza D1, D2, D8, D9, D10 | `architect` | — |
| 2 | `ingestion/src/ingestion/connectors/fiscal_uniao.py` | Create | `Connector` CKAN + XLSX→pivot (D1/D3/D4/D5/D6/D7) | `ai-data-engineer-gcp` | — |
| 3 | `ingestion/tests/test_connector.py` | Modify | +suite `fiscal_uniao` (fixture XLSX pequena, incluindo ≥1 mês negativo) | `python-reviewer` | 2 |
| 4 | `ingestion/src/ingestion/contract.py` | Modify | `check_gold_period(..., allow_negative: bool = False)` (D10) | `python-developer` | — |
| 5 | `ingestion/tests/test_contract.py` | Modify | +caso `allow_negative=True` aceita negativo; regressão do default `False` | `python-reviewer` | 4 |
| 6 | `ingestion/src/ingestion/provenance.py` | Modify | `reference_date: dt.date \| None = None` (D9) | `python-developer` | — |
| 7 | `ingestion/tests/test_provenance.py` | Modify | +caso `None` (escopo todo-metric_id); regressão do caso com data | `python-reviewer` | 6 |
| 8 | `ingestion/src/ingestion/pipeline_wide_series.py` | Create | Orquestrador novo (D8): download 1x → RAW → Bronze whole-table → Silver/Gold pivot → provenance | `python-developer` | 2,4,6 |
| 9 | `ingestion/tests/test_pipeline_wide_series.py` | Create | Unit com `FakeBigQuery`/`FakeStorage`, cobre mês negativo e positivo | `python-reviewer` | 8 |
| 10 | `ingestion/contracts/fiscal_uniao.yaml` | Create | Schema (`metric_id, reference_date, value`), `NOT NULL` em chaves | `data-contracts-engineer` | — |
| 11 | `ingestion/sql/silver/fiscal_uniao.sql` | Create | Converte unidade (D7), 1 linha por `(metric_id, reference_date)` | `sql-optimizer` | — |
| 12 | `ingestion/sql/gold/gold_fiscal_uniao.sql` | Create | Grão `(metric_id, reference_date)`, `unit='BRL'`, `data_class='observed'` | `sql-optimizer` | 11 |
| 13 | `ingestion/config/fiscal_uniao.yaml` | Create | `dataset_id`, `ckan_package_id`/`resource_id`, tabelas, `contract_path` | `(general)` | — |
| 14 | `ingestion/tests/integration/fixtures/fiscal_uniao_sample.xlsx` | Create | Fixture pequena (poucos meses, incluindo ≥1 negativo) | `(general)` | — |
| 15 | `ingestion/tests/integration/test_pipeline_fiscal_bigquery.py` | Create | `@pytest.mark.integration` contra BigQuery real (G6); prova que o mês negativo não quarentena | `data-quality-analyst` | 8,14 |
| 16 | `INDEX.md` | Modify | +ADR-056, +contrato, +SQL novos | `(general)` | 1,10 |

### PR2 — apresentação

| # | Arquivo | Ação | Propósito | Agente | Deps |
|---|---|---|---|---|---|
| 17 | `api/src/api/config.yaml` | Modify | +3 entradas em `metric_tables` → `gold_fiscal_uniao` (D11) | `(general)` | PR1 completo |
| 18 | `api/tests/test_bigquery_repo.py` | Modify | +casos `fiscal_receita`/`_despesa`/`_primario` (incl. valor negativo em `_primario`); regressão dívida+INSS | `python-reviewer` | 17 |
| 19 | `web/src/fiscal.ts` | Create | Módulo M02: "Receita líquida" (D4), "Despesa total", "Resultado primário" (formata negativo como déficit, não erro) | `typescript-reviewer` | 17 |
| 20 | `web/src/main.ts` | Modify | `void renderFiscalModule();` (mesmo padrão de `renderInssModule`) | `typescript-reviewer` | 19 |
| 21 | `web/tests/e2e/card.spec.ts` | Modify | +suite M02; **todo seletor CSS de classe genérica (`.data-class--*`) escopado a um container**, não solto na página — lição do achado ao vivo pós-INSS (PR #14) | `python-reviewer` | 19 |

### Racional de agentes
Conector de dados → `ai-data-engineer-gcp`; SQL de agregação/pivot → `sql-optimizer`; contrato →
`data-contracts-engineer`; pipeline/orquestração/extensões de módulo Python → `python-developer`;
revisão e testes → `python-reviewer`; frontend → `typescript-reviewer`; ADR → `architect`.

### Independência
PR1 é autocontido. PR2 depende de PR1 mergeado (a Gold precisa existir). Sem ciclo:
`fiscal_uniao.py` → `pipeline_wide_series.py` → SQL → `Config.metric_tables` → web. Os itens 4-7
(contract/provenance) são extensões aditivas de módulos já usados pela dívida e pelo INSS —
cobertos por teste de regressão explícito (item 5 e 7) antes de qualquer coisa nova depender
deles.

---

## 5. Padrões de código

### 5.1 `fiscal_uniao.py` — parser de linha por rótulo (não por índice fixo)

```python
# Pattern: localizar linha-alvo por texto de rótulo, tolerante a variação de
# posição entre versões mensais do arquivo — nunca por índice de linha fixo.
_TARGET_ROWS = {
    "fiscal_receita": "3. RECEITA LÍQUIDA",       # D4: líquida, não total
    "fiscal_despesa": "4. DESPESA TOTAL",
    "fiscal_primario": "5. RESULTADO PRIMÁRIO GOVERNO CENTRAL - ACIMA DA LINHA",
}


def _find_row(rows: list[tuple[object, ...]], label_prefix: str) -> tuple[object, ...]:
    for row in rows:
        label = row[0]
        if isinstance(label, str) and label.strip().startswith(label_prefix):
            return row
    raise SchemaDriftError(f"row starting with {label_prefix!r} not found — source layout changed")
```

### 5.2 `contract.py` — `allow_negative` aditivo (D10)

```python
def check_gold_period(
    self,
    rows: Sequence[Mapping[str, Any]],
    *,
    key_fields: Sequence[str],
    value_field: str,
    provenance_row_count: int,
    allow_negative: bool = False,
) -> ContractResult:
    violations: list[str] = []
    for key in (*key_fields, value_field):
        if any(r.get(key) in (None, "") for r in rows):
            violations.append(f"null values in required field {key!r}")
    if not allow_negative and any(_as_decimal(r.get(value_field)) < 0 for r in rows):
        violations.append(f"negative {value_field} found")
    ...
```

### 5.3 `provenance.py` — `reference_date` opcional (D9)

```python
def write_from_gold(
    client, *, project, dataset_gold, gold_table, provenance_table,
    metric_id: str, reference_date: dt.date | None,
    source_url, silver_transform, silver_transform_version, bronze_object,
    catalog_dataset_id, producing_organization, run_id,
) -> int:
    metric_lit = sql_literal(metric_id)
    if reference_date is None:
        scope = f"metric_id = {metric_lit}"
    else:
        date_lit = sql_literal(reference_date.isoformat())
        scope = f"metric_id = {metric_lit} AND reference_date = DATE({date_lit})"
    ...  # DELETE + INSERT como hoje, só a cláusula `scope` muda
```

---

## 6. Estratégia de testes

| Tipo | Escopo | Ferramenta |
|---|---|---|
| Unit — conector | Parse de fixture XLSX pequena; localização de linha por rótulo; erro alto se rótulo sumir | `pytest` |
| Unit — contrato | `allow_negative=True` aceita negativo; default `False` ainda rejeita (regressão dívida/INSS) | `pytest` |
| Unit — provenance | `reference_date=None` escopa por `metric_id` inteiro; `reference_date=<data>` continua como hoje (regressão) | `pytest` |
| Unit — pipeline | `pipeline_wide_series.run()` com `FakeBigQuery`/`FakeStorage`, cobre mês positivo e negativo | `pytest` |
| Integração | `@pytest.mark.integration` contra BigQuery real (gate `integration`, `ci.yml`), fixture inclui ≥1 mês negativo — prova viva que D10 funciona | `pytest` + BigQuery real |
| Regressão de API | Rotas da dívida e do INSS continuam respondendo como antes após `Config.metric_tables` crescer | `pytest` |
| e2e web | Módulo M02 renderiza 3 números (ou degrada); seletor de card escopado (lição do achado pós-INSS) | Playwright |

Cobre todos os acceptance tests do DEFINE (AT1–AT11).

---

## 7. Pipeline Architecture (contexto DE)

| Aspecto | Definição |
|---|---|
| **Partição/estratégia de escrita** | Bronze: tabela inteira `CREATE OR REPLACE` (segura — exclusiva desta fatia, não compartilhada). Gold/Silver: `MERGE`-like via `DELETE metric_id IN (...) ` + `INSERT` (reescreve as 3 métricas × todos os períodos a cada run — sempre a série completa, nunca parcial). Provenance: `DELETE WHERE metric_id = X` (sem filtro de data, D9) + `INSERT`. |
| **Idempotência** | Rerodar não duplica: cada run substitui atomicamente a série inteira de cada `metric_id`. Diferente do INSS (partição por mês) porque aqui não há "meses anteriores" a preservar de um run pra outro — a fonte já entrega tudo de novo a cada vez. |
| **Schema evolution** | `check_bronze_schema` (já existente) + `_find_row` fail-loud (§5.1) cobrem drift: mudança de colunas ou sumiço de uma linha-alvo interrompe o run antes de gravar dado incorreto. |
| **Data quality gates** | `check_gold_period` com `allow_negative` correto por métrica (D10); 0 nulos em chaves; cobertura de provenance 100%. |
| **Volume** | ~1.068 linhas Gold no máximo (356 meses × 3 métricas) — trivial para BigQuery, sem revisão de cap de bytes necessária (`OQ5`). |

---

## 8. Quality gate (Fase 2)

- [x] Descoberta real feita — arquivo baixado e inspecionado, não suposição (`§0`)
- [x] ASCII diagram criado e claro (`§2`)
- [x] Pelo menos 1 decisão com racional completo (11 decisões, D1-D11)
- [x] Manifesto de arquivos completo (21 itens, PR1+PR2)
- [x] Agente atribuído a cada arquivo
- [x] Padrões de código sintaticamente corretos, prontos para copiar-adaptar
- [x] Estratégia de testes cobre todos os acceptance tests do DEFINE (AT1-AT11)
- [x] Sem dependência circular na arquitetura
- [x] Achado crítico (D10, negative primary result) documentado ANTES do build, não depois de uma
      carga real falhar
- [x] DEFINE status → `✅ Complete (Designed)`

---

## 9. Handoff

Pronto para `/build .claude/sdd/features/DESIGN_FISCAL_RECEITA_DESPESA.md`.

---

## 10. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-05 | 1.0 | Criação a partir de `DEFINE_FISCAL_RECEITA_DESPESA.md`. Descoberta real (§0) resolveu OQ1-OQ5; revisou C5 do DEFINE (1 tabela Gold, não 2 — D2) após confirmar que as 3 métricas vêm do mesmo arquivo/grão; achado crítico D10 (38% dos meses reais têm resultado primário negativo, contrato hoje rejeita incondicionalmente). 11 decisões inline (D1-D11). Manifesto 21 itens. Status → Ready for Build. | /design (Claude Sonnet 5) |
