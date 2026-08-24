# Publicar o app Cinala Verde nas lojas (App Store e Google Play)

Scaffold Expo (React Native + TypeScript) em `apps/cannabis-app/`. O
codigo compila localmente; a submissao as lojas depende de contas que so
o dono pode criar.

## Bloqueios externos (acao do dono)

1. **Apple Developer Program** — USD 99/ano — developer.apple.com.
   Exige Apple ID com 2FA; aprovacao leva 1-2 dias.
2. **Google Play Console** — USD 25 (taxa unica) — play.google.com/console.
   Exige verificacao de identidade; contas novas precisam de teste
   fechado com 12+ testadores por 14 dias antes de producao.
3. Conta Expo (gratuita) para o EAS Build: expo.dev.

## Passo a passo

    cd apps/cannabis-app
    npm install
    npm run typecheck          # sanidade
    npx expo start             # teste local no Expo Go

    npm install -g eas-cli
    eas login
    eas build:configure        # gera eas.json
    eas build -p android --profile production   # .aab para o Play
    eas build -p ios --profile production       # .ipa para a App Store
    eas submit -p android      # envia ao Play Console
    eas submit -p ios          # envia ao App Store Connect

## Revisao das lojas — pontos criticos para um app de cannabis

- **Apple (guideline 1.4.3)**: apps de cannabis so passam com operacao
  legal comprovada e restricao geografica; um app INFORMATIVO (sem venda,
  sem pedido) como este tem caminho muito mais simples. Nao incluir
  botao de compra.
- **Google Play**: proibe facilitar VENDA de cannabis (pedido, carrinho,
  entrega). Conteudo informativo/educacional e permitido. Manter o app
  sem qualquer fluxo de compra ate haver operacao licenciada e parecer
  juridico.
- Marcar classificacao etaria 18+ nos dois consoles.
- Politica de privacidade publicada em URL propria e preenchida nos dois
  consoles (obrigatoria mesmo sem coleta de dados).

## Codigo de acesso

A tela de gate usa `EXPO_PUBLIC_ACCESS_CODE` (padrao de build:
`cinala2026`). Para trocar: definir a variavel no `eas.json` ou no
ambiente de build. E um controle de apresentacao, nao um segredo forte —
o conteudo do app e demonstrativo.
