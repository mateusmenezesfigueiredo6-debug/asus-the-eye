# Política de segurança

## Reportar uma vulnerabilidade

Repositório privado. Reporte diretamente ao dono do projeto — não abra issue
pública, mesmo que o repositório venha a ser aberto no futuro.

## Superfícies e seu estado

| Superfície | Exposição | Proteção |
| --- | --- | --- |
| Repositório | privada | GitHub privado, 1 colaborador |
| Worker de auditoria | internet | **todos** os endpoints exigem bearer token, `/health` incluído |
| Banco D1 / R2 | conta Cloudflare | acesso só pela conta do dono |
| App comercial | localhost | não publicado |
| Painéis | localhost | não publicados |
| LLM local | máquina | cliente **recusa** host não-local por construção |

## Segredos

Nenhum segredo vive no repositório. Verificado a cada checagem:

| Segredo | Onde vive |
| --- | --- |
| Token do ledger | `~/.the-eye/staging-token` (0600) + cofre da Cloudflare |
| Senha de publicação | `~/.the-eye/publish-lock.json` — só o hash PBKDF2, 480k iterações |
| Credenciais Cloudflare / IBM | nas contas dos provedores, nunca em arquivo |
| Token do GitHub | gerenciado pelo `gh`; o código chama `gh api` e **nunca lê o token** |

## Verificação contínua

```bash
python3 scripts/leak_check.py       # três camadas independentes
```

1. **Estranho** — requisições anônimas devem receber 401 do worker e 404 do repo.
2. **Provedor** — Cloudflare e GitHub confirmam visibilidade, forks, colaboradores.
3. **Matemática** — cadeia de hashes, sequência contígua, raiz Merkle recalculada.

A terceira camada é a que não pede confiança a ninguém: ou o hash bate, ou não bate.

## Trava de publicação

`scripts/publish_guard.py` roda como hook `PreToolUse` e barra comandos que
expõem conteúdo (repo público, release, npm/PyPI/docker, broadcast blockchain).

- A senha é definida pelo dono em prompt oculto e **nunca passa por conversa com IA**.
- Alvos recorrentes (produto vivo publicando versões) são autorizados uma vez.
- Rotina em superfície privada (push, deploy do worker restrito) avisa, não bloqueia.

## Limites conhecidos e assumidos

- **Staging não é produção.** O ledger atual é ambiente de teste (classe L2).
- **`BLOCKCHAIN_BROADCAST_ENABLED` é `false`** por padrão no código e na config.
- **Nenhum dado real de terceiros** foi ingerido: a Fase G exige DPIA humana (L4).
- **Ranqueamento de pessoas está bloqueado no código**, não apenas desencorajado.
