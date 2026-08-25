// SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
// SPDX-License-Identifier: AGPL-3.0-or-later
// Painel admin de disparos: convites a medicos e empresas via o mesmo
// Worker do site (/api/outreach), com opt-out e lista de supressao.

import React, { useState } from "react";
import { ScrollView, Text, TextInput, View, Pressable, StyleSheet,
  Switch } from "react-native";
import { CORES } from "../tema";

const API = process.env.EXPO_PUBLIC_API_URL ?? "";

export function DisparosScreen() {
  const [lista, setLista] = useState("");
  const [baseLegal, setBaseLegal] = useState(false);
  const [status, setStatus] = useState("");
  const disparar = async () => {
    if (!baseLegal) {
      setStatus("Confirme a base legal da lista antes de disparar.");
      return;
    }
    const dest = lista
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean)
      .map((l) => {
        const p = l.split(";");
        return {
          nome: (p[0] ?? "").trim(),
          email: (p[1] ?? "").trim(),
          crm: (p[2] ?? "").trim(),
          tipo: (p[3] ?? "medico").trim(),
        };
      })
      .filter((d) => d.email.includes("@"));
    if (!dest.length) {
      setStatus("Nenhum email valido na lista.");
      return;
    }
    setStatus(`Enviando ${dest.length} convites...`);
    try {
      const r = await fetch(`${API}/api/outreach`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ destinatarios: dest }),
      });
      const j = await r.json();
      setStatus(
        j.configurado
          ? `Enviados: ${j.enviados} | pulados (opt-out): ${j.suprimidos}`
          : `Lote validado (${j.total}). Envio ativa no deploy.`,
      );
    } catch {
      setStatus(`Lote validado localmente (${dest.length} contatos).`);
    }
  };
  return (
    <ScrollView style={s.fundo} contentContainerStyle={s.pad}>
      <Text style={s.rotulo}>PAINEL ADMINISTRATIVO</Text>
      <Text style={s.h1}>Disparos a medicos e empresas</Text>
      <Text style={s.lead}>
        Template oficial do funil, com descadastro automatico. Maximo
        100 por lote.
      </Text>
      <View style={s.grupo}>
        <Text style={s.grupoTitulo}>LISTA DE CONTATOS</Text>
        <Text style={s.dica}>
          Uma linha por contato: nome;email;crm;tipo (medico ou
          empresa).
        </Text>
        <TextInput
          style={s.area}
          multiline
          numberOfLines={8}
          placeholder="Maria Silva;maria@exemplo.com;123456;medico"
          placeholderTextColor={CORES.sage}
          value={lista}
          onChangeText={setLista}
        />
      </View>
      <View style={s.consentimento}>
        <Switch
          value={baseLegal}
          onValueChange={setBaseLegal}
          trackColor={{ false: CORES.line, true: CORES.sage }}
          thumbColor={baseLegal ? CORES.verde : "#ffffff"}
        />
        <Text style={s.consentimentoTexto}>
          Declaro que a lista tem base legal (LGPD) e respeita
          descadastros anteriores.
        </Text>
      </View>
      <Pressable style={s.botao} onPress={disparar}>
        <Text style={s.botaoTexto}>DISPARAR</Text>
      </Pressable>
      {status ? <Text style={s.status}>{status}</Text> : null}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  fundo: { flex: 1, backgroundColor: CORES.bg },
  pad: { padding: 24, paddingBottom: 64 },
  rotulo: { color: CORES.sage, fontSize: 11, letterSpacing: 3,
    fontWeight: "600", marginBottom: 8 },
  h1: { color: CORES.ink, fontSize: 26, lineHeight: 34,
    fontWeight: "600", marginBottom: 12 },
  lead: { color: CORES.dim, fontSize: 14, lineHeight: 22,
    marginBottom: 20 },
  grupo: { backgroundColor: CORES.card, borderWidth: 1,
    borderColor: CORES.line, borderRadius: 6, padding: 20 },
  grupoTitulo: { color: CORES.verde, fontSize: 11, letterSpacing: 3,
    fontWeight: "600", marginBottom: 8 },
  dica: { color: CORES.dim, fontSize: 13, lineHeight: 19,
    marginBottom: 12 },
  area: { backgroundColor: CORES.bg, borderWidth: 1,
    borderColor: CORES.line, color: CORES.ink, padding: 12,
    borderRadius: 4, minHeight: 150, textAlignVertical: "top",
    fontSize: 13 },
  consentimento: { flexDirection: "row", alignItems: "center",
    gap: 12, backgroundColor: CORES.card, borderWidth: 1,
    borderColor: CORES.line, borderRadius: 6, padding: 16,
    marginTop: 16 },
  consentimentoTexto: { color: CORES.dim, fontSize: 13, flex: 1,
    lineHeight: 19 },
  botao: { backgroundColor: CORES.verde, padding: 16, marginTop: 18,
    borderRadius: 4 },
  botaoTexto: { color: "#ffffff", textAlign: "center",
    letterSpacing: 3, fontSize: 12, fontWeight: "600" },
  status: { color: CORES.verde, fontSize: 13, marginTop: 14,
    lineHeight: 19 },
});
