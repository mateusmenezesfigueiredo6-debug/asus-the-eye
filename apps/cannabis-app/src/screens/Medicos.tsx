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
      <Text style={s.rotulo}>CORPO CLINICO</Text>
      <Text style={s.h1}>Prescreva com estrutura, sem conflito</Text>
      <Text style={s.lead}>
        Buscamos medicos com CRM ativo, sem exclusividade com outras
        plataformas, para o corpo clinico da Gota Verde.
      </Text>
      <Text style={s.secao}>MODELOS DE REMUNERACAO</Text>
      <View style={s.grupo}>
        {MODELOS.map(([t, d], i) => (
          <View
            key={t}
            style={[s.item, i === MODELOS.length - 1 && s.itemUltimo]}
          >
            <Text style={s.itemTitulo}>{t}</Text>
            <Text style={s.p}>{d}</Text>
          </View>
        ))}
      </View>
      <View style={s.etica}>
        <Text style={s.eticaRotulo}>COMPROMISSO ETICO</Text>
        <Text style={s.eticaTexto}>
          NAO pagamos comissao por prescricao, por paciente encaminhado
          ou por volume de receita. Isso e vedado pelo Codigo de Etica
          Medica.
        </Text>
      </View>
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
  pad: { padding: 24, paddingBottom: 48 },
  rotulo: { color: CORES.sage, fontSize: 11, letterSpacing: 3,
    fontWeight: "600", marginBottom: 8 },
  h1: { color: CORES.ink, fontSize: 26, lineHeight: 34,
    fontWeight: "600", marginBottom: 12 },
  lead: { color: CORES.dim, fontSize: 15, lineHeight: 23,
    marginBottom: 24 },
  secao: { color: CORES.sage, fontSize: 11, letterSpacing: 3,
    fontWeight: "600", marginBottom: 10 },
  grupo: { backgroundColor: CORES.card, borderWidth: 1,
    borderColor: CORES.line, borderRadius: 6 },
  item: { padding: 20, borderBottomWidth: 1,
    borderBottomColor: CORES.line },
  itemUltimo: { borderBottomWidth: 0 },
  itemTitulo: { color: CORES.ink, fontSize: 16, fontWeight: "600",
    marginBottom: 4 },
  p: { color: CORES.dim, fontSize: 14, lineHeight: 21 },
  etica: { backgroundColor: CORES.card, borderWidth: 1,
    borderColor: CORES.line, borderLeftWidth: 3,
    borderLeftColor: CORES.verde, borderRadius: 6, padding: 18,
    marginTop: 22 },
  eticaRotulo: { color: CORES.verde, fontSize: 10, letterSpacing: 3,
    fontWeight: "600", marginBottom: 6 },
  eticaTexto: { color: CORES.dim, fontSize: 14, lineHeight: 21 },
  botao: { backgroundColor: CORES.verde, padding: 16, marginTop: 26,
    borderRadius: 4 },
  botaoTexto: { color: "#ffffff", textAlign: "center", letterSpacing: 3,
    fontSize: 12, fontWeight: "600" },
});
