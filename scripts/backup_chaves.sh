#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
# Custódia cifrada das chaves do THE EYE — ato do dono.
#
# POR QUE ISSO EXISTE:
#   reports/audit/pseudonimos.key é a IDENTIDADE da corrente auditável. A
#   corrente pertence a UMA chave (fingerprint versionado em
#   reports/markets/chave.fingerprint). Perder essa chave = nunca mais poder
#   selar eventos naquela corrente. O histórico continua verificável, mas
#   vira somente-leitura para sempre. NÃO existe recuperação.
#
# O QUE FAZ:
#   Empacota as chaves + o fingerprint num .tar.gz e CIFRA com senha (AES-256).
#   A senha nunca é gravada em lugar nenhum — é digitada por você, na hora.
#
# USO:
#   ./scripts/backup_chaves.sh                 # gera o pacote cifrado
#   ./scripts/backup_chaves.sh --verificar ARQ # testa que o pacote abre
#
# DEPOIS DE GERAR: copie o .gpg para DOIS lugares fisicamente separados
#   (ex.: pendrive guardado + nuvem pessoal). Um só lugar não é backup.
set -euo pipefail
cd "$(dirname "$0")/.."

DESTINO="${THE_EYE_BACKUP_DIR:-$HOME/Área de trabalho/organizado/Backups/the-eye-chaves}"
CARIMBO="$(date -u +%Y-%m-%d)"
SAIDA="$DESTINO/the-eye-chaves-$CARIMBO.tar.gz.gpg"

cifrar() { gpg --symmetric --cipher-algo AES256 --output "$1" -; }
decifrar() { gpg --decrypt "$1"; }
if ! command -v gpg >/dev/null 2>&1; then
  cifrar() { openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -salt -out "$1"; }
  decifrar() { openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -in "$1"; }
  echo "aviso: gpg ausente — usando openssl (AES-256-CBC, PBKDF2 600k)"
fi

if [ "${1:-}" = "--verificar" ]; then
  ARQ="${2:?informe o arquivo .gpg}"
  echo "conferindo $ARQ (digite a senha do backup):"
  decifrar "$ARQ" | tar -tzf - && echo "OK: o pacote abre e lista os arquivos acima."
  exit 0
fi

ITENS=()
for f in reports/audit/pseudonimos.key reports/audit/anchor.key reports/markets/chave.fingerprint; do
  [ -f "$f" ] && ITENS+=("$f")
done
for f in "$HOME/.the-eye/staging-token" "$HOME/.the-eye/publish-lock.json"; do
  [ -f "$f" ] && ITENS+=("$f")
done
[ ${#ITENS[@]} -gt 0 ] || { echo "erro: nenhuma chave encontrada"; exit 1; }

mkdir -p "$DESTINO"
echo "vou cifrar ${#ITENS[@]} arquivos:"; printf '  %s\n' "${ITENS[@]}"
echo
echo "ESCOLHA UMA SENHA FORTE e GUARDE-A SEPARADAMENTE do arquivo."
echo "Sem a senha, este backup é inútil. Sem o backup, a corrente morre."
echo
tar -czf - "${ITENS[@]}" | cifrar "$SAIDA"
chmod 600 "$SAIDA"

echo
echo "backup cifrado: $SAIDA"
echo "sha256: $(sha256sum "$SAIDA" | cut -d' ' -f1)"
echo
echo "AGORA (não pule):"
echo "  1. copie esse arquivo para DOIS lugares separados (pendrive + nuvem)"
echo "  2. teste: ./scripts/backup_chaves.sh --verificar '$SAIDA'"
echo "  3. guarde a senha num gerenciador de senhas ou no papel, longe do arquivo"
