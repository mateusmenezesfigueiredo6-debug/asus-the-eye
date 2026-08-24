# ROTEIRO DE DEMONSTRACAO PARA SOCIOS — CINALA VERDE

Como apresentar o site, o deck e o app numa reuniao com socios ou
investidores. Atualizado em 24/08/2026.

## Antes da reuniao (checklist)

1. Regerar o site: `python src/asus_theye/dashboard/cannabis_demo.py
   dist-cannabis`.
2. Se o Worker ainda nao foi publicado: seguir
   `apps/cannabis-demo/PUBLICAR.md` (secrets + `wrangler deploy`). URL
   final: `cannabis-demo.<conta>.workers.dev`.
3. Guardar o codigo de acesso do site para passar aos socios na hora
   (nao enviar por escrito antes; o material e restrito).
4. Testar a URL num celular e num notebook.
5. Deck PPTX (`DECK_INVESTIDORES_CINALA.pptx`) aberto como reserva
   offline, caso a internet falhe.

## Roteiro sugerido (20 minutos)

| Min | O que mostrar | Mensagem |
|---|---|---|
| 0-2 | Tela de codigo do site | "Nada aqui e publico; ate a apresentacao e auditada" |
| 2-8 | `deck.html` (setas do teclado) | A narrativa completa: problema, tese, travas, P&D, modelo, regulatorio, roadmap |
| 8-12 | Aba Produtos | A vitrine com selo DEMONSTRATIVO: mostra ambicao sem prometer o que nao existe |
| 12-15 | Aba P&D | O fosso: evidencia propria, publicacao aberta |
| 15-17 | Aba Para medicos | O funil e o compromisso etico (nunca comissao por prescricao) |
| 17-20 | App no celular | Mesmo conteudo, experiencia nativa; PWA instala na hora |

## Demonstrar o app

Opcao rapida (sem loja, qualquer celular):

1. No site aberto no celular, usar "Adicionar a tela inicial" — o PWA
   instala e abre como app.

Opcao nativa (Expo Go, para mostrar o app das lojas):

1. Na maquina: `cd apps/cannabis-app && npm install && npx expo start`.
2. No celular: instalar o app "Expo Go" (gratuito) e escanear o QR do
   terminal.
3. Codigo de acesso do app demo: `cinala2026` (trocavel via
   `EXPO_PUBLIC_ACCESS_CODE`).

## Perguntas que socios fazem (e as respostas honestas)

- "Quanto ja fatura?" — Nada; fase de apresentacao. Nao publicamos
  projecao sem metodo; o deck diz isso explicitamente.
- "E legal?" — O slide Regulatorio mostra a linha: operamos nas vias RDC
  660/327, telemedicina CFM 2.314 e, para cultivo, so com autorizacao
  judicial.
- "Por que voces e nao um concorrente?" — Auditabilidade herdada do THE
  EYE: laudo, prescricao e dispensacao em cadeia de hash publica.
- "Posso levar o material?" — O PPTX pode ser enviado apos a reuniao com
  marca de confidencialidade; o site fica atras do codigo.
