// SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
// SPDX-License-Identifier: AGPL-3.0-or-later
// Wizard do pedido de autorizacao ANVISA (RDC 660): coleta os dados,
// envia o pacote ao Worker da associacao; a submissao no Gov.br e
// concluida pelo despachante humano com procuracao (sem API publica).

import React, { useState } from "react";
import { ScrollView, Text, TextInput, Pressable, StyleSheet }
  from "react-native";
import { CORES } from "../tema";

const API = process.env.EXPO_PUBLIC_API_URL ?? "";

const CAMPOS: Array<[string, string]> = [
  ["nome", "Nome completo"], ["cpf", "CPF"],
  ["nascimento", "Data de nascimento"], ["email", "Email"],
  ["telefone", "Telefone"], ["endereco", "Endereco completo"],
  ["medico", "Nome do medico"], ["crm", "CRM"], ["uf", "UF do CRM"],
  ["dataReceita", "Data da receita"], ["produto", "Produto prescrito"],
  ["posologia", "Concentracao e posologia"],
  ["fornecedor", "Fornecedor pretendido (opcional)"],
];

export function AutorizacaoScreen() {
  const [dados, setDados] = useState<Record<string, string>>({});
  const [status, setStatus] = useState("");
  const enviar = async () => {
    const faltando = CAMPOS.filter(
      ([k]) => k !== "fornecedor" && !(dados[k] ?? "").trim(),
    );
    if (faltando.length) {
      setStatus(`Preencha: ${faltando.map(([, r]) => r).join(", ")}`);
      return;
    }
    setStatus("Enviando pacote...");
    try {
      const r = await fetch(`${API}/api/autorizacao`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dados),
      });
      const j = await r.json();
      setStatus(
        j.encaminhado
          ? "Pacote enviado. A equipe retorna em ate 1 dia util."
          : "Pacote registrado (envio ativa no deploy).",
      );
    } catch {
      setStatus("Pacote gerado localmente (demonstracao, sem backend).");
    }
  };
  return (
    <ScrollView style={s.fundo} contentContainerStyle={s.pad}>
      <Text style={s.h1}>Pedido de autorizacao ANVISA</Text>
      <Text style={s.p}>
        Preencha uma vez; nossa equipe protocola no Gov.br como sua
        representante e devolve o protocolo. A autorizacao sai no seu
        nome e vale 2 anos. Nenhum dado fica no app.
      </Text>
      {CAMPOS.map(([k, rotulo]) => (
        <TextInput
          key={k}
          style={s.campo}
          placeholder={rotulo}
          placeholderTextColor={CORES.dim}
          value={dados[k] ?? ""}
          onChangeText={(v) => setDados((d) => ({ ...d, [k]: v }))}
        />
      ))}
      <Pressable style={s.botao} onPress={enviar}>
        <Text style={s.botaoTexto}>ENVIAR PACOTE</Text>
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
    marginBottom: 16 },
  campo: { backgroundColor: CORES.panel, borderWidth: 1,
    borderColor: CORES.line, color: CORES.ink, padding: 12,
    borderRadius: 2, marginBottom: 10, fontSize: 14 },
  botao: { backgroundColor: CORES.gold, padding: 14, marginTop: 10,
    borderRadius: 2 },
  botaoTexto: { color: "#14100a", textAlign: "center",
    letterSpacing: 3, fontSize: 12, fontWeight: "600" },
  status: { color: CORES.green, fontSize: 13, marginTop: 12 },
});
