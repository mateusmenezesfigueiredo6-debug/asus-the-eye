# ADR-013 — Licença AGPL-3.0 para o código, restrita para os dados

**Status:** aceito · **Data:** 2026-08-05 · **Supera:** [ADR-012](ADR-012-ESTRUTURA-E-FERRAMENTAS.md) §1

## Contexto

O projeto adotou MIT em 03/08/2026 (ADR-012 §1). Dois dias depois a licença foi
trocada por AGPL-3.0-or-later, e o diretório `data/` recebeu licença própria e
restrita. A troca aconteceu, o `LICENSE`, o `pyproject.toml` e o `CONTRIBUTING`
foram atualizados — mas **o raciocínio nunca foi registrado**, e o ADR-012
continuou afirmando "Licença MIT". Este documento fecha essa lacuna.

A convenção do próprio projeto é explícita no `CONTRIBUTING`: *"Se a mudança
envolve uma decisão não óbvia, ela vira um ADR."* Trocar a licença de um
repositório é o exemplo mais claro possível de decisão não óbvia.

## Decisões

### 1. Código sob AGPL-3.0-or-later

MIT permite que qualquer um pegue o código, feche e ofereça como serviço sem
devolver nada. Para um projeto cuja tese é **evidência verificável**, isso é
mais que uma perda comercial: um fork fechado poderia oferecer "auditoria"
sem que ninguém pudesse conferir se as garantias — cadeia append-only, score
sem imputação, recusa de ranquear pessoas — continuam de pé.

A AGPL fecha especificamente o buraco que importa aqui: quem roda o software
**como serviço em rede** precisa oferecer o código-fonte aos usuários desse
serviço. Como o produto natural deste projeto é justamente um serviço em rede
(o worker de auditoria, o verificador público, o painel), a cláusula de rede é
o mecanismo, não um detalhe.

### 2. `data/` sob licença restrita, fora da AGPL

O diretório `data/` não é código: é **trabalho de curadoria**. As 145 áreas
jurídicas em 22 grupos, os aliases PT-BR revisados um a um, os 19 tipos de
categoria da Phase C, os pesos de score — isso é o resultado de decisões
editoriais, não de compilação.

Separar as licenças reconhece o que cada parte é. O código pode circular sob
copyleft; a curadoria segue sob controle do titular. Misturar as duas numa
licença só trataria trabalho de natureza diferente como se fosse a mesma coisa.

### 3. A troca foi feita enquanto havia autor único

Detalhe jurídico decisivo, e por isso registrado: relicenciar exige o
consentimento de todos os detentores de direitos sobre o código. Com autor
único, o titular decide sozinho. **Depois da primeira contribuição externa
aceita, essa janela fecha** — e uma nova troca passaria a exigir o acordo de
cada contribuidor, ou a remoção do código deles.

Foi por isso que a troca aconteceu agora e não depois. Quem contribuir daqui
para frente concorda, ao enviar, que a contribuição entra sob a mesma licença.

## Consequências

- Fork fechado oferecido como serviço deixa de ser possível sem devolver fonte.
- Uso comercial continua permitido — AGPL não é "não comercial"; ela é copyleft.
- Adoção por empresas com política anti-AGPL fica mais difícil. Custo aceito
  conscientemente: a garantia vale mais que o alcance.
- Qualquer PR que toque `data/` precisa de acordo prévio com o titular, e o
  `CONTRIBUTING` diz isso na cara de quem contribui.
- O `pyproject.toml` declara `license = { text = "AGPL-3.0-or-later" }`, então
  a informação viaja com o pacote, não só com o repositório.

## O que reverteria esta decisão

Uma decisão consciente de priorizar adoção sobre garantia — e, a partir da
primeira contribuição externa, o consentimento de todos os contribuidores.
Nenhuma das duas coisas acontece por acidente.

## Nota de método

Este ADR **supera** o ADR-012 §1 em vez de editá-lo. Um ADR registra o que foi
decidido naquele momento, com o que se sabia então. Reescrever a decisão antiga
para casar com a nova apagaria a história — exatamente o que o ledger deste
projeto existe para impedir. A seção antiga ficou no lugar, com o aviso de
superação e o link para cá.
