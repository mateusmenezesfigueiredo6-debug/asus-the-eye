# Publicar o site de apresentacao (gotaverde)

Runbook para o dono. Agentes nao executam estes passos (regra do
publish lock).

1. Gerar o site:

       python src/asus_theye/dashboard/cannabis_demo.py dist-cannabis

2. Conferir localmente:

       python -m http.server -d dist-cannabis 8080

3. Definir os secrets (uma vez):

       cd apps/cannabis-demo
       npx wrangler secret put SITE_ACCESS_CODE   # o codigo que abre o site
       npx wrangler secret put COOKIE_SECRET      # string aleatoria longa

   Gerar um COOKIE_SECRET forte: `openssl rand -hex 32`.

4. Destravar e publicar:

       python3 scripts/publish_lock.py unlock
       cd apps/cannabis-demo && npx wrangler deploy

5. O site sobe em `gotaverde.<sua-conta>.workers.dev`. Sem cookie
   valido, qualquer rota mostra a tela de codigo; o cookie dura 12 horas.

Para trocar o codigo de acesso, repita `wrangler secret put
SITE_ACCESS_CODE` e faca novo deploy.
