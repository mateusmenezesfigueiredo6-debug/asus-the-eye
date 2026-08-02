#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

PROJECT="${1:?project path required}"
RUN_ID="${2:?run id required}"
MAX_CYCLES="${MAX_CYCLES:-4}"
CYCLE_TIMEOUT="${CYCLE_TIMEOUT:-2h}"

cd "$PROJECT"
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
unset CLOUDFLARE_API_TOKEN OPENAI_API_KEY PRIVATE_KEY

ROOT="$PROJECT/reports/autonomous"
RUN_DIR="$ROOT/$RUN_ID"
MASTER="$PROJECT/prompts/THE_EYE_MASTER_MISSION.md"
SCHEMA="$PROJECT/prompts/autonomous-final.schema.json"
mkdir -p "$RUN_DIR"
ln -sfn "$RUN_ID" "$ROOT/latest"

printf '# Autonomous run %s\n\n' "$RUN_ID" > "$RUN_DIR/RUN_SUMMARY.md"
printf 'Project: `%s`\n\n' "$PROJECT" >> "$RUN_DIR/RUN_SUMMARY.md"
printf 'Max cycles: `%s`\n\n' "$MAX_CYCLES" >> "$RUN_DIR/RUN_SUMMARY.md"
printf 'Cycle timeout: `%s`\n\n' "$CYCLE_TIMEOUT" >> "$RUN_DIR/RUN_SUMMARY.md"

status="partial"
for cycle in $(seq 1 "$MAX_CYCLES"); do
  CYCLE_DIR="$RUN_DIR/cycle-$cycle"
  mkdir -p "$CYCLE_DIR"
  PROMPT_FILE="$CYCLE_DIR/prompt.md"

  if [ "$cycle" -eq 1 ]; then
    cp "$MASTER" "$PROMPT_FILE"
  else
    cat > "$PROMPT_FILE" <<EOF
Read AGENTS.md and prompts/THE_EYE_MASTER_MISSION.md in full.
This is autonomous continuation cycle $cycle of $MAX_CYCLES.

Read all existing files in research/, reports/AUTONOMOUS_RESEARCH_REPORT.md,
reports/autonomous/$RUN_ID, and the current repository diff. Continue from the
last verified state. Do not restart completed work. Resolve the highest-impact
open questions and blockers that can be addressed safely inside the workspace.

Revalidate important current facts with primary sources, seek contrary evidence,
implement safe local improvements, execute tests, update the evidence matrix and
final report, and return the required JSON object.

All restrictions in AGENTS.md and the master mission remain mandatory.
EOF
  fi

  set +e
  if command -v timeout >/dev/null 2>&1; then
    timeout --signal=INT --kill-after=60s "$CYCLE_TIMEOUT" \
      codex exec \
      --profile research \
      --search \
      --sandbox workspace-write \
      --ask-for-approval never \
      --json \
      --output-schema "$SCHEMA" \
      --output-last-message "$CYCLE_DIR/final.json" \
      - \
      < "$PROMPT_FILE" \
      > "$CYCLE_DIR/events.jsonl" \
      2> "$CYCLE_DIR/errors.log"
    exit_code=$?
  else
    codex exec \
      --profile research \
      --search \
      --sandbox workspace-write \
      --ask-for-approval never \
      --json \
      --output-schema "$SCHEMA" \
      --output-last-message "$CYCLE_DIR/final.json" \
      - \
      < "$PROMPT_FILE" \
      > "$CYCLE_DIR/events.jsonl" \
      2> "$CYCLE_DIR/errors.log"
    exit_code=$?
  fi
  set -e

  status="$(python3 - "$CYCLE_DIR/final.json" <<'PY'
from pathlib import Path
import json, sys
p = Path(sys.argv[1])
try:
    value = json.loads(p.read_text(encoding='utf-8'))
    print(value.get('status', 'partial'))
except Exception:
    print('partial')
PY
)"

  printf '## Cycle %s\n\n' "$cycle" >> "$RUN_DIR/RUN_SUMMARY.md"
  printf -- '- Exit code: `%s`\n' "$exit_code" >> "$RUN_DIR/RUN_SUMMARY.md"
  printf -- '- Status: `%s`\n' "$status" >> "$RUN_DIR/RUN_SUMMARY.md"
  printf -- '- Final: `%s`\n' "$CYCLE_DIR/final.json" >> "$RUN_DIR/RUN_SUMMARY.md"
  printf -- '- Events: `%s`\n' "$CYCLE_DIR/events.jsonl" >> "$RUN_DIR/RUN_SUMMARY.md"
  printf -- '- Errors: `%s`\n\n' "$CYCLE_DIR/errors.log" >> "$RUN_DIR/RUN_SUMMARY.md"

  cp "$CYCLE_DIR/final.json" "$RUN_DIR/final.json" 2>/dev/null || true

  if [ "$status" = "complete" ]; then
    break
  fi

done

{
  printf '\n## Final state\n\n'
  printf -- '- Status: `%s`\n' "$status"
  printf -- '- Finished at: `%s`\n' "$(date -Iseconds)"
} >> "$RUN_DIR/RUN_SUMMARY.md"

git status --porcelain=v1 > "$RUN_DIR/git-status-after.txt" 2>&1 || true
git diff > "$RUN_DIR/git-diff-after.patch" 2>&1 || true

printf '%s\n' "$status" > "$RUN_DIR/status"
