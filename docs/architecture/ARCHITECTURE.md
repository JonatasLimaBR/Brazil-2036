# Arquitetura Completa

```text
dados.gov.br + APIs/arquivos oficiais
                |
                v
       OPEN DATA DISCOVERY
                |
       Dataset Registry
                |
       Resource Resolver
                |
       Adaptive Connectors
                |
                v
        Cloud Storage RAW
                |
           BigQuery Bronze
                |
             Dataform
                v
           BigQuery Silver
                |
      Quality / Contracts / Trust
                |
                v
            BigQuery Gold
                |
        Semantic Metric Layer
        /        |          \
       /         |           \
 Forecast      Graph         RAG
 Models        Service       AlloyDB
       \         |           /
        \        |          /
             Vertex AI
                 |
        Agent Orchestrator
                 |
   READ / COMPUTE / DRAFT agents
                 |
          Risk Evaluation
                 |
            [interrupt]
                 |
      Persisted Approval Queue
                 |
        Action Executor (rare)
                 |
          APIs / Portals
```

## Truth boundaries
BigQuery: quantitative analytical truth.
AlloyDB: transactional state/checkpoints/approvals and RAG operational needs.
LLM: reasoning/explanation only.
