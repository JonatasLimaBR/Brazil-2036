import createClient from "openapi-fetch";
import type { paths } from "./api-client/schema";

const API_URL = import.meta.env.VITE_API_URL ?? "";
const METRIC_ID = "divida_consolidada";
const STATE = "35";

const client = createClient<paths>({ baseUrl: API_URL });

const brl = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
});

function render(html: string): void {
  const card = document.querySelector<HTMLElement>("#card");
  if (!card) return;
  card.innerHTML = html;
  card.setAttribute("aria-busy", "false");
}

async function load(): Promise<void> {
  const { data, error } = await client.GET("/v1/metrics/{metric_id}", {
    params: { path: { metric_id: METRIC_ID }, query: { state_ibge_code: STATE } },
  });

  if (error || !data) {
    render(`<p class="error" role="alert">Indisponível no momento.</p>`);
    return;
  }

  render(`
    <span class="data-class data-class--${data.data_class}">${data.data_class}</span>
    <p class="state">São Paulo</p>
    <p class="value" data-testid="value">${brl.format(data.value)}</p>
    <p class="ref">refer&ecirc;ncia: ${data.reference_year}</p>
    <a class="source" data-testid="source" href="${data.provenance.source}"
       target="_blank" rel="noopener noreferrer">fonte oficial</a>
  `);
}

void load();
