# Proveniência — OpenZeppelin Contracts (vendoring)

Registro de reuso de terceiro, conforme a política de licenças do projeto.
Este é o **único caso de CÓPIA LITERAL** no repositório — todos os demais
registros nesta pasta são reimplementações independentes. Por isso ele é o que
mais precisa de registro, e por isso este arquivo existe.

## O que foi copiado

| campo | valor |
|---|---|
| Projeto | OpenZeppelin Contracts |
| Origem | https://github.com/OpenZeppelin/openzeppelin-contracts |
| Versão vendorada | **v5.7.0** (`contracts/audit-anchor/lib/openzeppelin-contracts/VENDORED_TAG`) |
| Licença | **MIT** — © 2016–2026 Zeppelin Group Ltd (`LICENSE` preservado íntegro na pasta) |
| Local no repo | `contracts/audit-anchor/lib/openzeppelin-contracts/` |
| Volume | 368 arquivos `.sol` (release completo, sem poda) |
| Natureza | **cópia literal (vendoring)** — nenhuma linha alterada |

## O que é efetivamente usado

O contrato do titular (`contracts/audit-anchor/src/TheEyeAuditAnchor.sol`, este
sim obra própria) importa exatamente **dois** componentes:

```solidity
import {AccessControlDefaultAdminRules} from
    "@openzeppelin/contracts/access/extensions/AccessControlDefaultAdminRules.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";

contract TheEyeAuditAnchor is AccessControlDefaultAdminRules, Pausable {
```

O `remapping` que liga os dois vive em `src/asus_theye/audit/anchor.py`
(`OZ_LIB` + `import_remappings`).

## Por que vendorar em vez de reimplementar

Controle de acesso e pausa de contrato são **primitivas de segurança
auditadas**. Reimplementá-las seria o oposto da doutrina do projeto: trocaria
código revisado pela comunidade e auditado profissionalmente por código novo,
não auditado, num contrato que guarda a prova temporal da corrente. Aqui o
reuso É a decisão segura.

Vendorar (em vez de baixar na hora do build) fixa a versão: o contrato
`0x910dAa67E74B0367872F7073884aaaB2a3458600`, deployado na Base Sepolia, foi
compilado contra **esta** árvore de arquivos. Build reproduzível exige que ela
não mude sob os pés.

## Fronteira de titularidade

Os 368 arquivos desta pasta são **obra de terceiro** e permanecem sob MIT, com
o aviso de copyright original intacto. Eles estão **explicitamente excluídos**
do carimbo de titularidade (`IGNORAR` em `scripts/aplicar_titularidade.py`):
carimbar obra alheia com o nome do titular seria exatamente o oposto do que
aquele script existe para fazer.

O que é do titular e está declarado como tal:
- `contracts/audit-anchor/src/TheEyeAuditAnchor.sol` — o contrato em si
- `contracts/audit-anchor/test/TheEyeAuditAnchor.t.sol` — os testes
- `src/asus_theye/audit/anchor.py` — a compilação, o lote e o broadcast

## Conformidade com a MIT

A licença MIT exige que o aviso de copyright e o texto da licença acompanhem
cópias substanciais do software. Cumprido: `LICENSE` está preservado na pasta
vendorada, o `NOTICE` da raiz cita a absorção, e este arquivo registra versão,
origem e fronteira.

---

© 2026 Mateus Menezes Figueiredo — o projeto ASUS THE EYE é AGPL-3.0-or-later;
este registro descreve obra de terceiro sob MIT, cuja titularidade permanece de
Zeppelin Group Ltd.
