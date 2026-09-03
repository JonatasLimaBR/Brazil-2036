#!/bin/bash
# LESSON RECALL HOOK — SessionStart
#
# Fecha o loop do sistema LESSON_LEARNED (data-agents v2.1.0 §lesson injection):
# injeta as lições mais recentes/frequentes capturadas por lesson_capture.sh
# como contexto adicional no início da sessão — funciona SEM mempalace
# instalado (lê direto os JSONL de buffer/ e archive/).
#
# Seleção: lições dos últimos RECALL_DAYS dias (decay de 30d como no
# data-agents), deduplicadas por (tool, contexto), no máximo RECALL_MAX.
# Fail-open: qualquer erro → "{}" e exit 0.

LESSONS_ROOT="$HOME/.mempalace/lessons"
RECALL_DAYS="${LESSON_RECALL_DAYS:-30}"
RECALL_MAX="${LESSON_RECALL_MAX:-5}"

[ -d "$LESSONS_ROOT" ] || { echo "{}"; exit 0; }

python3 - "$LESSONS_ROOT" "$RECALL_DAYS" "$RECALL_MAX" <<'PYEOF' 2>/dev/null || echo "{}"
import glob, json, os, sys, time

root, days, max_n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
cutoff = time.time() - days * 86400

lessons = []
for path in glob.glob(os.path.join(root, "buffer", "*.jsonl")) + \
            glob.glob(os.path.join(root, "archive", "*.jsonl")):
    try:
        if os.path.getmtime(path) < cutoff:
            continue
        with open(path) as f:
            for line in f:
                try:
                    lessons.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass

if not lessons:
    print("{}")
    sys.exit(0)

# Dedup por (tool, contexto truncado); mantém a mais recente e conta recorrência
seen = {}
for l in lessons:
    key = (l.get("tool", ""), str(l.get("context", ""))[:80])
    prev = seen.get(key)
    if prev is None or l.get("ts", "") > prev.get("ts", ""):
        count = (prev.get("_count", 0) if prev else 0) + 1
        l["_count"] = count
        seen[key] = l
    else:
        prev["_count"] = prev.get("_count", 0) + 1

# Recorrentes primeiro, depois mais recentes
top = sorted(seen.values(), key=lambda l: (-l.get("_count", 1), l.get("ts", "")), reverse=False)
top = sorted(top, key=lambda l: (-l.get("_count", 1), ""))[:max_n]

lines = ["### Lições Aprendidas ⚠️ (capturadas automaticamente em sessões anteriores)"]
for l in top:
    rec = f" ({l['_count']}x)" if l.get("_count", 1) > 1 else ""
    trig = ",".join(l.get("triggers", []))
    ctx = str(l.get("context", ""))[:100]
    ev = str(l.get("evidence", ""))[:140]
    lines.append(f"- [{trig}]{rec} `{l.get('tool','')}`: {ctx} → {ev}")
lines.append("Evite repetir estes erros; se um deles for relevante à tarefa atual, mencione a mitigação.")

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": "\n".join(lines),
    }
}))
PYEOF
exit 0
