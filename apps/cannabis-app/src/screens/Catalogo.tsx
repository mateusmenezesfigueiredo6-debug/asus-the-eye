// SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
// SPDX-License-Identifier: AGPL-3.0-or-later

import React from "react";
import { FlatList, Text, View, StyleSheet } from "react-native";
import { CORES, PRODUTOS } from "../tema";

export function CatalogoScreen() {
  return (
    <FlatList
      style={s.fundo}
      contentContainerStyle={s.pad}
      data={PRODUTOS}
      keyExtractor={(p) => p.nome}
      ListHeaderComponent={
        <View style={s.aviso}>
          <Text style={s.avisoRotulo}>CATALOGO FICTICIO</Text>
          <Text style={s.avisoTexto}>
            Material de apresentacao. Nomes, formulas e precos
            inventados. Nenhum item esta a venda.
          </Text>
        </View>
      }
      renderItem={({ item }) => (
        <View style={s.card}>
          <View style={s.linhaTopo}>
            <Text style={s.tipo}>{item.tipo.toUpperCase()}</Text>
            <Text style={s.preco}>{item.preco}</Text>
          </View>
          <Text style={s.nome}>{item.nome}</Text>
          <Text style={s.spec}>{item.spec}</Text>
          <View style={s.separador} />
          <Text style={s.desc}>{item.desc}</Text>
          <Text style={s.selo}>DEMONSTRATIVO — NAO E OFERTA</Text>
        </View>
      )}
    />
  );
}

const s = StyleSheet.create({
  fundo: { flex: 1, backgroundColor: CORES.bg },
  pad: { padding: 24, paddingBottom: 48 },
  aviso: { backgroundColor: CORES.card, borderWidth: 1,
    borderColor: CORES.line, borderLeftWidth: 3,
    borderLeftColor: CORES.verde, borderRadius: 6, padding: 16,
    marginBottom: 18 },
  avisoRotulo: { color: CORES.verde, fontSize: 10, letterSpacing: 3,
    fontWeight: "600", marginBottom: 6 },
  avisoTexto: { color: CORES.dim, fontSize: 13, lineHeight: 20 },
  card: { backgroundColor: CORES.card, borderWidth: 1,
    borderColor: CORES.line, borderRadius: 6, padding: 20,
    marginBottom: 14 },
  linhaTopo: { flexDirection: "row", justifyContent: "space-between",
    alignItems: "center", marginBottom: 8 },
  tipo: { color: CORES.sage, fontSize: 10, letterSpacing: 2,
    fontWeight: "600" },
  preco: { color: CORES.verde, fontSize: 13, fontWeight: "600" },
  nome: { color: CORES.ink, fontSize: 19, fontWeight: "600" },
  spec: { color: CORES.dim, fontSize: 13, marginTop: 3 },
  separador: { height: 1, backgroundColor: CORES.line,
    marginVertical: 12 },
  desc: { color: CORES.dim, fontSize: 14, lineHeight: 21 },
  selo: { color: CORES.sage, fontSize: 9, letterSpacing: 2,
    marginTop: 12, borderWidth: 1, borderColor: CORES.line,
    borderRadius: 3, alignSelf: "flex-start",
    paddingHorizontal: 8, paddingVertical: 3 },
});
