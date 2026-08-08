# Tarefa: fechar a etapa 7 — superfície pública de verificação

Você está num `git worktree` próprio em `/home/sexexes/asus_the_eye_codex`, no
branch `codex/etapa-7-verificador`. O Claude trabalha em paralelo no diretório
principal `/home/sexexes/asus_the_eye` (branch `main`). **Não saia deste
worktree e não troque de branch** — foi exatamente essa colisão que já custou
12 commits perdidos numa sessão anterior.

## Por que esta é a tarefa

A plataforma é **preditiva e unificada** — um observatório auditável de
fronteira tecnológica, não um produto jurídico. A missão está no `AGENTS.md`
da raiz; leia antes de escrever qualquer linha.

A medição de hoje (`reports/chart/snapshot.json`) diz: 103 de 106 artefatos
existem. Os três que faltam são todos seus:

    apps/public-verifier/worker.ts
    apps/public-verifier/wrangler.toml
    apps/public-verifier/README.md

Enquanto eles não existem, a plataforma tem cadeia de evidência, Merkle e
verificador — e **ninguém de fora consegue conferir nada**. Uma plataforma de
verificação que só se verifica sozinha não prova coisa alguma. A etapa 7 é o
que fecha isso.

## O que construir

Um Cloudflare Worker de **leitura apenas**, sem credencial, que deixa um
terceiro conferir provas sem ter acesso a dado nenhum.

    GET  /health              vivo, sem dado de tenant
    POST /verify              recebe um documento de auditoria offline (JSON)
                              e devolve válido/inválido com o motivo
    GET  /root/:date          raiz Merkle publicada naquela data, se houver
    GET  /                    página estática explicando o que dá para conferir

### Regras que não se negociam

1. **Só hash.** Nenhum endpoint devolve conteúdo de evento, payload, nome de
   tenant ou qualquer dado pessoal. Se a resposta pode revelar o que foi
   registrado, ela está errada.
2. **Sem credencial.** O verificador público não autentica ninguém e não
   guarda segredo. Se precisar de token para funcionar, o desenho está errado.
3. **Falha é resposta.** Documento inválido devolve 200 com
   `{"valido": false, "motivo": "..."}`, não 500. O motivo diz onde a cadeia
   quebrou — qual sequência, qual hash esperado contra qual recebido.
4. **Sem emoji** em qualquer saída, incluindo a página estática e o README.
5. **Não promova fase.** O projeto é L5 no manifesto; deixe assim. Promoção
   L0–L6 exige aprovação humana registrada e você não tem essa aprovação.

### Onde está a lógica que você reaproveita

    src/asus_theye/audit/verifier.py     verify_document — a semântica de
                                         verificação já decidida; o worker
                                         reimplementa em TS, não reinventa
    src/asus_theye/audit/merkle.py       raiz e prova de inclusão
    src/asus_theye/audit/ledger.py       formato do evento e do encadeamento
    apps/verifier/app.py                 a versão FastAPI local — mesmo
                                         contrato, outra superfície
    infra/cloudflare/worker.ts           estilo de worker adotado no projeto
    infra/cloudflare/staging/wrangler.toml   formato de config já usado

O `GENESIS_HASH` é 64 zeros. A verificação de continuidade confere que cada
evento aponta o hash do anterior e que a sequência não tem buraco até a gênese.

## O que entregar

1. Os três artefatos, existindo de fato nos caminhos declarados.
2. Teste que roda sem rede — o worker precisa ser testável com um documento
   fixo de entrada, incluindo pelo menos um caso de cadeia quebrada.
3. `python3 -m asus_theye.cli chart` rodando e mostrando a etapa 7 acima de 0%.
4. Commit no branch `codex/etapa-7-verificador` com mensagem explicando a
   decisão de desenho, não só o que mudou.

Não faça deploy. Publicar é decisão do Mateus, e o `scripts/publish_lock.py`
exige passphrase que você não tem.

## Se travar

Escreva o que travou em `COORDENACAO.md` (seção de mensagens entre agentes) e
siga para a próxima parte. Entregar dois dos três com o motivo do terceiro
registrado vale mais que travar nos três.
