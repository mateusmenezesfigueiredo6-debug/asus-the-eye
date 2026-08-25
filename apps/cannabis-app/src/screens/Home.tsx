// SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
// SPDX-License-Identifier: AGPL-3.0-or-later

import React from "react";
import { ScrollView, Text, View, StyleSheet } from "react-native";
import { CORES } from "../tema";

export function HomeScreen() {
  return (
    <ScrollView style={s.fundo} contentContainerStyle={s.pad}>
      <Text style={s.badge}>APRESENTACAO — DADOS ILUSTRATIVOS</Text>
      <Text style={s.h1}>Cannabis medicinal com prova, nao com promessa.</Text>
      <Text style={s.p}>
        A Gota Verde esta sendo construida sobre uma tese simples: quem
        provar origem, pureza e dispensacao correta — com evidencia que
        ninguem consegue reescrever — define o padrao do mercado.
      </Text>
      {[
        ["Rastreabilidade", "Da semente ao frasco, encadeada por hash."],
        ["Dispensacao condicionada", "Sem prescricao valida, nao libera."],
        ["Farmacovigilancia", "Evento adverso vira registro permanente."],
        ["Honestidade", "Nenhum numero publicado sem metodo e fonte."],
      ].map(([t, d]) => (
        <View key={t} style={s.card}>
          <Text style={s.cardTitulo}>{t}</Text>
          <Text style={s.p}>{d}</Text>
        </View>
      ))}
      <Text style={s.rodape}>
        Fase atual: apresentacao. Nao ha operacao comercial, estoque ou
        venda. Produtos a base de cannabis exigem prescricao medica.
      </Text>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  fundo: { flex: 1, backgroundColor: CORES.bg },
  pad: { padding: 22 },
  badge: { color: CORES.gold, fontSize: 10, letterSpacing: 3,
    marginBottom: 14 },
  h1: { color: CORES.ink, fontSize: 26, lineHeight: 34,
    marginBottom: 12 },
  p: { color: CORES.dim, fontSize: 14, lineHeight: 21 },
  card: { backgroundColor: CORES.panel, borderWidth: 1,
    borderColor: CORES.line, borderRadius: 4, padding: 16,
    marginTop: 14 },
  cardTitulo: { color: CORES.gold2, fontSize: 15, marginBottom: 4 },
  rodape: { color: CORES.dim, fontSize: 11, marginTop: 24,
    lineHeight: 17 },
});
