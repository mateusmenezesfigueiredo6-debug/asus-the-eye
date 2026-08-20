# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes da ontologia de Evidência — grafo e linhagem sobre dados reais/sintéticos."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asus_theye.evidence import (
    GrafoError,
    construir_grafo,
    fontes_de,
    linhagem_ascendente,
)
from asus_theye.evidence.entidades import ANCORA, EVENTO, FONTE, LOTE, MERCADO, RESOLUCAO

FONTE_BCB = "api.bcb.gov.br (SGS)"


def _montar_base(tmp: Path, *, com_ancora: bool = False) -> Path:
    base = tmp / "markets"
    base.mkdir(parents=True)
    (base / "registro.json").write_text(
        json.dumps(
            {
                "versao": 1,
                "mercados": [
                    {
                        "claim_id": "MACRO-01::2026-07",
                        "market_area_id": "macroeconomia",
                        "question": "IPCA jul >= 0,50%?",
                        "probability": 0.5,
                        "resolution_source": FONTE_BCB,
                        "estado": "LIQUIDADO",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (base / "resolucoes.jsonl").write_text(
        json.dumps(
            {
                "claim_id": "MACRO-01::2026-07",
                "outcome": 0,
                "resolution_source": FONTE_BCB,
                "brier_do_contrato": 0.25,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (base / "eventos.jsonl").write_text(
        json.dumps(
            {
                "event_id": "ev-1",
                "sequence": 1,
                "event_hash_sha256": "a" * 64,
                "previous_event_hash_sha256": "0" * 64,
                "correlation_id": "MACRO-01::2026-07",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    if com_ancora:
        (base / "ancoras.jsonl").write_text(
            json.dumps(
                {
                    "manifest": {
                        "batch_id": "batch-1",
                        "merkle_root": "b" * 64,
                        "first_sequence": 1,
                        "last_sequence": 1,
                    },
                    "ancora": {
                        "tx_hash": "0x" + "c" * 64,
                        "chain_id": 84532,
                        "contrato": "0x" + "d" * 40,
                        "block_number": 123,
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
    return base


# --------------------------------------------------------------- construção


def test_grafo_liga_a_corrente(tmp_path: Path) -> None:
    g = construir_grafo(_montar_base(tmp_path))
    tipos = {chave[0] for chave in g.nos}
    assert {MERCADO, RESOLUCAO, EVENTO, FONTE} <= tipos
    relacoes = {a.relacao for a in g.arestas}
    assert {"CONSULTA", "MEDE", "CONTRA", "SELA"} <= relacoes


def test_base_vazia_da_grafo_vazio(tmp_path: Path) -> None:
    g = construir_grafo(tmp_path / "inexistente")
    assert g.nos == {} and g.arestas == []


# --------------------------------------------------------------- linhagem


def test_linhagem_do_evento_chega_a_fonte(tmp_path: Path) -> None:
    """A pergunta central: do evento selado, provar a Fonte primária."""
    g = construir_grafo(_montar_base(tmp_path))
    fontes = fontes_de(g, EVENTO, "ev-1")
    assert [f.id for f in fontes] == [FONTE_BCB]
    # o caminho passa pela Resolução antes da Fonte
    linhagem = linhagem_ascendente(g, EVENTO, "ev-1")
    tipos_no_caminho = [n.tipo for n in linhagem]
    assert tipos_no_caminho.index(RESOLUCAO) < tipos_no_caminho.index(FONTE)


def test_ancora_agrega_evento_e_linhagem_completa(tmp_path: Path) -> None:
    g = construir_grafo(_montar_base(tmp_path, com_ancora=True))
    # Âncora → Lote → Evento → Resolucao → Fonte
    fontes = fontes_de(g, ANCORA, "0x" + "c" * 64)
    assert [f.id for f in fontes] == [FONTE_BCB]
    tipos = [n.tipo for n in linhagem_ascendente(g, ANCORA, "0x" + "c" * 64)]
    assert LOTE in tipos and EVENTO in tipos and RESOLUCAO in tipos and FONTE in tipos


def test_sem_ancora_linhagem_e_parcial_mas_honesta(tmp_path: Path) -> None:
    """Sem âncora, a linhagem para no evento — mostra o que existe, não inventa."""
    g = construir_grafo(_montar_base(tmp_path, com_ancora=False))
    assert not any(chave[0] == LOTE for chave in g.nos)
    assert not any(chave[0] == ANCORA for chave in g.nos)
    # do evento ainda se chega à fonte
    assert [f.id for f in fontes_de(g, EVENTO, "ev-1")] == [FONTE_BCB]


def test_no_inexistente_levanta(tmp_path: Path) -> None:
    g = construir_grafo(_montar_base(tmp_path))
    with pytest.raises(GrafoError, match="inexistente"):
        linhagem_ascendente(g, EVENTO, "nao-existe")


def test_resolucao_e_mercado_nao_colidem(tmp_path: Path) -> None:
    """Resolução e Mercado têm o mesmo claim_id mas ids de nó distintos."""
    g = construir_grafo(_montar_base(tmp_path))
    assert (MERCADO, "MACRO-01::2026-07") in g.nos
    assert (RESOLUCAO, "res:MACRO-01::2026-07") in g.nos


def test_sucede_nao_vaza_fonte_de_evento_anterior(tmp_path: Path) -> None:
    """Semântica: fonte de um evento é a da sua resolução, não a dos anteriores.

    Dois eventos em corrente (SUCEDE), cada um selando uma resolução de fonte
    diferente. fontes_de(evento_2) deve devolver só a fonte do evento 2.
    """
    base = tmp_path / "markets"
    base.mkdir(parents=True)
    (base / "registro.json").write_text(json.dumps({"versao": 1, "mercados": []}), encoding="utf-8")
    (base / "resolucoes.jsonl").write_text(
        json.dumps({"claim_id": "A", "outcome": 1, "resolution_source": "fonte-A", "brier_do_contrato": 0.1})
        + "\n"
        + json.dumps({"claim_id": "B", "outcome": 0, "resolution_source": "fonte-B", "brier_do_contrato": 0.2})
        + "\n",
        encoding="utf-8",
    )
    (base / "eventos.jsonl").write_text(
        json.dumps(
            {
                "event_id": "e1",
                "sequence": 1,
                "event_hash_sha256": "1" * 64,
                "previous_event_hash_sha256": "0" * 64,
                "correlation_id": "A",
            }
        )
        + "\n"
        + json.dumps(
            {
                "event_id": "e2",
                "sequence": 2,
                "event_hash_sha256": "2" * 64,
                "previous_event_hash_sha256": "1" * 64,
                "correlation_id": "B",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    g = construir_grafo(base)
    # derivação (padrão): e2 só chega em fonte-B
    assert [f.id for f in fontes_de(g, EVENTO, "e2")] == ["fonte-B"]
    # seguindo TODAS as relações (inclui SUCEDE), aí sim alcança fonte-A também
    todas = {n.id for n in linhagem_ascendente(g, EVENTO, "e2", relacoes=None) if n.tipo == FONTE}
    assert todas == {"fonte-A", "fonte-B"}


def test_as_dict_serializa(tmp_path: Path) -> None:
    g = construir_grafo(_montar_base(tmp_path))
    d = g.as_dict()
    assert d["totais"]["nos"] == len(g.nos)
    assert all("origem" in a and "relacao" in a for a in d["arestas"])


# --------------------------------------------------------------- L3: Artefato, Recibo, Comparador


def test_artefato_deriva_da_fonte(tmp_path: Path) -> None:
    """Artefato = dado bruto de Fonte oficial, com hash — linhagem direta."""
    from asus_theye.evidence.entidades import ARTEFATO

    base = _montar_base(tmp_path)
    (base / "artefatos.jsonl").write_text(
        json.dumps(
            {
                "id": "art-1",
                "fonte": FONTE_BCB,
                "sha256": "e" * 64,
                "retrieved_at": "2026-08-19T00:00:00Z",
                "descricao": "resposta bruta",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    g = construir_grafo(base)
    assert (ARTEFATO, "art-1") in g.nos
    assert [f.id for f in fontes_de(g, ARTEFATO, "art-1")] == [FONTE_BCB]


def test_recibo_atesta_o_topo_e_diz_a_verdade(tmp_path: Path) -> None:
    """Hashes sintéticos NÃO verificam — o Recibo tem de dizer 'tampered'."""
    from asus_theye.evidence.entidades import RECIBO

    g = construir_grafo(_montar_base(tmp_path))
    rec = next(n for n in g.nos.values() if n.tipo == RECIBO)
    assert rec.dados["estado"] == "tampered"
    assert any(a.relacao == "ATESTA" for a in g.arestas)


def test_recibo_da_corrente_real_verifica() -> None:
    """A corrente REAL do repo: verify_chain True; estado reflete a âncora."""
    from asus_theye.evidence.entidades import RECIBO

    g = construir_grafo()
    rec = next(n for n in g.nos.values() if n.tipo == RECIBO)
    assert rec.dados["verificacoes"]["verify_chain"] is True
    assert rec.dados["estado"] in ("not_anchored", "valid")


def test_comparador_diverge_e_evento_registra_sem_contaminar_linhagem(tmp_path: Path) -> None:
    """DIVERGE_DE fora de DERIVACAO; o evento da observação chega à Fonte VIA o mercado."""
    from asus_theye.evidence.entidades import COMPARADOR

    base = _montar_base(tmp_path)
    (base / "comparador.jsonl").write_text(
        json.dumps(
            {
                "claim_id": "MACRO-01::2026-07",
                "comparator": "Comparador-Demo",
                "comparator_price": 0.6,
                "our_probability": 0.5,
                "observacao_id": "f" * 64,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    with (base / "eventos.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps(
                {
                    "event_id": "ev-2",
                    "sequence": 2,
                    "event_hash_sha256": "b" * 64,
                    "previous_event_hash_sha256": "a" * 64,
                    "correlation_id": "comparador:" + "f" * 32,
                }
            )
            + "\n"
        )
    g = construir_grafo(base)
    assert (COMPARADOR, "Comparador-Demo") in g.nos
    assert any(a.relacao == "DIVERGE_DE" for a in g.arestas)
    assert [f.id for f in fontes_de(g, EVENTO, "ev-2")] == [FONTE_BCB]
    assert all(n.tipo != COMPARADOR for n in linhagem_ascendente(g, MERCADO, "MACRO-01::2026-07"))
