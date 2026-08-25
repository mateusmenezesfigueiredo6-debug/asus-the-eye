// SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
// SPDX-License-Identifier: AGPL-3.0-or-later
//
// App de apresentacao do vertical cannabis (Gota Verde).
// Mesmo conteudo demonstrativo do site: nada aqui e oferta real.

import React, { useState } from "react";
import { NavigationContainer, DefaultTheme } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { StatusBar } from "expo-status-bar";
import { GateScreen } from "./src/screens/Gate";
import { HomeScreen } from "./src/screens/Home";
import { AutorizacaoScreen } from "./src/screens/Autorizacao";
import { DisparosScreen } from "./src/screens/Disparos";
import { CatalogoScreen } from "./src/screens/Catalogo";
import { PesquisaScreen } from "./src/screens/Pesquisa";
import { MedicosScreen } from "./src/screens/Medicos";
import { CORES } from "./src/tema";

const Tab = createBottomTabNavigator();

const tema = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    background: CORES.bg,
    card: CORES.card,
    text: CORES.ink,
    border: CORES.line,
    primary: CORES.verde,
  },
};

export default function App() {
  const [liberado, setLiberado] = useState(false);
  if (!liberado) {
    return <GateScreen onLiberar={() => setLiberado(true)} />;
  }
  return (
    <NavigationContainer theme={tema}>
      <StatusBar style="dark" />
      <Tab.Navigator
        screenOptions={{
          headerStyle: {
            backgroundColor: CORES.bg,
            borderBottomWidth: 1,
            borderBottomColor: CORES.line,
            elevation: 0,
            shadowOpacity: 0,
          },
          headerTitleStyle: {
            color: CORES.ink,
            fontSize: 14,
            fontWeight: "600",
            letterSpacing: 2,
            textTransform: "uppercase",
          },
          tabBarStyle: {
            backgroundColor: CORES.card,
            borderTopWidth: 1,
            borderTopColor: CORES.line,
            elevation: 0,
          },
          tabBarActiveTintColor: CORES.verde,
          tabBarInactiveTintColor: CORES.sage,
          tabBarLabelStyle: { fontSize: 10, letterSpacing: 0.5 },
        }}
      >
        <Tab.Screen name="Inicio" component={HomeScreen} />
        <Tab.Screen name="Produtos" component={CatalogoScreen} />
        <Tab.Screen name="P&D" component={PesquisaScreen} />
        <Tab.Screen name="Medicos" component={MedicosScreen} />
        <Tab.Screen name="Autorizacao" component={AutorizacaoScreen} />
        <Tab.Screen name="Disparos" component={DisparosScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
