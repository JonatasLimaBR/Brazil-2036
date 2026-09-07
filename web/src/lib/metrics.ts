import createClient from "openapi-fetch";
import type { paths } from "../api-client/schema";

const API_URL = import.meta.env.VITE_API_URL ?? "";
const client = createClient<paths>({ baseUrl: API_URL });

const brl = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
});
const count = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });

export type Formatter = "brl" | "count";

export function formatValue(value: number, formatter: Formatter = "brl"): string {
  const formatted = formatter === "brl" ? brl.format(value) : count.format(value);
  // Only currency metrics can legitimately go negative (e.g. fiscal_primario in
  // a primary deficit) -- a bare negative figure could otherwise read as a
  // data error, so it gets a plain-language qualifier instead.
  return value < 0 ? `${formatted} (déficit)` : formatted;
}

export function monthLabel(isoDate: string): string {
  const [year, month] = isoDate.split("-");
  return `${month}/${year}`;
}

interface MetricSpec {
  id: string;
  label: string;
  formatter?: Formatter;
}

interface RenderedMetric {
  spec: MetricSpec;
  dataClass?: string;
  value?: string;
  reference?: string;
  source?: string;
  error?: boolean;
}

function metricCardHtml(prefix: string, metric: RenderedMetric): string {
  if (metric.error || metric.value === undefined) {
    return `
      <article class="metric-card" data-testid="${prefix}-${metric.spec.id}">
        <p class="metric-label">${metric.spec.label}</p>
        <p class="error" role="alert">Indisponível no momento.</p>
      </article>
    `;
  }
  return `
    <article class="metric-card" data-testid="${prefix}-${metric.spec.id}">
      <span class="data-class data-class--${metric.dataClass}">${metric.dataClass}</span>
      <p class="metric-label">${metric.spec.label}</p>
      <p class="value" data-testid="${prefix}-${metric.spec.id}-value">${metric.value}</p>
      <p class="ref">referência: ${metric.reference}</p>
      <a class="source" data-testid="${prefix}-${metric.spec.id}-source" href="${metric.source}"
         target="_blank" rel="noopener noreferrer">fonte oficial</a>
    </article>
  `;
}

async function renderNationalGroup(
  rootId: string,
  prefix: string,
  metrics: MetricSpec[],
): Promise<void> {
  const root = document.querySelector<HTMLElement>(`#${rootId}`);
  if (!root) return;

  const results = await Promise.all(
    metrics.map(async (spec): Promise<RenderedMetric> => {
      const { data, error } = await client.GET("/v1/metrics/{metric_id}/national", {
        params: { path: { metric_id: spec.id } },
      });
      if (error || !data) return { spec, error: true };
      return {
        spec,
        dataClass: data.data_class,
        value: formatValue(data.value, spec.formatter ?? "brl"),
        reference: monthLabel(data.reference_date),
        source: data.provenance.source,
      };
    }),
  );

  root.innerHTML = results.map((result) => metricCardHtml(prefix, result)).join("");
  root.setAttribute("aria-busy", "false");
}

async function renderDebtCard(): Promise<void> {
  const card = document.querySelector<HTMLElement>("#card");
  if (!card) return;

  const { data, error } = await client.GET("/v1/metrics/{metric_id}", {
    params: { path: { metric_id: "divida_consolidada" }, query: { state_ibge_code: "35" } },
  });

  if (error || !data) {
    card.innerHTML = `<p class="error" role="alert">Indisponível no momento.</p>`;
    card.setAttribute("aria-busy", "false");
    return;
  }

  card.innerHTML = `
    <span class="data-class data-class--${data.data_class}">${data.data_class}</span>
    <p class="state">São Paulo</p>
    <p class="value" data-testid="value">${brl.format(data.value)}</p>
    <p class="ref">refer&ecirc;ncia: ${data.reference_year}</p>
    <a class="source" data-testid="source" href="${data.provenance.source}"
       target="_blank" rel="noopener noreferrer">fonte oficial</a>
  `;
  card.setAttribute("aria-busy", "false");
}

export async function renderMetricsPanel(): Promise<void> {
  await Promise.all([
    renderDebtCard(),
    renderNationalGroup("inss-module", "inss", [
      { id: "inss_beneficios_emitidos", label: "Benefícios emitidos" },
      { id: "inss_beneficios_mantidos", label: "Benefícios mantidos" },
      { id: "inss_beneficios_indeferidos", label: "Benefícios indeferidos", formatter: "count" },
    ]),
    renderNationalGroup("fiscal-module", "fiscal", [
      { id: "fiscal_receita", label: "Receita líquida" },
      { id: "fiscal_despesa", label: "Despesa total" },
      { id: "fiscal_primario", label: "Resultado primário" },
    ]),
  ]);
}
