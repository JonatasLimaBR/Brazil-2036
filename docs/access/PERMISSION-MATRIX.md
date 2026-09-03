# Permission Matrix (baseline)
| Role | VIEW | EXPORT | FORECAST | SIMULATE | DRAFT | PUBLISH | MANAGE_AGENT | MANAGE_MODEL | ADMIN_USERS | SECURITY |
|---|---|---|---|---|---|---|---|---|---|---|
| Public | Y | public | N | public-only | N | N | N | N | N | N |
| Analyst | Y | scoped | N | N | N | N | N | N | N | N |
| Economist | Y | scoped | Y | scoped | Y | N | N | N | N | N |
| Simulator | Y | scoped | Y | Y | Y | N | N | N | N | N |
| Agent Manager | Y | scoped | Y | Y | Y | N | Y | N | N | N |
| ML Engineer | Y | scoped | Y | Y | Y | N | N | scoped | N | N |
| Org Admin | Y | scoped | scoped | scoped | Y | policy | N | N | Y-own-org | N |
| Platform Admin | Y | Y | Y | Y | Y | approval | Y | approval | Y | limited |
| Security Admin | Y | audit | N | N | N | N | N | N | policy | Y |
