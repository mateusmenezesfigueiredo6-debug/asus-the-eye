# Proveniência — segno + zxing-cpp (geração e verificação de QR)

Registro de dependência de terceiros, conforme a política de licenças do projeto.

## Finalidade

Usadas exclusivamente em `scripts/qr_do_backup.py` para gerar e verificar
o QR de custódia do backup cifrado das chaves.

## Bibliotecas

| campo | segno | zxing-cpp | Pillow |
|---|---|---|---|
| Projeto | segno | zxing-cpp Python binding | Pillow |
| Origem | https://github.com/heuer/segno | https://github.com/zxing-cpp/zxing-cpp | https://github.com/python-pillow/Pillow |
| Versão usada | 1.6+ | 3.1+ | 12+ |
| Licença | **MIT** | **Apache-2.0** | **HPND (permissiva)** |
| Natureza | geração de QR code | decodificação de QR code | leitura de imagem PNG |
| Uso | `segno.make(hash_hex)` | `zxingcpp.read_barcodes(img)` | `Image.open(bytes)` |

## Por que estas três e não outras

- **segno**: única biblioteca Python de geração de QR sem dependências de
  compilação, licença MIT, mantida ativamente, suporta todos os níveis de
  correção de erro.
- **zxing-cpp**: binding oficial da biblioteca Apache ZXing C++ (o mesmo motor
  que alimenta decodificadores em Android e Chrome), licença Apache-2.0, roda
  offline sem JVM.
- **Pillow**: já era dependência indireta do projeto; necessária para converter
  PNG em formato que o zxing-cpp aceita.

## Por que não stdlib

A stdlib do Python não inclui geração nem decodificação de QR. Usar apenas
`hashlib` + `qr` manual seria reinventar uma especificação complexa (ISO/IEC
18004) com alto risco de gerar QRs não legíveis por leitores de prateleira.

## Verificação de licenças

```
# segno — MIT
curl -s https://raw.githubusercontent.com/heuer/segno/master/LICENSE | head -3
# The MIT License

# zxing-cpp — Apache-2.0
curl -s https://raw.githubusercontent.com/zxing-cpp/zxing-cpp/master/LICENSE | head -3
# Apache License

# Pillow — HPND
pip show Pillow | grep License
# License: HPND
```

## Registrado em

`scripts/qr_do_backup.py` — docstring, seção BIBLIOTECAS.

## Data de absorção

2026-08-20
