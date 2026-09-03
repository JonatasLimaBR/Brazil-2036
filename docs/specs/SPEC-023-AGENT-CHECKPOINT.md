# SPEC-023 — Agent Checkpoint
Before approval-required action, persist state needed to resume deterministically.
Resume token references immutable checkpoint version.
Reject terminates the action path; changing parameters requires a new approval request.
