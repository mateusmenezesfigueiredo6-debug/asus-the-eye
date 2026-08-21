# Proveniência — segno + zxing-cpp (geração e verificação de QR)

Registro de dependência de terceiros, conforme a política de licenças do projeto.

## Finalidade

Usadas exclusivamente em `scripts/qr_do_backup.py` para gerar e verificar
o QR de custódia do backup cifrado das chaves.

## Bibliotecas

| campo | segno | zxing-cpp | Pillow |
|---|---|---|---|
| Projeto | segno | zxing-cpp (binding Python) | Pillow |
| Origem | https://github.com/heuer/segno | https://github.com/zxing-cpp/zxing-cpp | https://github.com/python-pillow/Pillow |
| Declarado no `pyproject` | `segno>=1.6` | `zxing-cpp>=3.1` | `Pillow>=10` |
| Versão conferida | 1.6.6 | 3.1.1 | 12.3.0 |
| **Licença** | **BSD-3-Clause** | **Apache-2.0** | **MIT-CMU** |
| Compatível com AGPL-3.0-or-later | sim | sim | sim |
| Natureza | geração de QR | decodificação de QR | leitura de PNG |
| Uso | `segno.make(hash_hex)` | `zxingcpp.read_barcodes(img)` | `Image.open(bytes)` |

## Correção de um registro anterior, e por que ela está aqui

A primeira versão deste documento declarava **segno como MIT** e **Pillow como
HPND**, e exibia, como prova executada, saídas de comando que os comandos não
produzem. As licenças reais são as da tabela acima.

O erro não criava risco jurídico — BSD-3-Clause, Apache-2.0 e MIT-CMU são todas
permissivas e compatíveis com AGPL-3.0-or-later, tanto quanto MIT e HPND seriam.
O problema é outro, e é maior: **este documento existe para ser prova**. Prova
que exibe saída de comando que ninguém rodou não é prova fraca — é o oposto do
que a casa afirma ser, e cria a aparência de auditoria feita exatamente onde ela
não foi. A correção fica registrada em vez de apagada, porque um registro que se
reescreve em silêncio vale tanto quanto o registro errado.

## Verificação — os comandos, e o que eles devolveram de verdade

Conferido em 21/08/2026 contra a origem, e ancorado por `sha256` do texto da
licença, como já se faz com a página de termos do GDELT: se o upstream mudar
amanhã, o hash prova o que vigia hoje.

```
$ python -c "import json,urllib.request; \
    d=json.load(urllib.request.urlopen('https://pypi.org/pypi/segno/json'))['info']; \
    print(d['version'], [c for c in d['classifiers'] if c.startswith('License')])"
1.6.6 ['License :: OSI Approved :: BSD License']

$ curl -s https://raw.githubusercontent.com/heuer/segno/master/LICENSE | head -2
Copyright (c) 2016 - 2025, Lars Heuer
All rights reserved.
    -> 1503 bytes, sha256 de6c85fccf5d5290...
    -> contém os 3 marcadores de cláusula BSD => BSD-3-Clause

$ curl -s https://raw.githubusercontent.com/zxing-cpp/zxing-cpp/master/LICENSE | head -2
                                 Apache License
                           Version 2.0, January 2004
    -> 11358 bytes, sha256 c6596eb7be8581c1...

$ python -c "import json,urllib.request; \
    print(json.load(urllib.request.urlopen('https://pypi.org/pypi/Pillow/json'))['info']['license_expression'])"
MIT-CMU
```

Sobre o Pillow, um detalhe que derrubou a prova antiga: o pacote **não emite
mais** um campo `License:`, e sim `License-Expression: MIT-CMU`. Um `pip show
Pillow | grep License` não devolve `License: HPND` em versão nenhuma que este
projeto aceite.

## Por que estas três, sem enfeitar o pedigree

- **segno**: geração de QR em Python puro, sem etapa de compilação e sem
  dependência de runtime. Cobre todos os níveis de correção de erro.
- **zxing-cpp**: decodificador C++ com binding Python mantido **no próprio
  repositório** do projeto. Roda offline, sem JVM.
  Correção de uma afirmação anterior: o zxing-cpp **não** é da Apache Software
  Foundation e **não** é o motor do Chrome. O próprio projeto se descreve como
  port independente, iniciado a partir do ZXing em Java e desenvolvido desde
  então por conta própria. A licença é Apache-2.0 — o nome da licença foi
  confundido com um pedigree institucional que não existe.
- **Pillow**: converte os bytes do PNG no formato que o zxing-cpp aceita.
  Correção de uma afirmação anterior: o Pillow **não** era dependência do
  projeto, nem direta nem indireta. Este PR o introduz. Dizer que já estava lá
  fazia a terceira dependência parecer de graça quando não é.

## Custo e vínculo — a regra dura nº 1

As três são pacotes do PyPI, gratuitos, executando **offline**: sem conta, sem
chave, sem serviço, sem camada paga, sem telemetria. Nada aqui cria despesa
recorrente nem prende o titular a fornecedor.

O `zxing-cpp` é código C++ e depende de wheel pronto para a plataforma; onde não
houver, exige toolchain de compilação. É custo de instalação, não de dinheiro —
e por isso as três entram como **extra opcional** `[qr]`, não como dependência
do caminho principal: quem não gera QR não paga esse preço.

## Por que não a stdlib

A stdlib não gera nem decodifica QR. Implementar a ISO/IEC 18004 à mão para
produzir um código que leitores de prateleira precisam ler é reinventar uma
especificação complexa no ponto em que um erro silencioso significaria um QR de
custódia ilegível justamente no dia em que ele fosse necessário.

## Registrado em

`scripts/qr_do_backup.py` — docstring, seção BIBLIOTECAS.

## Data de absorção

2026-08-20
