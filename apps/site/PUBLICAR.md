# Publicar o site — o que só o dono faz

O site inteiro é gerado do estado real da corrente. Nenhum agente publica
sozinho: o `publish_lock` exige a sua passphrase e abre uma janela de 5 minutos.

## 1. Gerar

```bash
cd ~/pegasus/asus_the_eye
asus-theye export-static --destino dist/
```

Saem 9 páginas. O `index.html` é a landing com os dois produtos — há teste que
falha se alguém reintroduzir um índice cru de nomes de arquivo.

## 2. Conferir antes de publicar

```bash
python -m http.server -d dist 8080     # abrir localhost:8080 e clicar em tudo
```

Todos os links são relativos e há teste que prova que nenhum aponta para
arquivo inexistente. Site publicado com link morto é pior que site não
publicado.

## 3. Abrir a janela (a sua passphrase)

```bash
python3 scripts/publish_lock.py unlock
```

## 4. Publicar

```bash
cd apps/site && npx wrangler deploy
```

## 5. Ligar ao domínio

Você já tem **theyeofgod.org** na Cloudflare. No painel do worker
`the-eye-site` → Settings → Domains & Routes → Add custom domain →
`theyeofgod.org` (e `www` se quiser).

Custo: **R$ 0**. Assets estáticos ficam na camada gratuita, e o domínio você já
tem.

## O que fica de fora, e por quê

O painel `/markets` (legado, DuckDB) não é exportado quando `ASUS_MARKETS_DB`
não está definido — e isso é deliberado: página que aparece ou some conforme
variável de ambiente tornaria a publicação não determinística.
