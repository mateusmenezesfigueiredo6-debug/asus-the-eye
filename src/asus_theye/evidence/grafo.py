"""Grafo de linhagem da Evidência — relações sobre os artefatos versionados.

Constrói o grafo a partir do que EXISTE em ``reports/markets/`` (registro,
resoluções, eventos selados, âncoras) e responde a pergunta central da
plataforma (a que a Palantir responde a portas fechadas, e nós respondemos
verificável):

    "Dado este nó, prove a linhagem até a Fonte primária."

Direção das arestas: sempre do DERIVADO para o UPSTREAM (o que ele deriva). Assim
a linhagem-até-a-fonte é uma caminhada seguindo as arestas até um nó ``Fonte``.
A corrente honesta é PARCIAL quando faltam elos (ex.: sem âncora ainda) — o grafo
mostra o que existe, nunca inventa o que falta.
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from asus_theye.audit.schema import verify_chain
from asus_theye.evidence.entidades import (
    ANCORA,
    FONTE,
    TIPOS,
    Chave,
    No,
    ancora,
    artefato,
    comparador,
    evento,
    fonte,
    lote,
    mercado,
    recibo,
    resolucao,
)

BASE_PADRAO = Path("reports/markets")

# Relações (nome da aresta derivado→upstream).
CONSULTA = "CONSULTA"  # Mercado → Fonte
MEDE = "MEDE"  # Resolucao → Mercado
CONTRA = "CONTRA"  # Resolucao → Fonte
SELA = "SELA"  # EventoSelado → Resolucao
SUCEDE = "SUCEDE"  # EventoSelado → EventoSelado anterior (integridade de corrente)
AGREGA = "AGREGA"  # LoteMerkle → EventoSelado
ANCORA_REL = "ANCORA"  # Ancora → LoteMerkle
DERIVA_DE = "DERIVA_DE"  # Artefato → Fonte (dado bruto com hash)
DIVERGE_DE = "DIVERGE_DE"  # Comparador → Mercado (registro de divergência; NUNCA resolve)
REGISTRA = "REGISTRA"  # EventoSelado(market.comparator) → Mercado observado
ATESTA = "ATESTA"  # Recibo → EventoSelado (resultado real da verificação)

# Arestas de DERIVAÇÃO (de onde o dado vem). SUCEDE fica de fora: é ordenação
# temporal/integridade, não derivação — seguir SUCEDE faria um evento parecer
# embasado pelas Fontes de todos os anteriores. A âncora já alcança todos os
# eventos do lote por AGREGA, então excluir SUCEDE não encurta a linhagem real.
# DIVERGE_DE também fica de fora (o comparador é deliberadamente EXTERNO à
# linhagem de resolução — spec 3.8) e ATESTA idem (recibo atesta; dado não
# deriva dele). REGISTRA entra: o evento de comparação deriva do Mercado que
# observa (e por ele alcança a Fonte declarada do claim).
DERIVACAO = (CONSULTA, MEDE, CONTRA, SELA, AGREGA, ANCORA_REL, DERIVA_DE, REGISTRA)


class GrafoError(RuntimeError):
    """Dado inconsistente ao montar o grafo. Sempre levanta — nunca inventa elo."""


@dataclass(frozen=True)
class Aresta:
    origem: Chave
    relacao: str
    destino: Chave

    def as_dict(self) -> dict[str, Any]:
        return {"origem": list(self.origem), "relacao": self.relacao, "destino": list(self.destino)}


@dataclass
class Grafo:
    nos: dict[Chave, No]
    arestas: list[Aresta]

    def no(self, chave: Chave) -> No | None:
        return self.nos.get(chave)

    def as_dict(self) -> dict[str, Any]:
        return {
            "nos": [n.as_dict() for n in self.nos.values()],
            "arestas": [a.as_dict() for a in self.arestas],
            "totais": {"nos": len(self.nos), "arestas": len(self.arestas)},
        }


def _linhas_jsonl(caminho: Path) -> list[dict[str, Any]]:
    if not caminho.exists():
        return []
    return [json.loads(li) for li in caminho.read_text(encoding="utf-8").splitlines() if li.strip()]


def construir_grafo(base: Path = BASE_PADRAO) -> Grafo:
    """Monta o grafo lendo o que existe em ``base``. Elos ausentes ficam ausentes."""
    nos: dict[Chave, No] = {}
    arestas: list[Aresta] = []

    def por(no: No) -> No:
        nos.setdefault(no.chave, no)
        return nos[no.chave]

    def liga(origem: No, relacao: str, destino: No) -> None:
        arestas.append(Aresta(origem.chave, relacao, destino.chave))

    # Mercados (registro.json) → Fonte
    registro_path = base / "registro.json"
    if registro_path.exists():
        registro = json.loads(registro_path.read_text(encoding="utf-8"))
        for m in registro.get("mercados", []):
            no_m = por(
                mercado(
                    m["claim_id"],
                    area=m["market_area_id"],
                    pergunta=m.get("question", ""),
                    estado=m["estado"],
                    probabilidade=m["probability"],
                )
            )
            liga(no_m, CONSULTA, por(fonte(m["resolution_source"])))

    # Resoluções (resolucoes.jsonl) → Mercado e Fonte
    por_claim_resolucao: dict[str, No] = {}
    for linha in _linhas_jsonl(base / "resolucoes.jsonl"):
        no_r = por(
            resolucao(
                linha["claim_id"],
                outcome=int(linha["outcome"]),
                brier=float(linha["brier_do_contrato"]),
                fonte_nome=linha["resolution_source"],
            )
        )
        por_claim_resolucao[linha["claim_id"]] = no_r
        mercado_existente = nos.get(("Mercado", linha["claim_id"]))
        if mercado_existente is not None:
            liga(no_r, MEDE, mercado_existente)
        liga(no_r, CONTRA, por(fonte(linha["resolution_source"])))

    # Artefatos (artefatos.jsonl) → Fonte: o dado bruto com hash, a evidência primária
    for art in _linhas_jsonl(base / "artefatos.jsonl"):
        no_art = por(
            artefato(
                art["id"],
                fonte_nome=art["fonte"],
                sha256=art["sha256"],
                retrieved_at=art["retrieved_at"],
                descricao=art.get("descricao", ""),
            )
        )
        liga(no_art, DERIVA_DE, por(fonte(art["fonte"])))

    # Comparador (comparador.jsonl) → DIVERGE_DE → Mercado. Fora da linhagem de
    # resolução por desenho (spec 3.8): comparador NUNCA resolve.
    mercado_por_observacao: dict[str, No] = {}
    for obs in _linhas_jsonl(base / "comparador.jsonl"):
        alvo_mercado = nos.get(("Mercado", obs["claim_id"]))
        if alvo_mercado is not None:
            no_c = por(comparador(obs.get("comparator", "Kalshi")))
            liga(no_c, DIVERGE_DE, alvo_mercado)
            mercado_por_observacao[f"comparador:{str(obs['observacao_id'])[:32]}"] = alvo_mercado

    # Eventos selados (eventos.jsonl) → Resolucao e evento anterior
    eventos_por_hash: dict[str, No] = {}
    eventos_ordenados: list[No] = []
    for e in sorted(_linhas_jsonl(base / "eventos.jsonl"), key=lambda x: int(x["sequence"])):
        no_e = por(
            evento(
                e["event_id"],
                sequence=int(e["sequence"]),
                event_hash=e["event_hash_sha256"],
                correlation_id=e.get("correlation_id", ""),
            )
        )
        eventos_por_hash[e["event_hash_sha256"]] = no_e
        eventos_ordenados.append(no_e)
        # SELA: correlation_id == claim_id da resolução
        alvo = por_claim_resolucao.get(e.get("correlation_id", ""))
        if alvo is not None:
            liga(no_e, SELA, alvo)
        # REGISTRA: evento de comparação → Mercado observado (e, por ele, a Fonte)
        alvo_observado = mercado_por_observacao.get(e.get("correlation_id", ""))
        if alvo_observado is not None:
            liga(no_e, REGISTRA, alvo_observado)
        # SUCEDE: aponta ao evento cujo hash == previous_event_hash
        anterior = eventos_por_hash.get(e.get("previous_event_hash_sha256", ""))
        if anterior is not None:
            liga(no_e, SUCEDE, anterior)

    # Âncoras (ancoras.jsonl) → LoteMerkle → EventoSelado(s) do intervalo
    for a in _linhas_jsonl(base / "ancoras.jsonl"):
        manifest = a.get("manifest", {})
        info = a.get("ancora", {})
        no_lote = por(
            lote(
                manifest["batch_id"],
                merkle_root=manifest["merkle_root"],
                first_sequence=int(manifest["first_sequence"]),
                last_sequence=int(manifest["last_sequence"]),
            )
        )
        no_anc = por(
            ancora(
                info["tx_hash"],
                chain_id=int(info["chain_id"]),
                contrato=info["contrato"],
                block_number=info.get("block_number"),
            )
        )
        liga(no_anc, ANCORA_REL, no_lote)
        for no_e in eventos_ordenados:
            seq = int(no_e.dados["sequence"])
            if manifest["first_sequence"] <= seq <= manifest["last_sequence"]:
                liga(no_lote, AGREGA, no_e)

    # Recibo — o resultado REAL da verificação da corrente NESTA montagem
    # (mesmos estados do verificador público). Recibo atesta o topo; dado não
    # deriva dele — ATESTA fica fora de DERIVACAO.
    selados = _linhas_jsonl(base / "eventos.jsonl")
    if selados:
        try:
            integra = verify_chain(selados)
        except Exception:  # noqa: BLE001 - evento fora do esquema NÃO verifica; o recibo diz isso
            integra = False
        ancoras_presentes = sum(1 for chave in nos if chave[0] == ANCORA)
        if not integra:
            estado = "tampered"
        elif ancoras_presentes:
            estado = "valid"
        else:
            estado = "not_anchored"
        no_rec = por(
            recibo(
                estado,
                verificacoes={
                    "eventos": len(selados),
                    "verify_chain": integra,
                    "ancoras": ancoras_presentes,
                },
            )
        )
        if eventos_ordenados:
            liga(no_rec, ATESTA, eventos_ordenados[-1])

    for chave in nos:
        if chave[0] not in TIPOS:  # pragma: no cover - guarda de sanidade
            raise GrafoError(f"nó de tipo desconhecido: {chave[0]!r}")
    return Grafo(nos=nos, arestas=arestas)


def _adjacencia(grafo: Grafo, relacoes: tuple[str, ...] | None) -> dict[Chave, list[Chave]]:
    adj: dict[Chave, list[Chave]] = defaultdict(list)
    for a in grafo.arestas:
        if relacoes is None or a.relacao in relacoes:
            adj[a.origem].append(a.destino)
    return adj


def linhagem_ascendente(grafo: Grafo, tipo: str, id: str, *, relacoes: tuple[str, ...] | None = DERIVACAO) -> list[No]:
    """Nós upstream alcançáveis a partir de (tipo, id), em ordem de BFS.

    ``relacoes`` filtra as arestas seguidas; o padrão é só derivação (``SUCEDE``
    fica de fora). Passe ``None`` para seguir todas (inclui a corrente temporal).
    """
    inicio: Chave = (tipo, id)
    if inicio not in grafo.nos:
        raise GrafoError(f"nó inexistente no grafo: {inicio}")
    adj = _adjacencia(grafo, relacoes)
    vistos: set[Chave] = set()
    ordem: list[No] = []
    fila: deque[Chave] = deque(adj.get(inicio, []))
    while fila:
        atual = fila.popleft()
        if atual in vistos:
            continue
        vistos.add(atual)
        ordem.append(grafo.nos[atual])
        fila.extend(adj.get(atual, []))
    return ordem


def fontes_de(grafo: Grafo, tipo: str, id: str) -> list[No]:
    """As Fontes primárias que embasam (tipo, id) — a prova de linhagem até a origem."""
    return [n for n in linhagem_ascendente(grafo, tipo, id) if n.tipo == FONTE]
