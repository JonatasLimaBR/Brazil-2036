#!/bin/bash
# LESSON CAPTURE HOOK — PostToolUse
#
# Ported from data-agents v2.1.0 autonomous learning system (hooks/memory_hook.py):
# captures LESSON_LEARNED entries when a tool call hits one of the triggers:
#
#   error   — tool output/error contains error indicators
#   slow_op — tool call took longer than SLOW_OP_THRESHOLD seconds
#             (t0 recorded by lesson_timing.sh in PreToolUse)
#
# Layout under ~/.mempalace/lessons/ (buffer/ is the ONLY dir mined by
# mempalace_save.sh — timing/ and archive/ stay out of the miner's path):
#   buffer/{session_id}.jsonl   — lessons awaiting the next save checkpoint
#   timing/{tool_use_id}        — t0 markers from lesson_timing.sh
#   archive/                    — mined buffers (kept for audit)
#
# The hook JSON is passed to Python via TEMP FILE, not env var: tool outputs
# above ~128KB would hit E2BIG on the env and silently drop the lesson.
# Evidence/context are redacted for common secret patterns before writing.
# Anti-bloat: max MAX_LESSONS per session (data-agents caps at 50 per agent).
#
# Fail-open by design: any error exits 0 with "{}" — never blocks a tool call.

LESSONS_ROOT="$HOME/.mempalace/lessons"
BUFFER_DIR="$LESSONS_ROOT/buffer"
TIMING_DIR="$LESSONS_ROOT/timing"
SLOW_OP_THRESHOLD="${LESSON_SLOW_OP_THRESHOLD:-90}"   # seconds
MAX_LESSONS="${LESSON_MAX_PER_SESSION:-50}"

mkdir -p "$BUFFER_DIR" "$TIMING_DIR" 2>/dev/null || { echo "{}"; exit 0; }

INPUT_FILE=$(mktemp "${TMPDIR:-/tmp}/lesson_input.XXXXXX" 2>/dev/null) || { echo "{}"; exit 0; }
trap 'rm -f "$INPUT_FILE"' EXIT
cat > "$INPUT_FILE"

python3 - "$INPUT_FILE" "$BUFFER_DIR" "$TIMING_DIR" "$SLOW_OP_THRESHOLD" "$MAX_LESSONS" <<'PYEOF' >/dev/null 2>&1
import json, os, re, sys, time

input_file, buffer_dir, timing_dir = sys.argv[1], sys.argv[2], sys.argv[3]
slow_threshold, max_lessons = int(sys.argv[4]), int(sys.argv[5])

try:
    with open(input_file) as f:
        data = json.load(f)
except Exception:
    sys.exit(0)

def safe(s, extra=""):
    return re.sub(r"[^a-zA-Z0-9_.\-" + extra + r"]", "", str(s or ""))

# Redação de segredos: padrões comuns em outputs de erro (connection strings,
# bearer tokens, chaves de API, blocos PEM). A lição interessa pelo padrão do
# erro, nunca pelo credencial que vazou junto.
_SECRET_PATTERNS = [
    (re.compile(r"(?i)(api[_-]?key|secret|password|passwd|token|authorization|bearer)"
                r"(\s*[:=]\s*|\s+)([\"']?)[^\s\"'&;]{8,}"), r"\1\2\3[REDACTED]"),
    (re.compile(r"(?i)(postgres|mysql|mongodb(\+srv)?|redis|amqp)://[^\s\"']+"), r"\1://[REDACTED]"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"), "[REDACTED-PEM]"),
    (re.compile(r"\b(AKIA|ASIA)[A-Z0-9]{16}\b"), "[REDACTED-AWS-KEY]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "[REDACTED-GH-TOKEN]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"), "[REDACTED-JWT]"),
]

def redact(text):
    for pattern, repl in _SECRET_PATTERNS:
        text = pattern.sub(repl, text)
    return text

session_id = safe(data.get("session_id", "unknown")) or "unknown"
tool_name = safe(data.get("tool_name", ""), extra="_")
tool_use_id = safe(data.get("tool_use_id") or data.get("toolUseId") or "")
tool_input = data.get("tool_input") or {}
response = data.get("tool_response") or data.get("tool_result") or {}

# Flatten response to searchable text (mirrors data-agents: tool_error + tool_output)
if isinstance(response, (dict, list)):
    resp_text = json.dumps(response, ensure_ascii=False)[:4000]
else:
    resp_text = str(response)[:4000]

ERROR_INDICATORS = ["error", "failed", "exception", "traceback", "unauthorized", "timeout"]
is_error = bool(data.get("is_error")) or any(
    kw in resp_text.lower() for kw in ERROR_INDICATORS
)

# slow_op: compare with t0 written by lesson_timing.sh
duration = None
if tool_use_id:
    t0_file = os.path.join(timing_dir, tool_use_id)
    try:
        with open(t0_file) as f:
            duration = int(time.time()) - int(f.read().strip())
        os.remove(t0_file)
    except Exception:
        pass
is_slow = duration is not None and duration >= slow_threshold

triggers = []
if is_error:
    triggers.append("error")
if is_slow:
    triggers.append("slow_op")
if not triggers:
    sys.exit(0)

# Command/description context (truncated — this is a hint, not a transcript)
if isinstance(tool_input, dict):
    ctx = tool_input.get("command") or tool_input.get("description") or tool_input.get("file_path") or ""
else:
    ctx = str(tool_input)
ctx = str(ctx)[:300]

lesson = {
    "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "session": session_id,
    "tool": tool_name,
    "triggers": triggers,
    "duration_s": duration,
    "context": redact(ctx),
    "evidence": redact(resp_text[:500]),
}

out_path = os.path.join(buffer_dir, f"{session_id}.jsonl")

# Anti-bloat: cap lessons per session (data-agents: prune_lessons_by_agent → 50)
count = 0
if os.path.exists(out_path):
    with open(out_path) as f:
        count = sum(1 for _ in f)
if count >= max_lessons:
    sys.exit(0)

with open(out_path, "a") as f:
    f.write(json.dumps(lesson, ensure_ascii=False) + "\n")
PYEOF

echo "{}"
exit 0
