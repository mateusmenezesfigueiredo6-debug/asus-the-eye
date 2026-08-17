# Proveniência — WPAM (gerador de probabilidade)

Registro de reuso legítimo de código de terceiro, conforme a política de
licenças do projeto. Cada absorção externa fica registrada aqui e entra na
cadeia auditável.

| Campo | Valor |
| --- | --- |
| Componente do projeto | `src/asus_theye/markets/gerador.py` |
| Origem | SocialPredict — Open Prediction Markets |
| Repositório | https://github.com/openpredictionmarkets/socialpredict |
| Arquivo estudado | `backend/internal/domain/math/probabilities/wpam/wpam_marketprobabilities.go` |
| Commit upstream | `3d978faac6b3391d5b6a9af4aa37a283d48699a7` |
| Licença de origem | **MIT** — © 2024 Open Prediction Markets |
| Data | 2026-08-17 |

## O que foi absorvido

A **estrutura** do Weighted Probability Adjustment Model: uma média ponderada com
pseudo-contagem, em que o prior neutro (`p_inicial = 0.5`) é ponderado por um
peso inicial (`I_inicial`) que aparece no numerador e no denominador, dando
estabilidade ao início e resistência a movimentos com pouca evidência.

Fórmula:

    p = (p_inicial · peso_inicial + peso_sim) / (peso_inicial + peso_sim + peso_nao)

## O que NÃO foi copiado

Nenhuma linha de código foi copiada. A implementação em
`src/asus_theye/markets/gerador.py` é **original em Python**, reescrita do zero,
e **adaptada de contexto**: no SocialPredict o `A_YES`/`A_NO` são apostas de
usuários; aqui são **sinais de evidência com fonte nomeada**, e o modelo só
move a probabilidade do prior quando há evidência medida — preservando a
doutrina "UNKNOWN over guess" do projeto (sem sinal → p = 0,50 → máxima
incerteza).

A fórmula matemática em si (média ponderada estilo Laplace/Beta com
pseudo-contagem) é de domínio público. O crédito à origem é mantido no docstring
do módulo e neste registro, cumprindo a licença MIT (que exige preservar o aviso
de copyright, não a cópia do código).

## Situação de licença

- Código do projeto: AGPL-3.0-or-later (© 2026 Mateus Menezes Figueiredo).
- Ideia/estrutura estudada: MIT — o aviso de origem é preservado aqui e no
  módulo. A incorporação é permitida pela MIT; o produto derivado é do titular.
