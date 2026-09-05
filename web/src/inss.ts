import createClient from "openapi-fetch";
import type { paths } from "./api-client/schema";

const API_URL = import.meta.env.VITE_API_URL ?? "";

const METRICS: Array<{ id: string; label: string; formatter: "brl" | "count" }> = [
  { id: "inss_beneficios_emitidos", label: "Benefícios emitidos", formatter: "brl" },
  { id: "inss_beneficios_mantidos", label: "Benefícios mantidos", formatter: "brl" },
  { id: "inss_beneficios_indeferidos", label: "Benefícios indeferidos", formatter: "count" },
];

const client = createClient<paths>({ baseUrl: API_URL });

const brl = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
});
const count = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });

function formatValue(value: number, formatter: "brl" | "count"): string {
  return formatter === "brl" ? brl.format(value) : count.format(value);
}

function monthLabel(isoDate: string): string {
  const [year, month] = isoDate.split("-");
  return `${month}/${year}`;
}

export async function renderInssModule(): Promise<void> {
  const root = document.querySelector<HTMLElement>("#inss-module");
  if (!root) return;

  const results = await Promise.all(
    METRICS.map(async (metric) => {
      const { data, error } = await client.GET("/v1/metrics/{metric_id}/national", {
        params: { path: { metric_id: metric.id } },
      });
      return { metric, data, error };
    }),
  );

  root.innerHTML = results
    .map(({ metric, data, error }) => {
      if (error || !data) {
        return `
          <article class="inss-number" data-testid="inss-${metric.id}">
            <p class="inss-label">${metric.label}</p>
            <p class="error" role="alert">Indisponível no momento.</p>
          </article>
        `;
      }
      return `
        <article class="inss-number" data-testid="inss-${metric.id}">
          <span class="data-class data-class--${data.data_class}">${data.data_class}</span>
          <p class="inss-label">${metric.label}</p>
          <p class="value" data-testid="inss-${metric.id}-value">${formatValue(
            data.value,
            metric.formatter,
          )}</p>
          <p class="ref">referência: ${monthLabel(data.reference_date)}</p>
          <a class="source" data-testid="inss-${metric.id}-source" href="${data.provenance.source}"
             target="_blank" rel="noopener noreferrer">fonte oficial</a>
        </article>
      `;
    })
    .join("");
  root.setAttribute("aria-busy", "false");
}
