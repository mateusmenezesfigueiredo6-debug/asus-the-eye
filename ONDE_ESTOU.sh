#!/usr/bin/env bash
# O BOTÃO — responde "onde eu estou?" em uma tela, sem depender de memória
# (nem sua, nem de IA). Só leitura: não altera, não publica, não gasta nada.
set -uo pipefail

REPO="/home/sexexes/asus_the_eye"
LEDGER="${THE_EYE_LEDGER_URL:-https://the-eye-audit-staging.mateusmenezesfigueiredo6.workers.dev}"
PY="$REPO/.venv/bin/python"
cd "$REPO" || { echo "Repositório não encontrado: $REPO"; exit 1; }

b() { printf '\n\033[1;36m%s\033[0m\n' "$1"; }
ok() { printf '  \033[0;32m✓\033[0m %s\n' "$1"; }
no() { printf '  \033[0;31m✗\033[0m %s\n' "$1"; }
info() { printf '    %s\n' "$1"; }

echo "======================================================================"
echo " THE EYE — ONDE ESTOU?   $(date '+%d/%m/%Y %H:%M')"
echo "======================================================================"

b "CÓDIGO"
info "branch:  $(git rev-parse --abbrev-ref HEAD)"
info "commit:  $(git log -1 --format='%h  %s' | cut -c1-60)"
info "quando:  $(git log -1 --format='%ad' --date=relative)"
DIRTY=$(git status --porcelain | grep -vc '^??' || true)
[ "$DIRTY" -eq 0 ] && ok "árvore limpa (nada por commitar)" || no "$DIRTY arquivo(s) modificado(s) sem commit"
UNPUSHED=$(git log origin/main..HEAD --oneline 2>/dev/null | wc -l)
[ "$UNPUSHED" -eq 0 ] && ok "sincronizado com o GitHub privado" || no "$UNPUSHED commit(s) sem enviar (git push)"

b "PRIVACIDADE"
VIS=$(gh repo view --json visibility --jq .visibility 2>/dev/null || echo "?")
[ "$VIS" = "PRIVATE" ] && ok "repositório PRIVADO" || no "visibilidade: $VIS  ← ATENÇÃO"
CODE=$(curl -s -o /dev/null -w '%{http_code}' -m 15 "$LEDGER/health" 2>/dev/null || echo 0)
[ "$CODE" = "401" ] && ok "ledger fechado a estranhos (401 sem token)" || no "ledger respondeu $CODE sem token ← ATENÇÃO"

b "TRAVA DE PUBLICAÇÃO"
if [ -f "$HOME/.the-eye/publish-lock.json" ]; then
  "$PY" scripts/publish_lock.py status 2>/dev/null | sed 's/^/  /'
else
  no "SENHA NÃO DEFINIDA — tudo que expõe está bloqueado (fail-closed)"
  info "defina com:  python3 scripts/publish_lock.py set"
fi

b "CADEIA DE EVIDÊNCIA"
if [ -f "$HOME/.the-eye/staging-token" ]; then
  RESP=$(curl -s -m 20 -H "authorization: Bearer $(cat "$HOME/.the-eye/staging-token")" \
    -H 'user-agent: onde-estou/1.0' "$LEDGER/events?tenant=tenant-demo" 2>/dev/null || echo '')
  if [ -n "$RESP" ]; then
    printf '%s' "$RESP" | "$PY" scripts/chain_summary.py || no "não consegui ler a cadeia"
  else
    no "ledger inacessível"
  fi
else
  no "token local ausente (~/.the-eye/staging-token)"
fi

b "PENDÊNCIAS (de RETOMADA.md)"
grep -E '^\- \[ \]' RETOMADA.md 2>/dev/null | sed 's/^- \[ \]/  ○/' | head -8

b "PRÓXIMO PASSO"
if [ ! -f "$HOME/.the-eye/publish-lock.json" ]; then
  echo "  → definir a senha:  python3 scripts/publish_lock.py set"
elif [ "$DIRTY" -ne 0 ]; then
  echo "  → commitar o que está em aberto"
elif [ "$UNPUSHED" -ne 0 ]; then
  echo "  → git push origin main"
else
  echo "  → tudo em dia. Escolha uma pendência acima."
fi

echo ""
echo "  Detalhes completos:  cat RETOMADA.md"
echo "  Checagem profunda:   .venv/bin/python scripts/leak_check.py"
echo "======================================================================"
