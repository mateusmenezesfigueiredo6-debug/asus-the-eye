# Tripla checagem de vazamento

`python3 scripts/leak_check.py` — rode a qualquer momento, sem IA no meio.

Três camadas independentes, desenhadas para não depender de confiar em ninguém:

| Camada | Pergunta | Como responde |
| --- | --- | --- |
| 1. Estranho | O que um terceiro sem credencial consegue? | Requisições anônimas ao worker (esperado 401) e à API pública do GitHub (esperado 404) |
| 2. Provedor | O que Cloudflare e GitHub registram? | Visibilidade, forks, estrelas, colaboradores — dados deles, não nossos |
| 3. Matemática | Alguém escreveu, alterou ou removeu algo? | Encadeamento de hashes, sequência contígua, raiz Merkle recalculada vs. armazenada, provas de inclusão |

A camada 3 é a única que não pode ser enganada por promessa: ou a raiz recalculada
é idêntica à armazenada, ou não é. Um evento injetado, editado ou removido muda a
raiz e o script acusa.

## Trava de publicação

`scripts/publish_lock.py` + `scripts/publish_guard.py` (hook PreToolUse):

- **EXPOSE** (repo público, release, gist, npm/PyPI/docker, broadcast blockchain):
  bloqueado sem a senha. A senha é definida por você em prompt oculto e guardada
  só como hash PBKDF2 — nunca passa por conversa com IA.
- **ROTINA** (push para o repo privado, deploy do worker restrito): avisa, não bloqueia.

    python3 scripts/publish_lock.py set      # define a senha (só você digita)
    python3 scripts/publish_lock.py unlock   # abre janela de 5 minutos
    python3 scripts/publish_lock.py status   # estado atual
