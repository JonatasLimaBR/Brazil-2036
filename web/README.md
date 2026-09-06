# web — public Landing (ADR-058, supersedes ADR-051)

Astro (`output: "static"`, no SSR). Static sections (proposal, module/portal/architecture
grids, roadmap, benefits, footer) ship as plain HTML; only the data panel (debt, INSS, fiscal —
`src/components/DataPanel.astro`) hydrates client-side to fetch real numbers at runtime — no
number is hardcoded in the bundle (ADR-012). The typed client is generated from the API's
OpenAPI (ADR-024/SPEC-026).

Status badges on the module grid, architecture diagram and roadmap (`src/data/status.ts`) are
never invented — each entry carries an `evidence` field pointing to the real SHIPPED
feature/ADR/Terraform file behind it.

## Develop

```bash
npm ci
npm run gen:client     # regenerate src/api-client/schema.d.ts from ../api/openapi/openapi.json
npm run typecheck      # astro check
npm run build          # astro build -> dist/
VITE_API_URL=http://localhost:8080 npm run preview   # serves dist/ on :4173
PLAYWRIGHT_BASE_URL=http://localhost:4173 npm run e2e
```

`src/api-client/schema.d.ts` is committed and checked for drift in CI. The image build
(`Dockerfile`) uses the committed file and bakes `VITE_API_URL` (the API's Cloud Run URL) at
build time -- `astro.config.mjs` sets `vite.envPrefix: ["VITE_"]` so Astro (which only exposes
`PUBLIC_`-prefixed vars to the client by default) still picks it up under its existing name.
