# ADR-052 — SQL transformation execution for the MVP walking skeleton (refines ADR-007)

## Status
Accepted

## Contexto
Esta decisão é parte do baseline arquitetural do BRASIL 2036 e deve ser lida com o `CONTEXTO.md`.
ADR-007 fixou **Dataform** como ferramenta de transformação SQL. A fatia
`MVP_WALKING_SKELETON` (SPEC-033) tem apenas dois modelos SQL (Silver e Gold). Levantar o
Dataform — conexão de repositório, workspace, release config e integração no CI — não tem
retorno com dois modelos e amplia a superfície do primeiro PR, contra o objetivo declarado de
uma fatia vertical mínima que prova a cadeia de provenance.

Esta ADR **refina** ADR-007 para o escopo do incremento inicial; **não o substitui**. ADR-007
permanece a decisão vigente para toda transformação SQL a partir do incremento seguinte.

## Decision drivers
- segurança e auditabilidade;
- reprodutibilidade;
- escalabilidade;
- custo operacional;
- aderência ao GCP;
- clareza para portfólio e agentes de código.

## Alternativas consideradas
### A. Dataform já na fatia #1
Alternativa considerada e descartada: PR1 cresce com setup de plataforma sem consumo que o
justifique; fere YAGNI para uma fatia cujo propósito é minimizar superfície.

### B. SQL embutido em strings Python
Alternativa considerada; perde testabilidade isolada dos modelos e o caminho de migração para
Dataform.

### C. BigQuery SQL direto, arquivos no formato Dataform, adoção de Dataform adiada
Alternativa escolhida ou base para a decisão.

## Decisão
Na fatia `MVP_WALKING_SKELETON`, os modelos Silver e Gold são arquivos `.sql` **no formato
Dataform** (um `.sql` por modelo, sem glue procedural, nomes de tabela parametrizados por
configuração), **executados via cliente BigQuery** pelo job de ingestão. A criação do projeto
Dataform e a adoção dos mesmos arquivos, sem reescrita, é um **incremento subsequente**
(referência de trabalho: SPEC-033, seção de trabalho futuro).

## Por que
Honra a intenção do ADR-007 — formato explícito, testável e reprodutível — sem pagar o custo de
setup de plataforma antes de haver consumo que o justifique. A migração posterior é mecânica
porque os arquivos já seguem a convenção do Dataform.

## Consequências positivas
- comportamento mais explícito e testável;
- decisão documentada para novos desenvolvedores/agentes;
- redução de ambiguidade;
- primeiro PR menor e revisável.

## Consequências negativas / custo aceito
Existe uma janela entre a fatia #1 e o incremento de adoção do Dataform em que a execução SQL é
feita pelo job, não pelo Dataform. Aceito e limitado por esta ADR ao escopo de
`MVP_WALKING_SKELETON`.

## Verificação
A decisão deve aparecer em SPECs, testes, CI ou políticas de repositório quando aplicável —
SPEC-033 (execução SQL) e o item de trabalho futuro "adoção do Dataform".

## Quando reconsiderar
Reconsiderar — e encerrar esta refinação, voltando ao ADR-007 pleno — quando o segundo dataset
entrar (fatia #2) ou quando houver mais de dois modelos SQL, o que ocorrer primeiro.
