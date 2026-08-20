#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
# Adjudicacao real com dois modelos remotos: um propoe, o outro refuta.
#
#   make adjudicate Q="sua pergunta"
#   bash scripts/adjudicate_real.sh "sua pergunta"
#
# Existe porque a chamada remota tem tres pre-condicoes independentes (egresso
# liberado para cada provedor, chave de cada provedor, porta aberta) e falhar
# numa delas no meio da execucao produz um erro que nao diz qual faltou. Aqui
# todas sao checadas antes, e nada e enviado ate que todas passem.
#
# Nao imprime valor de chave em lugar nenhum, so o comprimento. A porta
# THE_EYE_REMOTE_LLM e aberta apenas para esta execucao: rodar este script e o
# ato consciente que a regra 6 exige, e ele nao deixa a porta aberta depois.
#
# Nunca use este caminho para dado da Fase G (contexto decisorio judicial):
# e local por construcao (ADR-001).

set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

PROPOSER="${PROPOSER:-chatgpt}"
CHALLENGER="${CHALLENGER:-claude}"
PERGUNTA="${1:-}"
if [ -z "$PERGUNTA" ]; then
  PERGUNTA="O log de chamadas de LLM do THE EYE encadeia cada registro com o SHA-256 do anterior?"
fi

if [ -x .venv/bin/python ]; then
  PY=.venv/bin/python
else
  PY=python3
fi

faltando=0

# Um 403 no CONNECT e negacao de politica de egresso, nao falha de rede: quem
# libera e o dono do ambiente, e contornar por dentro seria furar a politica.
checar_egresso() {
  local host="$1" nome="$2" codigo
  # O `|| true` fica DENTRO da substituicao de propósito: em falha o curl ja
  # escreve "000" por conta do -w, e um `|| echo 000` por fora concatenaria um
  # segundo "000", fazendo um host bloqueado passar por alcancavel.
  codigo=$(curl -s -o /dev/null -w "%{http_code}" -m 10 "https://$host/v1/models" 2>/dev/null || true)
  if [ -z "$codigo" ] || [ "$codigo" = "000" ]; then
    echo "  [FALTA] $nome: $host inalcancavel (tipicamente 403 no CONNECT = politica de egresso)"
    return 1
  fi
  echo "  [ok]    $nome: $host alcancavel (HTTP $codigo)"
}

# So o comprimento e exibido; o valor nunca aparece no terminal nem em log.
checar_chave() {
  local var="$1" nome="$2" valor
  valor="${!var:-}"
  if [ -z "$valor" ]; then
    echo "  [FALTA] $nome: $var nao definida"
    return 1
  fi
  echo "  [ok]    $nome: $var definida (${#valor} caracteres, valor nunca exibido)"
}

provedor_host() {
  case "$1" in
    chatgpt | gpt | openai) echo "api.openai.com" ;;
    claude | anthropic) echo "api.anthropic.com" ;;
    local | ollama) echo "" ;;
    *) echo "" ;;
  esac
}

provedor_chave() {
  case "$1" in
    chatgpt | gpt | openai) echo "OPENAI_API_KEY" ;;
    claude | anthropic) echo "ANTHROPIC_API_KEY" ;;
    *) echo "" ;;
  esac
}

echo "=== pre-condicoes ($PROPOSER propoe, $CHALLENGER refuta) ==="
for papel in "$PROPOSER" "$CHALLENGER"; do
  host=$(provedor_host "$papel")
  chave=$(provedor_chave "$papel")
  if [ -z "$host" ]; then
    echo "  [ok]    $papel: local, nao sai da maquina"
    continue
  fi
  checar_egresso "$host" "$papel" || faltando=$((faltando + 1))
  checar_chave "$chave" "$papel" || faltando=$((faltando + 1))
done

if [ "$faltando" -gt 0 ]; then
  echo
  echo "$faltando pre-condicao(oes) faltando. Nada foi enviado para lugar nenhum."
  echo "Libere o egresso do provedor no ambiente e defina as chaves; depois rode de novo."
  exit 1
fi

echo
echo "=== chamada real ==="
echo "pergunta: $PERGUNTA"
echo "aviso: a partir daqui o prompt sai desta maquina para os dois provedores."
echo

if THE_EYE_REMOTE_LLM=1 "$PY" -m asus_theye.cli adjudicate "$PERGUNTA" \
  --proposer "$PROPOSER" --challenger "$CHALLENGER"; then
  codigo=0
else
  codigo=$?
fi

echo
case "$codigo" in
  0) echo "exit=0 — os dois concordaram na substancia e na classe da alegacao" ;;
  2) echo "exit=2 — CONFLICTED: discordaram. E um resultado valido, nao uma falha" ;;
  *) echo "exit=$codigo — a adjudicacao falhou" ;;
esac

echo
echo "=== trilha desta execucao (so hashes, nunca o texto) ==="
if [ -s reports/llm/calls.jsonl ]; then
  tail -2 reports/llm/calls.jsonl | "$PY" -c '
import json
import sys

for linha in sys.stdin:
    if linha.strip():
        r = json.loads(linha)
        print(f"  backend={r[\"backend\"]:<10} model={r[\"model\"]:<22} hash={r[\"record_hash_sha256\"][:16]}...")
'
else
  echo "  (nenhum registro)"
fi

exit "$codigo"
