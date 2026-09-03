# SPEC-024 — PII Redaction Before Trace
Raw user text passes redaction before being sent to observability sinks.
Patterns/classes include CPF, personal email, phone, address-like identifiers, tokens and secrets.
Security tests inject synthetic PII and assert it never appears in stored trace.
