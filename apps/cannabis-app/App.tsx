// SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
// SPDX-License-Identifier: AGPL-3.0-or-later
//
// App de apresentacao do vertical cannabis (Cinala Verde).
// Mesmo conteudo demonstrativo do site: nada aqui e oferta real.

import React, { useState } from "react";
import { NavigationContainer, DarkTheme } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { StatusBar } from "expo-status-bar";
import { GateScreen } from "./src/screens/Gate";
import { HomeScreen } from "./src/screens/Home";
import { CatalogoScreen } from "./src/screens/Catalogo";
import { PesquisaScreen } from "./src/screens/Pesquisa";
import { MedicosScreen } from "./src/screens/Medicos";
import { CORES } from "./src/tema";

const Tab = createBottomTabNavigator();

const tema = {
  ...DarkTheme,
  colors: {
    ...DarkTheme.colors,
    background: CORES.bg,
    card: CORES.panel,
    text: CORES.ink,
    border: CORES.line,
    primary: CORES.gold,
  },
};

export default function App() {
  const [liberado, setLiberado] = useState(false);
  if (!liberado) {
    return <GateScreen onLiberar={() => setLiberado(true)} />;
  }
  return (
    <NavigationContainer theme={tema}>
      <StatusBar style="light" />
      <Tab.Navigator
        screenOptions={{
          headerStyle: { backgroundColor: CORES.bg },
          headerTitleStyle: { color: CORES.gold2, letterSpacing: 3 },
          tabBarStyle: { backgroundColor: CORES.panel },
          tabBarActiveTintColor: CORES.gold,
          tabBarInactiveTintColor: CORES.dim,
        }}
      >
        <Tab.Screen name="Inicio" component={HomeScreen} />
        <Tab.Screen name="Produtos" component={CatalogoScreen} />
        <Tab.Screen name="P&D" component={PesquisaScreen} />
        <Tab.Screen name="Medicos" component={MedicosScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
