// SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
// SPDX-License-Identifier: AGPL-3.0-or-later

import React from "react";
import { ScrollView, Text, View, StyleSheet, Linking, Pressable }
  from "react-native";
import { CORES } from "../tema";

const MODELOS: Array<[string, string]> = [
  ["Pagamento por consulta",
   "O medico define o valor e recebe por atendimento realizado."],
  ["Hora clinica / retainer",
   "Blocos de horas ou valor mensal fixo por disponibilidade."],
  ["Conselho cientifico",
   "Remuneracao por reuniao ou projeto de P&D."],
];

export function MedicosScreen() {
  return (
    <ScrollView style={s.fundo} contentContainerStyle={s.pad}>
      <Text style={s.h1}>Prescreva com estrutura, sem conflito</Text>
      <Text style={s.p}>
        Buscamos medicos com CRM ativo, sem exclusividade com outras
        plataformas, para o corpo clinico da Cinala Verde.
      </Text>
      {MODELOS.map(([t, d]) => (
        <View key={t} style={s.card}>
          <Text style={s.cardTitulo}>{t}</Text>
          <Text style={s.p}>{d}</Text>
        </View>
      ))}
      <Text style={s.etica}>
        Compromisso etico: NAO pagamos comissao por prescricao, por
        paciente encaminhado ou por volume de receita. Isso e vedado pelo
        Codigo de Etica Medica.
      </Text>
      <Pressable
        style={s.botao}
        onPress={() =>
          Linking.openURL(
            "mailto:medicos@example.invalid?subject=Interesse%20corpo%20clinico",
          )
        }
      >
        <Text style={s.botaoTexto}>MANIFESTAR INTERESSE</Text>
      </Pressable>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  fundo: { flex: 1, backgroundColor: CORES.bg },
  pad: { padding: 22 },
  h1: { color: CORES.ink, fontSize: 24, lineHeight: 32,
    marginBottom: 10 },
  p: { color: CORES.dim, fontSize: 14, lineHeight: 21 },
  card: { backgroundColor: CORES.panel, borderWidth: 1,
    borderColor: CORES.line, borderRadius: 4, padding: 16,
    marginTop: 14 },
  cardTitulo: { color: CORES.gold2, fontSize: 15, marginBottom: 4 },
  etica: { color: CORES.gold, fontSize: 13, lineHeight: 20,
    marginTop: 20, borderLeftWidth: 2, borderLeftColor: CORES.gold,
    paddingLeft: 12 },
  botao: { backgroundColor: CORES.gold, padding: 14, marginTop: 24,
    borderRadius: 2 },
  botaoTexto: { color: "#14100a", textAlign: "center", letterSpacing: 3,
    fontSize: 12, fontWeight: "600" },
});
