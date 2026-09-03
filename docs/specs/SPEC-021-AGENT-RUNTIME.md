# SPEC-021 — Agent Runtime
Every run has agent_run_id, trace_id, user/org context, agent/model/prompt versions.
Tool calls are structured and auditable.
Numeric official answers use tools; prompt memory is not authoritative.
Streaming events support started/tool_started/tool_completed/approval_required/answer_delta/completed.
