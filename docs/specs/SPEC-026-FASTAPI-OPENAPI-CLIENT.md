# SPEC-026 — API Contract
FastAPI/Pydantic define backend contracts.
OpenAPI schema is generated in CI.
TypeScript client package is generated from OpenAPI; frontend must not hand-copy DTOs.
Breaking API changes require versioning/migration note.
