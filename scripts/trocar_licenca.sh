#!/usr/bin/env bash
# Troca AGPL-3.0-or-later por licença proprietária em TODOS os arquivos dos dois repos.
# NÃO roda sozinho. Decisão do titular. Reversível com `git checkout -- .` enquanto não commitar.
# Pré-condição (Parte IV do termo): o código NÃO foi distribuído a terceiro sob AGPL.
set -euo pipefail
NOVA="LicenseRef-THE-EYE-Proprietaria"
for repo in "$HOME/pegasus/asus_the_eye" "$HOME/projetos/painel-mercados"; do
  cd "$repo"
  n=$(grep -rlE "SPDX-License-Identifier: AGPL-3.0-or-later" --include='*.py' --include='*.ts' --include='*.tsx' --include='*.mjs' --include='*.js' --include='*.css' --include='*.md' . | grep -vE "node_modules|\.venv|\.next" | wc -l)
  grep -rlE "SPDX-License-Identifier: AGPL-3.0-or-later" --include='*.py' --include='*.ts' --include='*.tsx' --include='*.mjs' --include='*.js' --include='*.css' --include='*.md' . | grep -vE "node_modules|\.venv|\.next" | xargs -r sed -i "s|SPDX-License-Identifier: AGPL-3.0-or-later|SPDX-License-Identifier: $NOVA|"
  cat > LICENSE <<L
THE EYE — Licença Proprietária ($NOVA)
Copyright (c) 2026 Mateus Menezes Figueiredo. Todos os direitos reservados.
Nenhuma licença de uso, cópia, modificação, distribuição, execução por rede ou venda é concedida
sem autorização prévia e expressa do titular (Lei 9.610/1998, art. 29; Lei 9.609/1998, art. 2º).
Termos completos: Área de trabalho/PORTAL-CIVICO-2026/TERMO-EXCLUSIVIDADE-E-SIGILO-2026-09-04.md
L
  echo "$repo: $n arquivos trocados · LICENSE gravado (não commitado)"
done
echo "Para desfazer antes do commit: git checkout -- . && rm LICENSE   (em cada repo)"
