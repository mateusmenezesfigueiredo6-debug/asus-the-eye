# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tempo de propaganda eleitoral gratuita como sinal estrutural.

É o segundo sinal do modelo, e existe para cobrir exatamente onde o primeiro
falha. No backtest contra 2022, a atenção pública superestimou Ciro Gomes em
8,36 pontos e subestimou Simone Tebet em 3,31. A causa é a mesma nos dois casos:
**atenção não enxerga estrutura partidária.** Ciro era figura midiática com legenda
pequena; Tebet tinha pouca visibilidade digital e o MDB atrás.

O tempo de TV é a medida direta dessa estrutura, e tem três propriedades raras:
é **público**, é **conhecido antes do pleito**, e é **determinado por lei** — não
por pesquisa, opinião ou negociação.

A REGRA, art. 47, §2º da Lei 9.504/1997:

    I  — 90% distribuídos proporcionalmente ao número de representantes na
         Câmara dos Deputados, considerado, no caso de coligação para eleições
         majoritárias, o resultado da soma dos **6 maiores partidos** que a
         integrem;
    II — 10% distribuídos igualitariamente.

O teto de seis partidos é detalhe que muda conta: uma coligação de dez legendas
só soma as seis maiores. Ignorá-lo daria vantagem artificial a quem junta muitos
partidos pequenos — que é precisamente a manobra que o dispositivo existe para
neutralizar.

────────────────────────────────────────────────────────────────────────────
O QUE A LITERATURA MEDIU, E O TAMANHO HONESTO DO SINAL

Speck & Cervi (2016), revista *Dados*: β padronizado do tempo de HGPE = **0,106**
(eleições municipais de 2012, N = 13.038 candidatos, R² = 0,54). O HGPE é o
**quarto** fator mais forte, atrás de dinheiro de campanha, memória eleitoral e
competitividade — e seu peso **cresce com o tamanho do município**.

Três consequências que este módulo assume:

1. **O sinal é real e é secundário.** Entra com peso, não como decisor.
2. **O sinal mais forte — dinheiro de campanha — está fora do nosso alcance.**
   A prestação de contas do TSE responde 403 nesta rede, enquanto a bancada da
   Câmara está aberta. Operamos com o segundo melhor sabendo disso, e é melhor
   dizer do que fingir que escolhemos.
3. **A medida veio de eleição MUNICIPAL.** Transferir para presidencial é
   extrapolação. O sinal de que a extrapolação é defensável está no próprio
   achado — o efeito cresce com o tamanho do município, e uma eleição nacional é
   o extremo dessa escala — mas continua sendo extrapolação, e fica declarada.
────────────────────────────────────────────────────────────────────────────

A BANCADA É A ELEITA, NÃO A QUE EXERCEU. A API da Câmara devolve, por
legislatura, todo mundo que exerceu mandato — 647 pessoas onde a Câmara tem 513,
porque suplentes assumem quando alguém vira ministro ou se licencia. Contar
assim inflaria o tempo de quem cedeu mais quadros ao Executivo, que é
justamente o partido do governo. A contagem usa apenas quem tem
``condicaoEleitoral == "Titular"``, deduplicado por pessoa.

FEDERAÇÕES SÃO DECLARADAS, NÃO DEDUZIDAS. Uma federação partidária conta como
bloco único para efeito de bancada. Quais existem em 2026 é fato jurídico com
data, não inferência — e este módulo exige que sejam informadas, pela mesma
razão que o conector de atenção exige o título do artigo declarado: derivar
identidade de rótulo é como se mede a lula errada.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class TempoDeTVError(RuntimeError):
    """Recusa calcular. Tempo de TV errado desloca o modelo inteiro."""


#: Art. 47, §2º, I e II. Não são parâmetros ajustáveis — são a lei.
FATIA_PROPORCIONAL = 0.90
FATIA_IGUALITARIA = 0.10

#: Art. 47, §2º, I, parte final: em eleição majoritária, a coligação soma apenas
#: os seis maiores partidos que a integram.
MAX_PARTIDOS_NA_COLIGACAO = 6


@dataclass(frozen=True)
class Candidatura:
    """Um candidato e o bloco partidário que o apoia.

    ``partidos`` é a lista de siglas do bloco — partido isolado, federação ou
    coligação. Declarada por pessoa, com a composição conferida na fonte
    jurídica, nunca inferida do nome do candidato ou da legenda principal.
    """

    nome: str
    partidos: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.nome.strip():
            raise TempoDeTVError("candidatura sem nome")
        if not self.partidos:
            raise TempoDeTVError(f"{self.nome!r} sem partido declarado")
        if len(set(self.partidos)) != len(self.partidos):
            raise TempoDeTVError(f"{self.nome!r} com partido repetido: {self.partidos}")


@dataclass
class TempoDeTV:
    """Reparte o horário gratuito conforme o art. 47, §2º."""

    #: {sigla: número de deputados federais ELEITOS}
    bancada: dict[str, int]
    candidaturas: list[Candidatura] = field(default_factory=list)
    #: Total de cadeiras, para conferência. A Câmara tem 513.
    cadeiras_esperadas: int = 513

    def __post_init__(self) -> None:
        if not self.bancada:
            raise TempoDeTVError("bancada vazia")
        if any(n < 0 for n in self.bancada.values()):
            raise TempoDeTVError("bancada com contagem negativa")
        total = sum(self.bancada.values())
        if total == 0:
            raise TempoDeTVError("bancada soma zero")
        # Aviso, não erro: a composição muda com trocas de partido, e travar
        # aqui impediria de trabalhar com dado parcial durante a coleta.
        self.divergencia_de_cadeiras = total - self.cadeiras_esperadas

    def cadeiras_do_bloco(self, c: Candidatura) -> int:
        """Soma da bancada do bloco, respeitando o teto de seis partidos.

        Partido sem representação na Câmara entra com zero — o que é correto e
        não é omissão: um partido sem deputado federal não gera tempo
        proporcional nenhum, só o naco igualitário.
        """
        tamanhos = sorted(
            (self.bancada.get(p, 0) for p in c.partidos), reverse=True
        )[:MAX_PARTIDOS_NA_COLIGACAO]
        return sum(tamanhos)

    def fatias(self) -> dict[str, float]:
        """Fração do tempo total de cada candidatura. Soma 1."""
        if not self.candidaturas:
            raise TempoDeTVError("nenhuma candidatura — não há o que repartir")
        nomes = [c.nome for c in self.candidaturas]
        if len(set(nomes)) != len(nomes):
            raise TempoDeTVError("candidatura repetida na lista")

        cadeiras = {c.nome: self.cadeiras_do_bloco(c) for c in self.candidaturas}
        soma = sum(cadeiras.values())
        n = len(self.candidaturas)

        igual = FATIA_IGUALITARIA / n
        if soma == 0:
            # Nenhum bloco tem cadeira: os 90% proporcionais não têm base de
            # rateio. A lei não prevê o caso porque na prática não ocorre; a
            # divisão igual é a leitura menos arbitrária, e fica declarada.
            return {c.nome: 1.0 / n for c in self.candidaturas}
        return {
            nome: FATIA_PROPORCIONAL * (cad / soma) + igual
            for nome, cad in cadeiras.items()
        }

    def relatorio(self) -> list[dict]:
        """Detalhe por candidatura, para conferência humana."""
        fatias = self.fatias()
        fora = []
        for c in self.candidaturas:
            usados = sorted(
                ((p, self.bancada.get(p, 0)) for p in c.partidos),
                key=lambda kv: -kv[1],
            )
            fora.append({
                "candidato": c.nome,
                "bloco": list(c.partidos),
                "cadeiras": self.cadeiras_do_bloco(c),
                "partidos_contados": [p for p, _ in usados[:MAX_PARTIDOS_NA_COLIGACAO]],
                "partidos_cortados_pelo_teto": [p for p, _ in usados[MAX_PARTIDOS_NA_COLIGACAO:]],
                "fatia_do_tempo": fatias[c.nome],
            })
        return sorted(fora, key=lambda d: -d["fatia_do_tempo"])

    def avisos(self) -> list[str]:
        """O que o consumidor precisa saber antes de confiar no número."""
        fora: list[str] = []
        if self.divergencia_de_cadeiras:
            fora.append(
                f"a bancada soma {sum(self.bancada.values())} cadeiras, e a Câmara tem "
                f"{self.cadeiras_esperadas} (diferença de {self.divergencia_de_cadeiras:+d}) "
                "— confira se a contagem inclui suplentes ou duplica quem trocou de partido"
            )
        sem_banca = [
            c.nome for c in self.candidaturas if self.cadeiras_do_bloco(c) == 0
        ]
        if sem_banca:
            fora.append(
                f"sem representação na Câmara, logo só o naco igualitário: {sem_banca}"
            )
        cortados = [
            (c.nome, len(c.partidos) - MAX_PARTIDOS_NA_COLIGACAO)
            for c in self.candidaturas
            if len(c.partidos) > MAX_PARTIDOS_NA_COLIGACAO
        ]
        for nome, quantos in cortados:
            fora.append(
                f"{nome}: {quantos} partido(s) fora da conta pelo teto de seis "
                "(art. 47, §2º, I, parte final)"
            )
        fora.append(
            "efeito medido em eleição MUNICIPAL (Speck & Cervi 2016, β=0,106); "
            "aplicar a pleito presidencial é extrapolação declarada"
        )
        fora.append(
            "o preditor mais forte segundo a mesma literatura é DINHEIRO DE CAMPANHA, "
            "e a prestação de contas do TSE responde 403 nesta rede — este é o "
            "segundo melhor sinal, não o melhor"
        )
        return fora
