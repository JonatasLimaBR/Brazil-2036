# ADR-060 — Macro Twin: mais 3 séries reais e sugestão de premissas para o DebtLab

## Status
Accepted

## Contexto
Esta decisão é parte do baseline arquitetural do BRASIL 2036 e deve ser lida com o `CONTEXTO.md`.
`MACRO_TWIN_EXPANSION` continua o `EPIC-008 — Macro Twin` (`PRD-003`/`SPEC-009`) — PIB
(`STORY-008.01`) já havia sido ingerido no `DEBTLAB_SIMULATOR` (`ADR-059`) como meio para o
simulador, não como entrega do Macro Twin em si. Faltavam inflação, juros e câmbio.

Descoberta real no `/design` (`DESIGN_MACRO_TWIN_EXPANSION.md §0`), não suposição: 3 séries do BCB
SGS confirmadas por chamada direta à API, mesmo grão mensal do PIB — IPCA (série 433, "Variação
mensal", 15 meses reais confirmados, inclui um mês real de deflação: -0,11% em 08/2025), SELIC
acumulada mensal (série 4390 — não a 432, que é a meta diária do Copom, grão incompatível) e
câmbio USD/BRL médio mensal (série 3695 — não a série 1, diária).

O usuário pediu explicitamente que essas séries alimentassem de volta o `DebtLab` — hoje o usuário
digita `juros_nominal`/`crescimento_nominal_pib` sem nenhuma referência a dado real. Com SELIC e
crescimento do PIB reais agora disponíveis, um endpoint pode sugerir uma média/desvio-padrão real
para essas premissas.

## Decision drivers
- usar a série de grão certo (mensal, não diária) para cada variável;
- não fabricar nenhuma sugestão — toda média/desvio vem de cálculo determinístico sobre dado real
  (`ADR-012`);
- não alterar o contrato do `POST /v1/simulations/debtlab` já shipado e em produção;
- não misturar duas naturezas de dado (taxa vs. nível) com a mesma fórmula de conversão.

## Alternativas consideradas

### A. Usar as séries diárias (432 para SELIC, 1 para câmbio)
Consideradas e descartadas: grão incompatível com o resto do Macro Twin (PIB, dívida, IPCA — todos
mensais); exigiriam agregação adicional sem necessidade real para este caso de uso.

### B. Default automático no `POST /v1/simulations/debtlab`
Considerada e descartada: decisão explícita do usuário no `/brainstorm` — mudar o contrato de um
endpoint já shipado e testado em produção é mais arriscado e menos transparente que uma sugestão
que o chamador escolhe usar ou não.

### C. Mesma fórmula de anualização (composição) para SELIC e PIB
Considerada e descartada: PIB é um nível absoluto (R$), não uma taxa — compor 12 partes iguais
assumiria crescimento uniforme dentro do ano, uma distorção desnecessária quando o dado real já
permite comparação direta ano-contra-ano (YoY).

### D. Séries mensais corretas (433/4390/3695), conjuntos de tabelas independentes (reafirma
`ADR-059` D1), endpoint `GET` novo de sugestão com metodologia por variável
Alternativa escolhida.

## Decisão
- **Fontes:** BCB SGS séries 433 (`ipca_mensal`), 4390 (`selic_mensal`), 3695 (`cambio_usd_brl`) —
  mesmo conector genérico (`BcbSgsConnector`) e mesmo padrão de conjunto de tabelas independente
  por série já estabelecido em `ADR-059`.
- **`ipca_mensal` aceita valor negativo** (`allow_negative: true`) — único entre as séries deste
  domínio, por causa do mês real de deflação confirmado.
- **Cálculo de sugestão:**
  `juros_anual = (1 + méd(selic_mensal, 12m))^12 - 1`, desvio-padrão anualizado aproximado por
  `desvio(selic_mensal, 12m) × √12` (escalonamento linear, não uma conversão exata — documentado
  explicitamente no campo `methodology` da resposta); `crescimento_anual` = média/desvio direto
  sobre os 12 valores de variação ano-contra-ano (`PIB_M / PIB_(M-12) - 1`) dos últimos 12 meses.
- **Endpoint novo, read-only:** `GET /v1/simulations/debtlab/suggested-assumptions` — nunca grava,
  nunca é chamado automaticamente pelo `POST`. Retorna `503` (não um valor fabricado) quando há
  menos de 12 meses reais disponíveis para qualquer uma das 2 séries fonte.
- **`data_class = estimated`** (não `observed`) na resposta — é uma derivação determinística de
  dado observado, não uma leitura direta (`ADR-028`).

## Por que
Cada conversão usa a matemática correta para a natureza da série fonte (composição para taxa
mensal, YoY para nível absoluto); a aproximação de desvio-padrão da SELIC é documentada como tal
na própria resposta, nunca apresentada com precisão maior do que tem; o endpoint `GET` separado
preserva 100% de compatibilidade com o `POST` já em produção.

## Consequências positivas
- Macro Twin ganha 3 séries reais adicionais sem nenhum código novo de conector (reaproveita
  `BcbSgsConnector` como está).
- DebtLab passa a ter um caminho real, opcional, para premissas informadas por dado real, sem
  nenhum risco de regressão no endpoint já shipado.
- `ipca_mensal` prova que o padrão de `allow_negative` (já usado em `fiscal_primario`) generaliza
  bem para uma nova série com necessidade real de valor negativo.

## Consequências negativas / custo aceito
- O desvio-padrão anualizado da SELIC é uma aproximação, não uma conversão estatística exata —
  aceito e documentado explicitamente, adequado para uma *sugestão*, não uma previsão oficial.
- 3x mais arquivos repetitivos (contrato/SQL/config quase idênticos por série) — mesmo padrão já
  aceito para INSS/DebtLab, YAGNI contra um framework de templating cross-metric prematuro.

## Verificação
`ingestion/tests/test_bcb_sgs_connector.py` (reaproveitado, sem mudança — conector já genérico),
`ingestion/tests/integration/test_pipeline_bcb_macro_bigquery.py` (parametrizado sobre as 5 séries
BCB agora, real contra `brasil2036-dev`), `api/tests/test_suggested_assumptions.py` (cálculo
contra dado sintético conhecido, incluindo o caso de dado insuficiente e um teste específico de
que a rota `/suggested-assumptions` não é engolida pela rota `/{scenario_id}`),
`api/tests/test_debtlab_endpoint.py` (confirma zero regressão no `POST` já shipado).

## Quando reconsiderar
Se uma fatia futura precisar de uma conversão de desvio-padrão mais precisa que o escalonamento
linear (ex.: para um simulador que use SELIC diretamente com maior rigor estatístico), substituir
a aproximação por um cálculo real de propagação de variância — não silenciosamente, com nota
explícita da mudança de metodologia.
