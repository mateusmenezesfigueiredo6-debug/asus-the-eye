# RECRUTAMENTO DE MEDICOS PRESCRITORES — ESTRATEGIA E TEMPLATES

Vertical cannabis (marca de trabalho: Cinala Verde). Documento operacional.

## Limite etico inegociavel

**E vedado pagar por prescricao.** O Codigo de Etica Medica proibe ao medico
receber comissao, vantagem ou remuneracao vinculada a prescricao, encaminhamento
ou volume de receitas. Qualquer modelo "por receita" expoe o CRM do medico a
processo etico e a empresa a responsabilizacao. Nenhum material, contrato ou
conversa deste funil pode conter remuneracao por prescricao. Os modelos abaixo
sao os licitos.

## Modelos de remuneracao (todos licitos)

| Modelo | Como funciona | Quando usar |
|---|---|---|
| Pagamento por consulta | Medico define o valor; recebe por atendimento realizado na plataforma; agenda, telemedicina e recepcao por nossa conta | Padrao de mercado; escala bem |
| Hora clinica | Blocos de horas de disponibilidade pagos por hora | Ambulatorio proprio, mutiroes |
| Retainer mensal | Valor fixo por disponibilidade minima mensal | Medicos ancora, especialidades raras |
| Conselho cientifico | Remuneracao por reuniao ou por projeto de P&D | Nomes de referencia, publicacoes |

## Perfil-alvo e triagem

1. CRM ativo (verificar em portal.cfm.org.br/busca-medicos) e RQE quando
   anunciar especialidade.
2. Sem exclusividade contratual com plataformas concorrentes (perguntar
   formalmente; registrar a resposta).
3. Prioridade: neurologia, psiquiatria, geriatria, medicina da dor, pediatria
   (epilepsias refratarias), clinica geral com formacao canabinoide.
4. Interesse em telemedicina (Resolucao CFM 2.314/2022 permite atender o pais
   inteiro).

## Canais e cadencia

Sequencia por lead: Email 1 -> (3 dias) Email 2 -> (4 dias) WhatsApp 1 ->
(5 dias) SMS 1 -> (7 dias) Email 3 (ultimo). Parar imediatamente ao receber
opt-out em qualquer canal.

Regras LGPD e anti-spam:

- Base legal documentada por lead (legitimo interesse para contato profissional
  B2B usando dado profissional publico; consentimento a partir do cadastro).
- Todo email com rodape de descadastro funcional; SMS com "PARE p/ sair";
  WhatsApp somente via API oficial do WhatsApp Business com template aprovado —
  nunca disparo em massa por numero comum (banimento e multa).
- Registrar data, fonte do contato e opt-outs em planilha unica.

## Templates

### Email 1 — apresentacao

Assunto: Corpo clinico [MARCA] — prescricao de cannabis com estrutura

Dr(a). [NOME],

Somos a [MARCA], plataforma em formacao de cannabis medicinal com
rastreabilidade auditavel (laudo por lote, dispensacao condicionada a
prescricao valida, farmacovigilancia ativa). Estamos convidando um grupo
inicial de medicos com CRM ativo para compor o corpo clinico.

Modelos de parceria: pagamento por consulta (valor definido pelo proprio
medico), hora clinica ou retainer mensal. Nao trabalhamos com qualquer
remuneracao vinculada a prescricao — isso e vedado pelo CEM e pela nossa
politica.

Teria 20 minutos esta semana para uma conversa?

[ASSINATURA]
[Para nao receber mais mensagens, responda SAIR.]

### Email 2 — follow-up (3 dias)

Assunto: Re: Corpo clinico [MARCA]

Dr(a). [NOME], retomando o convite. Enviamos abaixo o material de
apresentacao com os modelos de remuneracao e a minuta de contrato. Se
preferir, indico dois horarios: [OPCAO A] ou [OPCAO B].
[ASSINATURA] [rodape de descadastro]

### Email 3 — encerramento (ultimo contato)

Assunto: Encerrando o convite — [MARCA]

Dr(a). [NOME], este e nosso ultimo contato sobre o convite ao corpo
clinico. Se houver interesse futuro, a porta segue aberta em
[EMAIL/LINK]. Obrigado pelo tempo. [ASSINATURA]

### WhatsApp 1 (template Business API)

Ola, Dr(a). {{1}}. Aqui e {{2}}, da [MARCA]. Enviamos por email um convite
para nosso corpo clinico de cannabis medicinal (remuneracao por consulta,
hora clinica ou retainer — nunca por prescricao). Posso enviar o material
por aqui? Responda SAIR para nao receber mais mensagens.

### WhatsApp 2 — agendamento

Dr(a). {{1}}, segue o link da agenda para a conversa de 20 min: {{2}}.
Qualquer horario ali funciona. Responda SAIR para nao receber mais
mensagens.

### SMS 1

[MARCA]: convite ao corpo clinico de cannabis medicinal. Remuneracao por
consulta/hora, nunca por prescricao. Detalhes: [LINK]. PARE p/ sair.

### SMS 2 — lembrete

[MARCA]: Dr(a). [SOBRENOME], seu acesso ao material do corpo clinico
expira em 7 dias: [LINK]. PARE p/ sair.

## Metricas do funil

Acompanhar por coorte semanal: contatados -> respondidos -> reuniao ->
contrato assinado -> primeira consulta realizada. Meta inicial honesta: nao
ha benchmark proprio ainda; medir 4 semanas antes de fixar metas.

## Ferramentas previstas

- Email: qualquer ESP com opt-out automatico (ex.: Brevo, Mailchimp).
- WhatsApp: API oficial WhatsApp Business (BSP: Twilio, Zenvia, Gupshup).
- SMS: Twilio/Zenvia.
- CRM comercial simples (Pipedrive/Notion) ate a plataforma propria existir.
