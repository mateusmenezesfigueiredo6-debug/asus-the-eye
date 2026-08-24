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
        <Text style={s.aviso}>
          Catalogo FICTICIO para apresentacao. Nomes, formulas e precos
          inventados. Nenhum item esta a venda.
        </Text>
      }
      renderItem={({ item }) => (
        <View style={s.card}>
          <Text style={s.tipo}>{item.tipo.toUpperCase()}</Text>
          <Text style={s.nome}>{item.nome}</Text>
          <Text style={s.desc}>{item.spec}</Text>
          <Text style={s.desc}>{item.desc}</Text>
          <Text style={s.preco}>{item.preco}</Text>
          <Text style={s.selo}>PRODUTO DEMONSTRATIVO — NAO E OFERTA</Text>
        </View>
      )}
    />
  );
}

const s = StyleSheet.create({
  fundo: { flex: 1, backgroundColor: CORES.bg },
  pad: { padding: 22 },
  aviso: { color: CORES.gold, fontSize: 12, lineHeight: 18,
    marginBottom: 14 },
  card: { backgroundColor: CORES.panel, borderWidth: 1,
    borderColor: CORES.line, borderRadius: 4, padding: 18,
    marginBottom: 14 },
  tipo: { color: CORES.gold, fontSize: 10, letterSpacing: 3 },
  nome: { color: CORES.ink, fontSize: 20, marginVertical: 4 },
  desc: { color: CORES.dim, fontSize: 13, lineHeight: 19 },
  preco: { color: CORES.gold2, fontSize: 16, marginTop: 8 },
  selo: { color: CORES.gold, fontSize: 9, letterSpacing: 2,
    marginTop: 10, borderWidth: 1, borderColor: CORES.gold,
    borderStyle: "dashed", alignSelf: "flex-start",
    paddingHorizontal: 7, paddingVertical: 2 },
});
