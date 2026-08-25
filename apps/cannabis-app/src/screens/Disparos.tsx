// SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
// SPDX-License-Identifier: AGPL-3.0-or-later
// Painel admin de disparos: convites a medicos e empresas via o mesmo
// Worker do site (/api/outreach), com opt-out e lista de supressao.

import React, { useState } from "react";
import { ScrollView, Text, TextInput, Pressable, StyleSheet, Switch }
  from "react-native";
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
      <Text style={s.h1}>Disparos a medicos e empresas</Text>
      <Text style={s.p}>
        Uma linha por contato: nome;email;crm;tipo (medico ou empresa).
        Template oficial do funil, com descadastro automatico. Maximo
        100 por lote.
      </Text>
      <TextInput
        style={s.area}
        multiline
        numberOfLines={8}
        placeholder="Maria Silva;maria@exemplo.com;123456;medico"
        placeholderTextColor={CORES.dim}
        value={lista}
        onChangeText={setLista}
      />
      <Text style={s.check}>
        <Switch value={baseLegal} onValueChange={setBaseLegal} />
        {"  "}Declaro que a lista tem base legal (LGPD) e respeita
        descadastros anteriores.
      </Text>
      <Pressable style={s.botao} onPress={disparar}>
        <Text style={s.botaoTexto}>DISPARAR</Text>
      </Pressable>
      {status ? <Text style={s.status}>{status}</Text> : null}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  fundo: { flex: 1, backgroundColor: CORES.bg },
  pad: { padding: 22, paddingBottom: 60 },
  h1: { color: CORES.ink, fontSize: 22, lineHeight: 30,
    marginBottom: 8 },
  p: { color: CORES.dim, fontSize: 13, lineHeight: 20,
    marginBottom: 14 },
  area: { backgroundColor: CORES.panel, borderWidth: 1,
    borderColor: CORES.line, color: CORES.ink, padding: 12,
    borderRadius: 2, minHeight: 150, textAlignVertical: "top",
    fontSize: 13 },
  check: { color: CORES.dim, fontSize: 13, marginVertical: 14,
    lineHeight: 22 },
  botao: { backgroundColor: CORES.gold, padding: 14, borderRadius: 2 },
  botaoTexto: { color: "#14100a", textAlign: "center",
    letterSpacing: 3, fontSize: 12, fontWeight: "600" },
  status: { color: CORES.green, fontSize: 13, marginTop: 12 },
});
