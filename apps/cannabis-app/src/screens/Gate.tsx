// SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
// SPDX-License-Identifier: AGPL-3.0-or-later
// Tela de codigo de acesso. Nesta fase de apresentacao o codigo e
// validado localmente (constante de build); quando houver backend, a
// validacao migra para o servidor.

import React, { useState } from "react";
import { View, Text, TextInput, Pressable, StyleSheet } from "react-native";
import { StatusBar } from "expo-status-bar";
import { CORES } from "../tema";

// Codigo de apresentacao definido no build (nao e segredo forte; o
// conteudo do app e demonstrativo).
const CODIGO_DEMO = process.env.EXPO_PUBLIC_ACCESS_CODE ?? "gotaverde2026";

export function GateScreen({ onLiberar }: { onLiberar: () => void }) {
  const [codigo, setCodigo] = useState("");
  const [erro, setErro] = useState(false);
  return (
    <View style={s.fundo}>
      <StatusBar style="dark" />
      <View style={s.topo}>
        <View style={s.marcaLinha} />
        <Text style={s.marca}>GOTA VERDE</Text>
        <Text style={s.marcaSub}>CANNABIS MEDICINAL AUDITAVEL</Text>
      </View>
      <View style={s.caixa}>
        <Text style={s.rotulo}>ACESSO RESTRITO</Text>
        <Text style={s.sub}>
          Material de apresentacao restrito. Informe o codigo de acesso.
        </Text>
        <TextInput
          style={s.campo}
          secureTextEntry
          autoCapitalize="none"
          value={codigo}
          onChangeText={setCodigo}
        />
        <Pressable
          style={s.botao}
          onPress={() =>
            codigo === CODIGO_DEMO ? onLiberar() : setErro(true)
          }
        >
          <Text style={s.botaoTexto}>ENTRAR</Text>
        </Pressable>
        {erro ? <Text style={s.erro}>Codigo incorreto.</Text> : null}
      </View>
      <Text style={s.rodape}>
        Fase de apresentacao. Nada aqui constitui oferta comercial.
      </Text>
    </View>
  );
}

const s = StyleSheet.create({
  fundo: { flex: 1, backgroundColor: CORES.bg, alignItems: "center",
    justifyContent: "center", padding: 28 },
  topo: { alignItems: "center", marginBottom: 36 },
  marcaLinha: { width: 40, height: 2, backgroundColor: CORES.verde,
    marginBottom: 18 },
  marca: { color: CORES.ink, fontSize: 22, letterSpacing: 8,
    fontWeight: "600" },
  marcaSub: { color: CORES.sage, fontSize: 10, letterSpacing: 3,
    marginTop: 8 },
  caixa: { backgroundColor: CORES.card, borderWidth: 1,
    borderColor: CORES.line, borderRadius: 6, padding: 32,
    width: "100%", maxWidth: 360 },
  rotulo: { color: CORES.verde, fontSize: 10, letterSpacing: 3,
    fontWeight: "600", marginBottom: 10 },
  sub: { color: CORES.dim, fontSize: 14, lineHeight: 21,
    marginBottom: 20 },
  campo: { backgroundColor: CORES.bg, borderWidth: 1,
    borderColor: CORES.line, color: CORES.ink, padding: 14,
    textAlign: "center", letterSpacing: 6, borderRadius: 4,
    fontSize: 15 },
  botao: { backgroundColor: CORES.verde, padding: 15, marginTop: 18,
    borderRadius: 4 },
  botaoTexto: { color: "#ffffff", textAlign: "center", letterSpacing: 3,
    fontSize: 12, fontWeight: "600" },
  erro: { color: CORES.erro, textAlign: "center", marginTop: 14,
    fontSize: 13 },
  rodape: { color: CORES.sage, fontSize: 11, textAlign: "center",
    marginTop: 32, lineHeight: 16 },
});
