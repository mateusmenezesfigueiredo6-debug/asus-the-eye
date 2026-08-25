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
      <Text style={s.rotulo}>PESQUISA E DESENVOLVIMENTO</Text>
      <Text style={s.h1}>A vantagem que nao se copia</Text>
      <Text style={s.lead}>
        Produto se imita em seis meses. O que nao se imita e um corpo de
        evidencia proprio. Cada linha abaixo passa por protocolo etico
        (CEP/CONEP) antes de tocar dado de paciente.
      </Text>
      <View style={s.lista}>
        {LINHAS.map(([t, d], i) => (
          <View
            key={t}
            style={[s.item, i === LINHAS.length - 1 && s.itemUltimo]}
          >
            <View style={s.numCaixa}>
              <Text style={s.num}>{String(i + 1).padStart(2, "0")}</Text>
            </View>
            <View style={s.corpo}>
              <Text style={s.itemTitulo}>{t}</Text>
              <Text style={s.p}>{d}</Text>
            </View>
          </View>
        ))}
      </View>
      <View style={s.regra}>
        <Text style={s.regraRotulo}>REGRA DE HONESTIDADE</Text>
        <Text style={s.regraTexto}>
          Se o dado mostrar que uma formulacao nao supera a alternativa
          mais simples, publicamos assim mesmo.
        </Text>
      </View>
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
  lista: { backgroundColor: CORES.card, borderWidth: 1,
    borderColor: CORES.line, borderRadius: 6 },
  item: { flexDirection: "row", gap: 16, padding: 20,
    borderBottomWidth: 1, borderBottomColor: CORES.line },
  itemUltimo: { borderBottomWidth: 0 },
  numCaixa: { width: 34, height: 34, borderRadius: 17,
    borderWidth: 1, borderColor: CORES.verde,
    alignItems: "center", justifyContent: "center" },
  num: { color: CORES.verde, fontSize: 12, fontWeight: "600" },
  corpo: { flex: 1 },
  itemTitulo: { color: CORES.ink, fontSize: 16, fontWeight: "600",
    marginBottom: 4 },
  p: { color: CORES.dim, fontSize: 14, lineHeight: 21 },
  regra: { backgroundColor: CORES.verde, borderRadius: 6,
    padding: 20, marginTop: 24 },
  regraRotulo: { color: "#ffffff", fontSize: 10, letterSpacing: 3,
    fontWeight: "600", opacity: 0.8, marginBottom: 6 },
  regraTexto: { color: "#ffffff", fontSize: 14, lineHeight: 21 },
});
