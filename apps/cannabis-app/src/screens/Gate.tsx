// SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
// SPDX-License-Identifier: AGPL-3.0-or-later
// Tela de codigo de acesso. Nesta fase de apresentacao o codigo e
// validado localmente (constante de build); quando houver backend, a
// validacao migra para o servidor.

import React, { useState } from "react";
import { View, Text, TextInput, Pressable, StyleSheet } from "react-native";
import { CORES } from "../tema";

// Codigo de apresentacao definido no build (nao e segredo forte; o
// conteudo do app e demonstrativo).
const CODIGO_DEMO = process.env.EXPO_PUBLIC_ACCESS_CODE ?? "cinala2026";

export function GateScreen({ onLiberar }: { onLiberar: () => void }) {
  const [codigo, setCodigo] = useState("");
  const [erro, setErro] = useState(false);
  return (
    <View style={s.fundo}>
      <View style={s.caixa}>
        <Text style={s.titulo}>CINALA VERDE</Text>
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
    </View>
  );
}

const s = StyleSheet.create({
  fundo: { flex: 1, backgroundColor: CORES.bg, alignItems: "center",
    justifyContent: "center" },
  caixa: { borderWidth: 1, borderColor: CORES.line, borderRadius: 4,
    padding: 36, width: 320, backgroundColor: CORES.panel },
  titulo: { color: CORES.gold2, letterSpacing: 6, textAlign: "center",
    fontSize: 16 },
  sub: { color: CORES.dim, fontSize: 13, textAlign: "center",
    marginVertical: 16 },
  campo: { backgroundColor: CORES.bg, borderWidth: 1,
    borderColor: CORES.line, color: CORES.ink, padding: 12,
    textAlign: "center", letterSpacing: 6, borderRadius: 2 },
  botao: { backgroundColor: CORES.gold, padding: 13, marginTop: 16,
    borderRadius: 2 },
  botaoTexto: { color: "#14100a", textAlign: "center", letterSpacing: 3,
    fontSize: 12, fontWeight: "600" },
  erro: { color: "#d97676", textAlign: "center", marginTop: 12,
    fontSize: 12 },
});
