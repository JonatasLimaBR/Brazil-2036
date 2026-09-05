import createClient from "openapi-fetch";
import type { paths } from "./api-client/schema";

const API_URL = import.meta.env.VITE_API_URL ?? "";

const METRICS: Array<{ id: string; label: string }> = [
  { id: "fiscal_receita", label: "Receita líquida" },
  { id: "fiscal_despesa", label: "Despesa total" },
  { id: "fiscal_primario", label: "Resultado primário" },
];

const client = createClient<paths>({ baseUrl: API_URL });

const brl = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
});

function formatValue(value: number): string {
  // fiscal_primario is legitimately negative (a primary deficit) -- append a
  // plain-language qualifier instead of leaving a bare negative currency
  // figure, which a reader could otherwise mistake for a data error.
  return value < 0 ? `${brl.format(value)} (déficit)` : brl.format(value);
}

function monthLabel(isoDate: string): string {
  const [year, month] = isoDate.split("-");
  return `${month}/${year}`;
}

export async function renderFiscalModule(): Promise<void> {
  const root = document.querySelector<HTMLElement>("#fiscal-module");
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
          <article class="fiscal-number" data-testid="fiscal-${metric.id}">
            <p class="fiscal-label">${metric.label}</p>
            <p class="error" role="alert">Indisponível no momento.</p>
          </article>
        `;
      }
      return `
        <article class="fiscal-number" data-testid="fiscal-${metric.id}">
          <span class="data-class data-class--${data.data_class}">${data.data_class}</span>
          <p class="fiscal-label">${metric.label}</p>
          <p class="value" data-testid="fiscal-${metric.id}-value">${formatValue(data.value)}</p>
          <p class="ref">referência: ${monthLabel(data.reference_date)}</p>
          <a class="source" data-testid="fiscal-${metric.id}-source" href="${data.provenance.source}"
             target="_blank" rel="noopener noreferrer">fonte oficial</a>
        </article>
      `;
    })
    .join("");
  root.setAttribute("aria-busy", "false");
}
