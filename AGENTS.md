# BRASIL 2036 — Product Agent Reference

This document is intentionally written in English because it is consumed by coding agents and reviewers.

## Core design rule
Agent permissions are capability-based. A forbidden capability must be absent from the registered toolset, not merely forbidden by prompt text.

## Agent classes

### READ
May query canonical metrics, documents, graph data, and provenance.
Must not receive write or publish tools.

### COMPUTE
May run forecasting, causal analysis, Monte Carlo, or simulation services.
Outputs are versioned and labeled ESTIMATED or SIMULATED.

### DRAFT
May create draft scenarios, draft reports, or review recommendations.
Draft tools must not implicitly publish.

### PUBLISH
May publish only after a persisted approval workflow authorizes the action.

### PRIVILEGED / SECURITY
IAM, RBAC, production model promotion, Gold changes, and security policies require explicit human approval; security-critical actions require four-eyes approval.

## Product agents
- Brasil2036 Orchestrator
- Macro Agent
- Fiscal Agent
- Debt Agent
- INSS Agent
- Labor Agent
- Municipal Agent
- Health Agent
- Education Agent
- Tax Agent
- Procurement Agent
- Infrastructure Agent
- Forecast Agent
- Causal Agent
- Policy Agent
- Open Data Discovery Agent

## Coding Reviewer
The Coding Reviewer is not a product agent.
It may read code, execute tests, inspect logs, and issue PASS/FAIL.
It must not edit, patch, commit, push, merge, or deploy.

## Safety examples
INSS analysis agents must not expose tools such as `cancel_benefit`, `deny_benefit`, `block_person`, or `modify_citizen_record`.
Fraud analysis agents may rank or recommend review; they must not punish, block, accuse, or deny payments.
