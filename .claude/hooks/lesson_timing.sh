#!/bin/bash
# LESSON TIMING HOOK — PreToolUse
#
# Ported from data-agents v2.1.0 `pre_track_lesson_timing()` (hooks/memory_hook.py).
# Records t0 of each tool call so lesson_capture.sh (PostToolUse) can detect
# slow operations (slow_op trigger). Stateless across sessions: one small file
# per tool_use_id under ~/.mempalace/lessons/timing/, pruned aggressively.
#
# Fail-open by design: any error exits 0 with "{}" so tool calls never block.

STATE_DIR="$HOME/.mempalace/lessons/timing"
mkdir -p "$STATE_DIR" 2>/dev/null || { echo "{}"; exit 0; }

INPUT=$(cat)

TOOL_USE_ID=$(echo "$INPUT" | python3 -c "
import sys, json, re
try:
    d = json.load(sys.stdin)
    tid = str(d.get('tool_use_id') or d.get('toolUseId') or '')
    print(re.sub(r'[^a-zA-Z0-9_.\-]', '', tid))
except Exception:
    pass
" 2>/dev/null)

if [ -n "$TOOL_USE_ID" ]; then
    date +%s > "$STATE_DIR/$TOOL_USE_ID" 2>/dev/null
fi

# Prune timing files older than 1 hour (orphans from crashed sessions)
find "$STATE_DIR" -type f -mmin +60 -delete 2>/dev/null

echo "{}"
exit 0
