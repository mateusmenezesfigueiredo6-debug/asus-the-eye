# Vertical cannabis — indice dos artefatos

Vertical comercial de cannabis medicinal (marca de trabalho: Cinala
Verde). Fase: apresentacao e estruturacao. Nada aqui e operacao
comercial.

## Documentos (cada .md tem o .docx correspondente)

- `ESTATUTO_SOCIAL_ASSOCIACAO_CANNABIS.md` — estatuto completo da
  associacao, cargos em branco, pronto para assinar.
- `ROTEIRO_TRAMITES_E_INSTITUICOES.md` — passo a passo burocratico e
  instituicoes (cartorio, CNPJ, ANVISA, via judicial de cultivo).
- `CENTRAIS_E_MEDICOS_PRESCRITORES_CBD_BRASIL.md` — levantamento das
  plataformas e associacoes que conectam pacientes a prescritores.
- `RECRUTAMENTO_MEDICOS_PRESCRITORES.md` — funil de recrutamento de CRMs
  com modelos licitos e templates de email/WhatsApp/SMS.
- `SKILLS_E_FERRAMENTAS.md` — as 30 skills/MCPs mais uteis ao vertical.
- `DECK_INVESTIDORES_CINALA.pptx` — deck de investidores (14 slides,
  tema da marca); versao HTML gemea em `dist-cannabis/deck.html`.
- `DEMO_SOCIOS.md` — roteiro de demonstracao do site, deck e app para
  reunioes com socios.

## Codigo

- `src/asus_theye/dashboard/cannabis_demo.py` — gerador do site de
  apresentacao (exporta para `dist-cannabis/`; PWA instalavel).
- `apps/cannabis-demo/` — Worker Cloudflare com gate por codigo de
  acesso + runbook de publicacao (`PUBLICAR.md`).
- `apps/cannabis-app/` — app Expo (React Native) para App Store e Play
  Store + runbook (`PUBLICACAO_LOJAS.md`).

## Regras que valem em tudo

1. Nenhum pagamento por prescricao (vedado pelo CEM).
2. Produtos e precos exibidos sao FICTICIOS e marcados como tal ate
   existir operacao licenciada.
3. Deploy e submissao a lojas passam pelo dono (publish lock; contas
   Apple/Google).
