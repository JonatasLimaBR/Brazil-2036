export type Status = "real" | "parcial" | "planejado";
export type PhaseStatus = "concluida" | "em_andamento" | "nao_iniciada";

export interface StatusEntry {
  id: string;
  label: string;
  status: Status;
  evidence: string;
}

export interface PhaseEntry {
  id: string;
  number: number;
  label: string;
  items: string[];
  status: PhaseStatus;
  evidence: string;
}

// Todo selo abaixo aponta para um fato real (SHIPPED doc, ADR ou Terraform) --
// nunca uma estimativa livre. DESIGN_LANDING_PAGE_ASTRO.md §0.5 tem o racional
// completo de cada entrada. Atualizar este arquivo é parte do ritual de /ship
// (mesma disciplina de sincronizar o CLAUDE.md a cada feature nova).
export const MODULE_STATUS: StatusEntry[] = [
  {
    id: "macro-twin",
    label: "Macro Economic Twin",
    status: "planejado",
    evidence: "EPIC-003, nenhum metric_id real em Gold ainda",
  },
  {
    id: "fiscal-debt",
    label: "Fiscal & Debt",
    status: "real",
    evidence: "FISCAL_RECEITA_DESPESA SHIPPED 2026-09-05 -- divida, receita, despesa e primario reais",
  },
  {
    id: "previdencia-inss",
    label: "Previdência & INSS",
    status: "parcial",
    evidence: "INSS_BENEFICIOS SHIPPED -- emitidos/indeferidos reais, mantidos sem dado real",
  },
  {
    id: "trabalho-renda",
    label: "Trabalho & Renda",
    status: "planejado",
    evidence: "EPIC-011, nenhum metric_id real em Gold ainda",
  },
  {
    id: "produtividade",
    label: "Produtividade",
    status: "planejado",
    evidence: "Sem EPIC/dataset dedicado ainda",
  },
  {
    id: "saude",
    label: "Saúde",
    status: "planejado",
    evidence: "EPIC-013, nenhum dataset ingerido ainda",
  },
  {
    id: "educacao",
    label: "Educação",
    status: "planejado",
    evidence: "EPIC-014, nenhum dataset ingerido ainda",
  },
  {
    id: "estados-municipios",
    label: "Estados & Municípios",
    status: "planejado",
    evidence: "EPIC-012, nenhum dataset ingerido ainda (a divida por UF vive dentro de Fiscal & Debt)",
  },
  {
    id: "compras-publicas",
    label: "Compras Públicas",
    status: "planejado",
    evidence: "EPIC-015 (PNCP), nenhum dataset ingerido ainda",
  },
  {
    id: "investimento-publico",
    label: "Investimento Público",
    status: "planejado",
    evidence: "Sem EPIC/dataset dedicado ainda",
  },
  {
    id: "tributacao",
    label: "Tributação",
    status: "planejado",
    evidence: "EPIC-017, nenhum dataset ingerido ainda",
  },
  {
    id: "fraude-anomalias",
    label: "Fraude & Anomalias",
    status: "planejado",
    evidence: "EPIC-019, nenhum codigo de deteccao ainda",
  },
  {
    id: "policy-lab",
    label: "Policy Lab",
    status: "planejado",
    evidence: "EPIC-023, nenhum simulador construido ainda",
  },
  {
    id: "command-center",
    label: "Command Center",
    status: "planejado",
    evidence: "EPIC-036 (Admin Center), nenhuma metrica agregada de plataforma existe ainda",
  },
  {
    id: "agent-center",
    label: "Agent Center",
    status: "planejado",
    evidence: "EPIC-026, nenhum agente em producao ainda",
  },
];

export const ARCHITECTURE_STATUS: StatusEntry[] = [
  {
    id: "cloud-storage",
    label: "Cloud Storage",
    status: "real",
    evidence: "bucket brasil2036-dev-raw, infra/terraform/storage.tf",
  },
  {
    id: "bigquery",
    label: "BigQuery",
    status: "real",
    evidence: "br2036_control/bronze/silver/gold, uso extensivo real nas 3 fatias de dados",
  },
  {
    id: "dataform",
    label: "Dataform",
    status: "planejado",
    evidence: "ADR-007 planeja; ADR-052 optou por SQL puro via client Python -- nunca provisionado",
  },
  {
    id: "pubsub-dataflow",
    label: "Pub/Sub & Dataflow",
    status: "planejado",
    evidence: "Sem recurso Terraform, sem uso real",
  },
  {
    id: "alloydb-ai",
    label: "AlloyDB & AI",
    status: "planejado",
    evidence: "ADR-004 planeja, nao provisionado",
  },
  {
    id: "vertex-ai-gemini",
    label: "Vertex AI / Gemini",
    status: "planejado",
    evidence: "Nenhum codigo de IA/agente em producao ainda",
  },
  {
    id: "cloud-run-api-gateway",
    label: "Cloud Run + API Gateway",
    status: "real",
    evidence:
      "Cloud Run real (br2036-api, br2036-web, br2036-ingestion); sem recurso formal de API Gateway -- a URL HTTPS do Cloud Run cumpre esse papel nesta fase",
  },
  {
    id: "knowledge-catalog",
    label: "Knowledge Catalog",
    status: "planejado",
    evidence: "dataset_registry e uma tabela de metadado interna, nao a capacidade de catalogo/descoberta do card",
  },
  {
    id: "iam-seguranca",
    label: "IAM & Segurança",
    status: "real",
    evidence: "WIF, sem chave estatica, ADR-040, Terraform real",
  },
  {
    id: "observabilidade",
    label: "Observabilidade (Monitoring)",
    status: "planejado",
    evidence: "So logs basicos do Cloud Run, sem dashboard formal",
  },
  {
    id: "finops",
    label: "FinOps",
    status: "parcial",
    evidence: "BIGQUERY_OPERATIONAL_STANDARDS SHIPPED -- cap por query real; orcamento/billing export (EPIC-042) nao implementado",
  },
  {
    id: "mlops-llmops",
    label: "MLOps/LLMOps",
    status: "planejado",
    evidence: "Sem modelo/agente em producao ainda",
  },
];

export const ROADMAP_PHASES: PhaseEntry[] = [
  {
    id: "fase-1",
    number: 1,
    label: "Landing Page & Marca",
    items: [
      "Naming e identidade visual em verde, amarelo e azul",
      "Landing page pública desde o início",
      "Proposta do projeto e posicionamento",
      "Call-to-actions e contato",
      "Roadmap de alto nível da plataforma",
    ],
    status: "em_andamento",
    evidence: "LANDING_PAGE_ASTRO em construção; identidade visual parcial já em styles.css",
  },
  {
    id: "fase-2",
    number: 2,
    label: "Fundação GCP",
    items: [
      "Landing zone e organização",
      "IAM e gestão de identidades",
      "Segurança, redes e firewalls",
      "IaC (Terraform) e automação",
      "Observabilidade e logging",
      "Ambientes dev/stg/prod",
    ],
    status: "em_andamento",
    evidence: "bootstrap.sh/WIF/Terraform reais (ADR-040); só ambiente dev existe, sem stg/prod",
  },
  {
    id: "fase-3",
    number: 3,
    label: "Dados Públicos",
    items: [
      "Ingestão de dados públicos",
      "Cloud Storage e versionamento",
      "BigQuery Bronze/Silver/Gold",
      "Dataform e ELT",
      "Qualidade de dados e validações",
      "Catálogo e governança",
    ],
    status: "em_andamento",
    evidence:
      "MVP_WALKING_SKELETON, INSS_BENEFICIOS, FISCAL_RECEITA_DESPESA SHIPPED; Dataform nunca usado, catálogo é só a tabela dataset_registry",
  },
  {
    id: "fase-4",
    number: 4,
    label: "Núcleo Econômico",
    items: [
      "Macro Twin (cenários macroeconômicos)",
      "DebtLab (dívida pública e risco fiscal)",
      "INSS Twin (demografia e previdência)",
      "Labor Intelligence (trabalho e renda)",
      "Municipality Twin (finanças municipais)",
    ],
    status: "nao_iniciada",
    evidence: "Dados brutos existem (Fiscal/INSS), mas nenhum Twin funcional com simulação/risco foi construído",
  },
  {
    id: "fase-5",
    number: 5,
    label: "Portais & Acessos",
    items: [
      "Portal público",
      "Portal executivo",
      "Portal analítico",
      "Portal INSS",
      "Estados e Municípios",
      "Administração da plataforma",
      "RBAC + ABAC",
      "Multi-organização",
    ],
    status: "nao_iniciada",
    evidence: "Só existe 1 landing pública, sem múltiplos portais nem RBAC/ABAC",
  },
  {
    id: "fase-6",
    number: 6,
    label: "Inteligência Avançada",
    items: [
      "Forecasting avançado",
      "RAG e chat com dados públicos",
      "Ontologia e Knowledge Graph",
      "Causal AI",
      "Simulação Monte Carlo",
    ],
    status: "nao_iniciada",
    evidence: "Nenhum código de IA/forecast/simulação existe ainda",
  },
  {
    id: "fase-7",
    number: 7,
    label: "Agentes & Simulação",
    items: [
      "Agentes especializados por domínio",
      "Orquestrador de agentes",
      "Copilotos para gestores",
      "Policy Simulator",
      "Recomendações e alertas proativos",
    ],
    status: "nao_iniciada",
    evidence: "Nenhum agente em produção (EPIC-026)",
  },
  {
    id: "fase-8",
    number: 8,
    label: "Plataforma Completa",
    items: [
      "Command Center nacional",
      "Expansão de módulos e dados",
      "Escala nacional e alta disponibilidade",
      "APIs públicas e parcerias",
      "Operação contínua e evolução",
    ],
    status: "nao_iniciada",
    evidence: "Depende de todas as fases anteriores",
  },
];
