# THE EYE — dashboard reproduzível. Imagem mínima, não-root, fail-closed na auth.
FROM python:3.12-slim AS base

# Não-root por desenho: o serviço nunca roda como root.
RUN useradd --create-home --uid 10001 theeye
WORKDIR /app

# Dependências primeiro (camada cacheável).
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[dashboard,markets]"

# Só o necessário para servir (dados de medição são montados em runtime).
COPY reports/markets ./reports/markets
COPY data ./data

USER theeye
EXPOSE 8712

# --expose força THE_EYE_DASHBOARD_TOKEN: sem token, o container recusa subir.
# Passe o token via secret do orquestrador, nunca no Dockerfile.
ENTRYPOINT ["asus-theye", "serve", "--expose", "--port", "8712"]
