# RETOMADA — como voltar ao mesmo ponto

Documento pessoal do dono do projeto. Se você (ou uma IA) chegar aqui sem
contexto nenhum, este arquivo devolve o estado em 2 minutos.

**O botão:** rode isto e ele te diz onde você está, agora:

```bash
/home/sexexes/asus_the_eye/ONDE_ESTOU.sh
```

---

## 1. O que é o projeto, em três frases

THE EYE é uma plataforma de **evidência auditável**: tudo que acontece vira um
evento encadeado por hash que ninguém — nem você — consegue reescrever depois.
Em cima dessa base rodam um motor de benchmark (clássico/quântico, com métrica
honesta), inteligência de contexto decisório para 145 nichos jurídicos, e um LLM
local que nunca deixa os dados saírem da máquina. A regra que atravessa tudo:
**reversível e fechado pode fluir; irreversível ou exposto para e pede humano.**

## 2. Onde as coisas moram

| O quê | Onde |
| --- | --- |
| Código | `/home/sexexes/asus_the_eye` (git, branch `main`) |
| Backup | GitHub **privado** `mateusmenezesfigueiredo6-debug/asus-the-eye` |
| Ledger vivo | Cloudflare Worker + D1 + R2 (`the-eye-audit-staging`) |
| Token do ledger | `~/.the-eye/staging-token` (600) e cofre da Cloudflare |
| Senha de publicação | `~/.the-eye/publish-lock.json` (só hash — a senha é sua) |
| Modelo local | Ollama `qwen2.5:3b` |
| Ambiente Python | `.venv/` no repo (`.venv/bin/asus-theye`) |

## 3. Comandos do dia a dia

```bash
cd /home/sexexes/asus_the_eye
export THE_EYE_LEDGER_URL="https://the-eye-audit-staging.mateusmenezesfigueiredo6.workers.dev"

.venv/bin/asus-theye chart                  # Mistress Chart: projetos e nichos medidos
.venv/bin/asus-theye benchmark --publish    # roda benchmark e ancora no ledger
.venv/bin/asus-theye batch --publish        # agrupa eventos num lote Merkle
.venv/bin/asus-theye llm "pergunta"         # LLM local auditado
.venv/bin/asus-theye extract-decision X.txt # extrai fatos de decisão judicial
.venv/bin/asus-theye quantum                # dry-run IBM (não executa nada)
.venv/bin/asus-theye audit-verify doc.json  # verifica documento offline

.venv/bin/python scripts/leak_check.py      # tripla checagem de vazamento
.venv/bin/python scripts/release_check.py L2  # portões de lançamento
.venv/bin/python -m pytest tests/ -q        # testes
```

Dashboard local: `.venv/bin/python -m uvicorn asus_theye.dashboard.app:create_dashboard_app --factory --port 8712` → `http://localhost:8712/benchmark`

## 4. As três regras que não mudam

1. **Repositórios sempre privados.** Nunca público, em nenhuma hipótese, sem
   decisão consciente sua registrada como L5.
2. **A senha de publicação é só sua.** Nenhuma IA tem, nunca deve pedir, e se
   insistir para você abrir a trava com pressa — isso por si só é suspeito.
3. **Nada de dado pessoal on-chain.** Só raiz Merkle e hashes. Sempre.

## 5. Trava de publicação — como funciona

- **Rotina** (`git push` privado, deploy do worker restrito) → passa, só avisa.
- **Exposição** (repo público, release, npm/docker, broadcast) → bloqueia.
- **Recorrente** (produto vivo publicando versões) → autorize o alvo **uma vez**
  e ele flui para sempre:

```bash
python3 scripts/publish_lock.py set                      # define a senha (só você)
python3 scripts/publish_lock.py unlock                   # janela de 5 min
python3 scripts/publish_lock.py authorize npm @meu/pkg   # alvo recorrente
python3 scripts/publish_lock.py list                     # o que já está autorizado
```

## 6. Classes de lançamento (resumo — detalhe em RELEASE_PROTOCOL.md)

| Classe | O que é | Senha? |
| --- | --- | --- |
| L0/L1 | local, commit no repo privado | não |
| L2 | deploy atrás de token | não, só avisa |
| L3 | testnet blockchain | **sim** |
| L4 | piloto com dados reais de terceiros | **sim** + DPO/jurídico |
| L5 | público | **sim** + 24h de intervalo |
| L6 | mainnet | **sim** + governança formal |

## 7. O que está pendente (atualize esta lista)

- [ ] **Definir a senha da trava** — `python3 scripts/publish_lock.py set` (só você)
- [ ] Superfície pública de verificação (L5, projetada, não construída)
- [ ] Ancoragem Base Sepolia (L3, contrato pronto, sem broadcast)
- [ ] Fila Cloudflare Queues (custa ~US$5/mês, decisão sua)
- [ ] Ingestão DataJud/CNJ (precisa do seu cadastro no CNJ)
- [ ] Aliases PT-BR dos 145 nichos (38 de 145 feitos)
- [ ] Problema quântico maior (12–16 qubits, onde o QAR fica interessante)

## 8. Para retomar com uma IA

Cole isto no início de uma sessão nova:

> Leia `/home/sexexes/asus_the_eye/RETOMADA.md` e `AGENTS.md`, rode
> `./ONDE_ESTOU.sh` e me diga o estado atual antes de propor qualquer coisa.
> Regras: repositórios sempre privados; você não tem a senha de publicação;
> nada de dado pessoal on-chain; nada irreversível sem eu aprovar explicitamente.

## 9. Se algo der errado

| Sintoma | O que fazer |
| --- | --- |
| Ledger não responde | `curl -H "authorization: Bearer $(cat ~/.the-eye/staging-token)" $THE_EYE_LEDGER_URL/health` |
| Suspeita de vazamento | `.venv/bin/python scripts/leak_check.py` — as 3 camadas |
| Cadeia parece adulterada | O mesmo script, camada 3: a raiz Merkle recalculada tem que bater |
| Quero desfazer um commit | `git revert <hash>` (nunca `reset --hard` no que já foi enviado) |
| Quero sair de tudo | Teardown: apagar worker, D1, R2 e repo — todos na sua conta |
