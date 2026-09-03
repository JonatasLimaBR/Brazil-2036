#!/bin/bash
# SYNC-CONTEXT REMINDER HOOK — Stop
#
# Detecta drift entre o CLAUDE.md do projeto e os artefatos SDD: se um
# SHIPPED_*.md ou BUILD_REPORT_*.md é mais novo que o CLAUDE.md, o projeto
# mudou sem atualizar o contexto — bloqueia UMA vez pedindo /sync-context.
#
# Origem: drift real em 3 projetos (KAFKADATABRICKS dizia "não é projeto de
# software" tendo pipeline completo; OpportunityAI teve 3 dias de drift;
# InsuranceLakehousePlatform idem — ver SHIPPED reports 2026-06/07).
#
# Anti-nag: lembra no máximo 1x por artefato novo (estado por hash do cwd).
# Fail-open: qualquer erro → "{}" e sai 0.

STATE_DIR="$HOME/.mempalace/hook_state"
mkdir -p "$STATE_DIR" 2>/dev/null || { echo "{}"; exit 0; }

INPUT=$(cat)

# Respeita o ciclo de bloqueio (mesmo protocolo do mempalace_save.sh)
STOP_ACTIVE=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print('true' if d.get('stop_hook_active') else 'false')
except Exception:
    print('true')
" 2>/dev/null)
[ "$STOP_ACTIVE" = "true" ] && { echo "{}"; exit 0; }

PROJ="$PWD"
CLAUDE_MD="$PROJ/CLAUDE.md"
SDD_DIR="$PROJ/.claude/sdd"

# Sem CLAUDE.md ou sem SDD → nada a comparar
{ [ -f "$CLAUDE_MD" ] && [ -d "$SDD_DIR" ]; } || { echo "{}"; exit 0; }

# Artefato SDD de entrega mais recente (POSIX: -printf é GNU-only e quebraria
# no macOS — usar find -newer + ls -t para ordenar)
CANDIDATES=$(find "$SDD_DIR" \( -name "SHIPPED_*.md" -o -name "BUILD_REPORT_*.md" \) \
    -newer "$CLAUDE_MD" 2>/dev/null | head -50)
# Guarda de vazio ANTES do xargs: sem ela, `xargs -0 ls -t` sem argumentos
# listaria o cwd e produziria um falso positivo de drift.
[ -z "$CANDIDATES" ] && { echo "{}"; exit 0; }
NEWEST_FILE=$(printf '%s\n' "$CANDIDATES" | tr '\n' '\0' | xargs -0 ls -t 2>/dev/null | head -1)
[ -z "$NEWEST_FILE" ] && { echo "{}"; exit 0; }

# Anti-nag: já lembramos sobre este artefato? (cksum é POSIX; md5sum é GNU-only)
PROJ_HASH=$(printf '%s' "$PROJ" | cksum | tr ' ' '_')
MARK_FILE="$STATE_DIR/syncctx_${PROJ_HASH}"
LAST_MARK=$(cat "$MARK_FILE" 2>/dev/null)
[ "$LAST_MARK" = "$NEWEST_FILE" ] && { echo "{}"; exit 0; }

echo "$NEWEST_FILE" > "$MARK_FILE"

# A reason mostra só o caminho relativo saneado (nome de arquivo vem do repo —
# não ecoar bytes arbitrários para dentro da mensagem de sistema)
python3 - "$NEWEST_FILE" "$PROJ" <<'PYEOF'
import json, re, sys
artifact, proj = sys.argv[1], sys.argv[2]
rel = artifact[len(proj):].lstrip("/") if artifact.startswith(proj) else artifact
rel = re.sub(r"[^a-zA-Z0-9_./\- ]", "", rel)[:120]
print(json.dumps({
    "decision": "block",
    "reason": (
        "CLAUDE.md drift detectado: o artefato SDD mais recente "
        f"({rel}) é mais novo que o CLAUDE.md do projeto. "
        "O projeto mudou sem atualizar o contexto — rode /sync-context "
        "(ou atualize o CLAUDE.md manualmente) antes de encerrar. "
        "Este lembrete dispara apenas uma vez por artefato."
    ),
}))
PYEOF
exit 0
