// SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
// SPDX-License-Identifier: AGPL-3.0-or-later

import React from "react";
import { ScrollView, Text, View, StyleSheet } from "react-native";
import { CORES } from "../tema";

const PILARES: Array<[string, string]> = [
  ["Rastreabilidade", "Da semente ao frasco, encadeada por hash."],
  ["Dispensacao condicionada", "Sem prescricao valida, nao libera."],
  ["Farmacovigilancia", "Evento adverso vira registro permanente."],
  ["Honestidade", "Nenhum numero publicado sem metodo e fonte."],
];

export function HomeScreen() {
  return (
    <ScrollView style={s.fundo} contentContainerStyle={s.pad}>
      <View style={s.faixa}>
        <Text style={s.faixaTexto}>
          APRESENTACAO — DADOS ILUSTRATIVOS
        </Text>
      </View>
      <Text style={s.h1}>
        Cannabis medicinal com prova, nao com promessa.
      </Text>
      <Text style={s.lead}>
        A Gota Verde esta sendo construida sobre uma tese simples: quem
        provar origem, pureza e dispensacao correta — com evidencia que
        ninguem consegue reescrever — define o padrao do mercado.
      </Text>
      <View style={s.divisor} />
      <Text style={s.secao}>OS QUATRO PILARES</Text>
      {PILARES.map(([t, d], i) => (
        <View key={t} style={s.card}>
          <View style={s.cardTopo}>
            <Text style={s.num}>{String(i + 1).padStart(2, "0")}</Text>
            <Text style={s.cardTitulo}>{t}</Text>
          </View>
          <Text style={s.p}>{d}</Text>
        </View>
      ))}
      <View style={s.rodapeCaixa}>
        <Text style={s.rodapeRotulo}>FASE ATUAL</Text>
        <Text style={s.rodape}>
          Apresentacao. Nao ha operacao comercial, estoque ou venda.
          Produtos a base de cannabis exigem prescricao medica.
        </Text>
      </View>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  fundo: { flex: 1, backgroundColor: CORES.bg },
  pad: { padding: 24, paddingBottom: 48 },
  faixa: { alignSelf: "flex-start", borderWidth: 1,
    borderColor: CORES.verde, borderRadius: 3,
    paddingHorizontal: 10, paddingVertical: 5, marginBottom: 18 },
  faixaTexto: { color: CORES.verde, fontSize: 10, letterSpacing: 2,
    fontWeight: "600" },
  h1: { color: CORES.ink, fontSize: 28, lineHeight: 36,
    fontWeight: "600", marginBottom: 14 },
  lead: { color: CORES.dim, fontSize: 15, lineHeight: 24 },
  divisor: { height: 1, backgroundColor: CORES.line,
    marginVertical: 26 },
  secao: { color: CORES.sage, fontSize: 11, letterSpacing: 3,
    fontWeight: "600", marginBottom: 4 },
  card: { backgroundColor: CORES.card, borderWidth: 1,
    borderColor: CORES.line, borderRadius: 6, padding: 20,
    marginTop: 14 },
  cardTopo: { flexDirection: "row", alignItems: "baseline",
    gap: 12, marginBottom: 6 },
  num: { color: CORES.verde, fontSize: 13, fontWeight: "600",
    letterSpacing: 1 },
  cardTitulo: { color: CORES.ink, fontSize: 16, fontWeight: "600",
    flex: 1 },
  p: { color: CORES.dim, fontSize: 14, lineHeight: 21 },
  rodapeCaixa: { backgroundColor: CORES.card, borderWidth: 1,
    borderColor: CORES.line, borderLeftWidth: 3,
    borderLeftColor: CORES.verde, borderRadius: 6, padding: 18,
    marginTop: 26 },
  rodapeRotulo: { color: CORES.verde, fontSize: 10, letterSpacing: 3,
    fontWeight: "600", marginBottom: 6 },
  rodape: { color: CORES.dim, fontSize: 13, lineHeight: 20 },
});
