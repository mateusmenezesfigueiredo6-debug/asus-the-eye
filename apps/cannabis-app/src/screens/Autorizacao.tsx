// SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
// SPDX-License-Identifier: AGPL-3.0-or-later
// Wizard do pedido de autorizacao ANVISA (RDC 660): coleta os dados,
// envia o pacote ao Worker da associacao; a submissao no Gov.br e
// concluida pelo despachante humano com procuracao (sem API publica).

import React, { useState } from "react";
import { ScrollView, Text, TextInput, View, Pressable, StyleSheet }
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

// Agrupamento visual dos mesmos campos (chaves de CAMPOS).
const GRUPOS: Array<[string, string[]]> = [
  ["PACIENTE",
   ["nome", "cpf", "nascimento", "email", "telefone", "endereco"]],
  ["PRESCRICAO",
   ["medico", "crm", "uf", "dataReceita", "produto", "posologia"]],
  ["FORNECIMENTO", ["fornecedor"]],
];

export function AutorizacaoScreen() {
  const [dados, setDados] = useState<Record<string, string>>({});
  const [status, setStatus] = useState("");
  const rotulos = new Map(CAMPOS);
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
      <Text style={s.rotulo}>ANVISA — RDC 660</Text>
      <Text style={s.h1}>Pedido de autorizacao</Text>
      <Text style={s.lead}>
        Preencha uma vez; nossa equipe protocola no Gov.br como sua
        representante e devolve o protocolo. A autorizacao sai no seu
        nome e vale 2 anos. Nenhum dado fica no app.
      </Text>
      {GRUPOS.map(([titulo, chaves]) => (
        <View key={titulo} style={s.grupo}>
          <Text style={s.grupoTitulo}>{titulo}</Text>
          {chaves.map((k) => (
            <View key={k} style={s.campoBloco}>
              <Text style={s.campoRotulo}>
                {(rotulos.get(k) ?? k).toUpperCase()}
              </Text>
              <TextInput
                style={s.campo}
                placeholder={rotulos.get(k) ?? k}
                placeholderTextColor={CORES.sage}
                value={dados[k] ?? ""}
                onChangeText={(v) =>
                  setDados((d) => ({ ...d, [k]: v }))
                }
              />
            </View>
          ))}
        </View>
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
  pad: { padding: 24, paddingBottom: 64 },
  rotulo: { color: CORES.sage, fontSize: 11, letterSpacing: 3,
    fontWeight: "600", marginBottom: 8 },
  h1: { color: CORES.ink, fontSize: 26, lineHeight: 34,
    fontWeight: "600", marginBottom: 12 },
  lead: { color: CORES.dim, fontSize: 14, lineHeight: 22,
    marginBottom: 22 },
  grupo: { backgroundColor: CORES.card, borderWidth: 1,
    borderColor: CORES.line, borderRadius: 6, padding: 20,
    marginBottom: 16 },
  grupoTitulo: { color: CORES.verde, fontSize: 11, letterSpacing: 3,
    fontWeight: "600", marginBottom: 14 },
  campoBloco: { marginBottom: 14 },
  campoRotulo: { color: CORES.sage, fontSize: 9, letterSpacing: 2,
    fontWeight: "600", marginBottom: 5 },
  campo: { backgroundColor: CORES.bg, borderWidth: 1,
    borderColor: CORES.line, color: CORES.ink, padding: 12,
    borderRadius: 4, fontSize: 14 },
  botao: { backgroundColor: CORES.verde, padding: 16, marginTop: 6,
    borderRadius: 4 },
  botaoTexto: { color: "#ffffff", textAlign: "center",
    letterSpacing: 3, fontSize: 12, fontWeight: "600" },
  status: { color: CORES.verde, fontSize: 13, marginTop: 14,
    lineHeight: 19 },
});
