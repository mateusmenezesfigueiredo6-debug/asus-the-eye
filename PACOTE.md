# O que há neste pacote

Arquivo único do projeto **ASUS + THE EYE**, gerado para transporte a disco
externo. Este documento explica o que está dentro, o que **não** está, e como
retomar a partir dele.

## Como começar

1. Descompacte em qualquer lugar.
2. Leia `RETOMADA.md` — é o documento de retomada completo.
3. Rode `./ONDE_ESTOU.sh` — responde "onde estou?" lendo evidência real.

Para voltar a rodar o código:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[telemetry,dashboard,dev]'
.venv/bin/python -m pytest tests/ -q
```

## O que ESTÁ no pacote

| Conteúdo | Detalhe |
| --- | --- |
| Todo o código-fonte | Python, TypeScript (Worker), Solidity (contrato) |
| Histórico git completo (`.git`) | 20+ commits, toda a evolução rastreável |
| Documentação | ADRs, arquitetura, segurança, LGPD, metodologia de ranking |
| Dados estruturados | 145 nichos jurídicos, 10 schemas da Fase G, 12 arquivos do grafo de fontes |
| Governança | protocolo de lançamento L0–L6, trava de publicação, tripla checagem |
| Testes | 180 testes |
| Relatórios | benchmark, cobertura, lacunas, limitações, registros de lançamento |
| Provas Merkle | lotes com raiz e provas de inclusão verificáveis offline |

## O que NÃO está no pacote — e por quê

| Excluído | Motivo |
| --- | --- |
| `~/.the-eye/staging-token` | Token de acesso ao ledger. **Nunca** deve viajar com o código |
| `~/.the-eye/publish-lock.json` | Hash da sua senha de publicação. Fica só na sua máquina |
| `.venv/` (397 MB) | Ambiente virtual — recriável com um comando |
| `node_modules/` | Dependências do Worker — recriáveis com `npm install` |
| `__pycache__/`, `.pytest_cache/`, `.ruff_cache/` | Artefatos de build |
| Credenciais de Cloudflare e IBM Quantum | Vivem nas contas dos provedores, não em arquivo |

**Consequência prática:** este pacote é seguro para copiar a um disco externo.
Ele contém o *projeto*, não as *chaves*. Quem tiver o pacote não consegue
escrever no seu ledger nem publicar nada em seu nome.

## O que NÃO viaja porque é remoto

Estes recursos vivem na nuvem, na sua conta, e não cabem num zip:

- **Ledger em produção**: Cloudflare Worker + D1 + R2 (`the-eye-audit-staging`)
- **Repositório remoto**: GitHub privado
- **Job quântico**: `d9ngkpcsfqic73ar17vg` no painel da IBM

O pacote traz as *provas* desses eventos (hashes, raízes Merkle, manifestos),
que podem ser verificadas offline com `asus-theye audit-verify`.

## Verificação de integridade

O arquivo `PACOTE_MANIFEST.txt` acompanha o pacote com o SHA-256 de cada
arquivo. Para conferir depois de copiar:

```bash
sha256sum -c PACOTE_MANIFEST.txt
```
