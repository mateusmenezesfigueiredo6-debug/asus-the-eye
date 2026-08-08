#!/usr/bin/env bash
# Gera HANDOFF.md com o estado real, para o Codex (ou outra sessao) continuar.
# Regra do dono: rodar SEMPRE antes de acabar tempo ou contexto.
set -u
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RAIZ" || exit 1
H=HANDOFF.md

{
echo "# HANDOFF — estado para continuar"
echo
echo "Gerado em $(date -Is) por Claude Code."
echo "Cole no Codex: leia AGENTS.md, COORDENACAO.md e este arquivo, nesta ordem."
echo
echo "## Servicos"
for p in "8713/api/health|API funil" "8712/benchmark|Dashboard quantico" "8790/|Site local"; do
  u=${p%%|*}; n=${p##*|}
  echo "- $n: HTTP $(curl -s -o /dev/null -m 5 -w '%{http_code}' "http://localhost:$u" 2>/dev/null)"
done
echo "- Site publico: HTTP $(curl -sL -o /dev/null -m 12 -w '%{http_code}' https://theyeofgod.pages.dev 2>/dev/null)"
echo "- systemd: $(systemctl --user is-active asus-api asus-dashboard asus-site 2>/dev/null | tr '\n' ' ')"
echo
echo "## Git"
for d in "$PWD" "$HOME/asus_global_predictive" "$HOME/Downloads/projeto-algoritmos"; do
  [ -e "$d/.git" ] || continue   # -e, nao -d: em worktree o .git e arquivo
  cd "$d"
  echo "- $(basename "$d"): $(git log --oneline -1 | cut -c1-56) | sujo: $(git status --porcelain | wc -l) | pendentes: $(git log --oneline @{u}..HEAD 2>/dev/null | wc -l)"
done
cd "$RAIZ" || exit 1
echo
echo "## Testes"
PY=""
for cand in "$RAIZ/.venv/bin/python" "$HOME/asus_the_eye/.venv/bin/python" "$(command -v python3)"; do
  [ -x "$cand" ] && { PY="$cand"; break; }
done
if [ -n "$PY" ]; then
  RES=$(PYTHONPATH="$RAIZ/src" timeout 300 "$PY" -m pytest tests/ -p no:cacheprovider 2>&1 \
        | grep -aoE "[0-9]+ (passed|failed|error)[^|]*" | tail -1)
  echo "- ${RES:-NAO MEDIDO: pytest nao devolveu resumo}"
  echo "- interpretador: $PY"
else
  echo "- NAO MEDIDO: nenhum interpretador encontrado"
fi
echo
echo "## Processos em segundo plano"
pgrep -af "python.*(sinal_taxonomia|serie_historica|qkp_|escalada|previsao|monitoramento)" 2>/dev/null \
  | grep -v "shell-snapshots" | sed 's/^/- /' | cut -c1-120 || echo "- nenhum"
echo
echo "## Ultimos artefatos gerados"
ls -t reports/commercial/*.json 2>/dev/null | head -5 | while read -r f; do
  echo "- $f ($(date -r "$f" '+%d/%m %H:%M'))"
done
echo
echo "## PROXIMO PASSO"
if [ -f PROXIMO_PASSO.txt ]; then cat PROXIMO_PASSO.txt; else
  echo "(nao declarado — quem encerrar a sessao deve escrever PROXIMO_PASSO.txt"
  echo " com arquivo, comando e criterio de pronto. Nunca 'continuar de onde parou'.)"
fi
} > "$H"

echo "OK $H"
grep -c "" "$H" | sed 's/^/  linhas: /'
