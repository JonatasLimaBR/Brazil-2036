# web — public Landing card (ADR-051, SPEC-033)

Vite + TypeScript (no framework). One card: the latest *Dívida Consolidada* for
São Paulo, fetched at runtime from the API — no number is hardcoded in the bundle
(ADR-012). The typed client is generated from the API's OpenAPI (ADR-024/SPEC-026).

## Develop

```bash
npm ci
npm run gen:client     # regenerate src/api-client/schema.d.ts from ../api/openapi/openapi.json
npm run typecheck
npm run build
VITE_API_URL=http://localhost:8080 npm run preview   # serves dist/ on :4173
PLAYWRIGHT_BASE_URL=http://localhost:4173 npm run e2e
```

`src/api-client/schema.d.ts` is committed and checked for drift in CI. The image
build (`Dockerfile`) uses the committed file and bakes `VITE_API_URL` (the API's
Cloud Run URL) at build time.
