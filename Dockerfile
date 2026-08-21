# THE EYE — dashboard reproduzível. Imagem mínima, não-root, fail-closed na auth.
FROM python:3.12-slim AS base

# Não-root por desenho: o serviço nunca roda como root.
RUN useradd --create-home --uid 10001 theeye
WORKDIR /app

# Dependências primeiro (camada cacheável).
#
# A ORDEM destes COPY é requisito de correção, não de cache. `src/asus_theye/data`
# e `src/asus_theye/migrations` são SYMLINKS para as árvores da raiz, e o
# package-data do pyproject empacota através deles. Se o `pip install` rodar
# antes de `/app/data` existir, o symlink está pendurado, o glob do setuptools
# não casa nada, o build sai com código 0 e a wheel instalada vem SEM NENHUM dos
# arquivos de dados — falha silenciosa, encontrada só em produção.
COPY pyproject.toml README.md ./
COPY src ./src
COPY migrations ./migrations
COPY data ./data
RUN pip install --no-cache-dir ".[dashboard,markets]"

# A guarda que transforma a falha silenciosa em build quebrado. Custa
# milissegundos e é a diferença entre descobrir isto aqui ou numa rota 500.
RUN python -c "\
from asus_theye._pkg_paths import pkg_data; \
alvo = pkg_data('data', 'domains', 'mercados_preditivos.json'); \
assert alvo.exists(), f'package-data ausente na imagem: {alvo}'; \
print('package-data OK:', alvo)"

# Só o necessário para servir (dados de medição são montados em runtime).
COPY reports/markets ./reports/markets

USER theeye
EXPOSE 8712

# --expose força THE_EYE_DASHBOARD_TOKEN: sem token, o container recusa subir.
# Passe o token via secret do orquestrador, nunca no Dockerfile.
ENTRYPOINT ["asus-theye", "serve", "--expose", "--port", "8712"]
