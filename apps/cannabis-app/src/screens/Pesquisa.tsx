// SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
// SPDX-License-Identifier: AGPL-3.0-or-later

import React from "react";
import { ScrollView, Text, View, StyleSheet } from "react-native";
import { CORES } from "../tema";

const LINHAS: Array<[string, string]> = [
  ["Evidencia de mundo real",
   "Registro longitudinal anonimizado de desfechos relatados por " +
   "pacientes, com consentimento e LGPD."],
  ["Estabilidade e formulacao",
   "Curvas de degradacao por matriz; validade dita pelo dado."],
  ["Farmacovigilancia computacional",
   "Deteccao de sinal de evento adverso sobre a base de notificacoes."],
  ["Genetica e cultivo (fase judicial)",
   "Banco de quimiotipos; so avanca com autorizacao judicial."],
  ["Economia do acesso",
   "Custo real por miligrama por via de acesso, publicado com metodo."],
];

export function PesquisaScreen() {
  return (
    <ScrollView style={s.fundo} contentContainerStyle={s.pad}>
      <Text style={s.h1}>P&D: a vantagem que nao se copia</Text>
      <Text style={s.p}>
        Produto se imita em seis meses. O que nao se imita e um corpo de
        evidencia proprio. Cada linha abaixo passa por protocolo etico
        (CEP/CONEP) antes de tocar dado de paciente.
      </Text>
      {LINHAS.map(([t, d], i) => (
        <View key={t} style={s.card}>
          <Text style={s.num}>{String(i + 1).padStart(2, "0")}</Text>
          <View style={s.corpo}>
            <Text style={s.cardTitulo}>{t}</Text>
            <Text style={s.p}>{d}</Text>
          </View>
        </View>
      ))}
      <Text style={s.rodape}>
        Regra de honestidade: se o dado mostrar que uma formulacao nao
        supera a alternativa mais simples, publicamos assim mesmo.
      </Text>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  fundo: { flex: 1, backgroundColor: CORES.bg },
  pad: { padding: 22 },
  h1: { color: CORES.ink, fontSize: 24, lineHeight: 32,
    marginBottom: 10 },
  p: { color: CORES.dim, fontSize: 14, lineHeight: 21 },
  card: { flexDirection: "row", gap: 14, backgroundColor: CORES.panel,
    borderWidth: 1, borderColor: CORES.line, borderRadius: 4,
    padding: 16, marginTop: 14 },
  num: { color: CORES.gold, fontSize: 18 },
  corpo: { flex: 1 },
  cardTitulo: { color: CORES.gold2, fontSize: 15, marginBottom: 4 },
  rodape: { color: CORES.gold, fontSize: 12, marginTop: 22,
    lineHeight: 18 },
});
