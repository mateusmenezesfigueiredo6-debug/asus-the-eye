#!/usr/bin/env bash
# Embrulha os fragments (formato artifact: começam em <title>) como documentos
# HTML completos para servir cru pelo worker. Idempotente: detecta o doctype.
set -euo pipefail
cd "$(dirname "$0")/frontends"

wrap() {
  local f="$1" desc="$2"
  if head -1 "$f" | grep -q '<!doctype'; then
    echo "$f já embrulhado, pulando"
    return
  fi
  local tmp
  tmp=$(mktemp)
  {
    printf '<!doctype html>\n<html lang="pt-BR">\n<head>\n'
    printf '<meta charset="utf-8">\n'
    printf '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
    printf '<meta name="description" content="%s">\n' "$desc"
    cat "$f"
    printf '\n</html>\n'
  } > "$tmp"
  mv "$tmp" "$f"
  echo "$f embrulhado"
}

wrap ledger.html "Ledger: a trilha que qualquer pessoa confere sem pedir licença. Selado por hash, encadeado, ancorado em rede pública. Produto para instituições; demonstração sob agendamento."
wrap markets.html "Markets: perguntas com prazo e critério, respondidas pela fonte oficial. Probabilidade antes do fato; Brier só depois da liquidação. Sem dinheiro real."
