// SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
// SPDX-License-Identifier: AGPL-3.0-or-later
// Paleta da marca (mesma do site de apresentacao).

export const CORES = {
  bg: "#070b08",
  panel: "#0f1811",
  line: "#1c2a1f",
  ink: "#ede9dd",
  dim: "#97a698",
  green: "#58c47f",
  gold: "#c9a44a",
  gold2: "#e6cf8e",
};

export interface Produto {
  nome: string;
  tipo: string;
  spec: string;
  preco: string;
  desc: string;
}

// Catalogo FICTICIO — identico ao do site; nada e oferta real.
export const PRODUTOS: Produto[] = [
  { nome: "Reserva 3000", tipo: "Oleo full spectrum",
    spec: "CBD 3000 mg | 30 ml", preco: "R$ 289 (ilustrativo)",
    desc: "Extrato full spectrum em oleo MCT; laudo por lote." },
  { nome: "Reserva 6000", tipo: "Oleo full spectrum",
    spec: "CBD 6000 mg | 30 ml", preco: "R$ 489 (ilustrativo)",
    desc: "Alta concentracao para terapias de manutencao." },
  { nome: "Puro Isolado 1500", tipo: "Oleo isolado",
    spec: "CBD 1500 mg | THC 0,0%", preco: "R$ 199 (ilustrativo)",
    desc: "Sem THC detectavel; restricao ocupacional." },
  { nome: "Capsulas 25", tipo: "Capsulas",
    spec: "25 mg por capsula | 30 un", preco: "R$ 159 (ilustrativo)",
    desc: "Dose fixa diaria, curva de liberacao previsivel." },
  { nome: "Balsamo Recupera", tipo: "Topico",
    spec: "CBD 500 mg | 60 g", preco: "R$ 129 (ilustrativo)",
    desc: "Uso topico para desconforto localizado." },
  { nome: "Noite 1:1", tipo: "Oleo balanceado",
    spec: "CBD:THC 1:1 | 30 ml", preco: "R$ 349 (ilustrativo)",
    desc: "Dor e sono; exige receituario tipo B." },
  { nome: "Linha Pet 600", tipo: "Veterinario",
    spec: "CBD 600 mg | 30 ml", preco: "R$ 149 (ilustrativo)",
    desc: "Mediante prescricao de medico veterinario." },
  { nome: "Sublingual Spray", tipo: "Spray",
    spec: "2,5 mg por jato", preco: "R$ 179 (ilustrativo)",
    desc: "Titulacao fina, absorcao rapida." },
];
