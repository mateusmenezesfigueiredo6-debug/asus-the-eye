#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
# Empacota o projeto inteiro num zip único para disco externo.
#
# O que NÃO entra, e por quê: o pacote contém o *projeto*, não as *chaves*.
# Quem o tiver não consegue escrever no ledger nem publicar em nome do dono.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M)"
STAGE="$(mktemp -d)/ASUS_THE_EYE_PACOTE"
ZIP="${1:-$HOME/ASUS_THE_EYE_COMPLETO_${STAMP}.zip}"

mkdir -p "$STAGE/asus_the_eye"
cd "$REPO"
tar -c --exclude='.venv' --exclude='node_modules' --exclude='__pycache__' \
    --exclude='.pytest_cache' --exclude='.ruff_cache' --exclude='htmlcov' \
    --exclude='*.pyc' --exclude='*.egg-info' . | tar -x -C "$STAGE/asus_the_eye"

cp -f docs/PACOTE.md "$STAGE/" 2>/dev/null || true
cd "$STAGE"
find asus_the_eye -type f -not -path 'asus_the_eye/.git/*' | sort \
  | xargs sha256sum > PACOTE_MANIFEST.txt

# Verificação anti-segredo: falha em vez de empacotar um token.
for secret in "$HOME/.the-eye/staging-token" "$HOME/.the-eye/publish-lock.json"; do
  [ -f "$secret" ] || continue
  if grep -rIqF -- "$(cat "$secret")" "$STAGE/asus_the_eye" 2>/dev/null; then
    echo "ABORTADO: conteúdo de $secret encontrado no pacote" >&2
    exit 1
  fi
done
if find "$STAGE/asus_the_eye" \( -name '.env' -o -name '*.key' -o -name '*.pem' \
     -o -name 'staging-token' -o -name 'publish-lock.json' \) \
     -not -name '*.example' | grep -q .; then
  echo "ABORTADO: arquivo de credencial no pacote" >&2
  exit 1
fi

rm -f "$ZIP"
zip -rq "$ZIP" asus_the_eye PACOTE_MANIFEST.txt $([ -f PACOTE.md ] && echo PACOTE.md)
rm -rf "$(dirname "$STAGE")"

echo "ZIP:      $ZIP"
echo "tamanho:  $(du -h "$ZIP" | cut -f1)"
echo "sha256:   $(sha256sum "$ZIP" | cut -d' ' -f1)"
echo
echo "Confira depois de copiar para o disco:"
echo "  sha256sum \"\$(basename "$ZIP")\""
