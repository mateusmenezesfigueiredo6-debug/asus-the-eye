"""Testes da medição do projeto — determinismo, método obrigatório e selagem."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asus_theye.projeto import MedicaoError, medir_projeto, selar_projeto

FASES = {
    "versao": 1,
    "fases": [
        {"id": "F0", "nome": "A", "estado": "concluida", "peso_concluido": 1.0, "metodo": "m0"},
        {"id": "F1", "nome": "B", "estado": "parcial", "peso_concluido": 0.5, "metodo": "m1"},
    ],
}


def _base(tmp: Path, *, fases: dict = FASES, com_evento: bool = True) -> Path:
    (tmp / "projeto").mkdir(parents=True, exist_ok=True)
    (tmp / "projeto" / "fases.json").write_text(json.dumps(fases), encoding="utf-8")
    markets = tmp / "markets"
    markets.mkdir(exist_ok=True)
    if com_evento:
        (markets / "eventos.jsonl").write_text(
            json.dumps(
                {
                    "event_id": "e1",
                    "tenant_id": "tenant-demo",
                    "sequence": 1,
                    "event_hash_sha256": "a" * 64,
                    "previous_event_hash_sha256": "0" * 64,
                }
            )
            + "\n",
            encoding="utf-8",
        )
    return tmp


# ------------------------------------------------------------ medição


def test_pct_e_media_dos_pesos(tmp_path: Path) -> None:
    snap = medir_projeto(_base(tmp_path))
    assert snap["caminho_minimo"]["pct"] == 75.0  # (1.0 + 0.5) / 2


def test_hash_e_deterministico_sem_relogio(tmp_path: Path) -> None:
    base = _base(tmp_path)
    a = medir_projeto(base)
    b = medir_projeto(base)
    assert a["hash_da_medicao"] == b["hash_da_medicao"]
    assert a == b  # nenhum campo de relógio no snapshot


def test_hash_muda_quando_o_estado_muda(tmp_path: Path) -> None:
    base = _base(tmp_path)
    antes = medir_projeto(base)["hash_da_medicao"]
    novas = json.loads(json.dumps(FASES))
    novas["fases"][1]["peso_concluido"] = 1.0
    (base / "projeto" / "fases.json").write_text(json.dumps(novas), encoding="utf-8")
    depois = medir_projeto(base)["hash_da_medicao"]
    assert antes != depois


def test_corrente_e_contada_e_verificada(tmp_path: Path) -> None:
    snap = medir_projeto(_base(tmp_path))
    assert snap["corrente"]["eventos"] == 1
    assert snap["corrente"]["topo_hash"] == "a" * 64


def test_eixo_mlops_conta_corridas_e_entra_no_hash(tmp_path: Path) -> None:
    base = _base(tmp_path)
    antes = medir_projeto(base)
    assert antes["mlops"] == {"modelos": 0, "corridas": 0, "metodo": antes["mlops"]["metodo"]}
    (base / "mlops").mkdir()
    (base / "mlops" / "corridas.jsonl").write_text('{"corrida_id": "c1"}\n', encoding="utf-8")
    depois = medir_projeto(base)
    assert depois["mlops"]["corridas"] == 1
    assert depois["hash_da_medicao"] != antes["hash_da_medicao"]  # corrida nova = estado novo


def test_roteiro_de_produtos_ausente_e_honesto_e_declarado_mede(tmp_path: Path) -> None:
    base = _base(tmp_path)
    antes = medir_projeto(base)
    assert antes["produtos"]["pct"] is None  # ausente ≠ 0% — é "não declarado"
    assert antes["produtos"]["fases"] == []
    roteiro = {
        "versao": 1,
        "fases": [
            {"id": "P0", "nome": "Feito", "estado": "concluida", "peso_concluido": 1.0, "metodo": "m"},
            {"id": "N1", "nome": "Nuvem", "estado": "pendente", "peso_concluido": 0.0, "metodo": "m"},
        ],
    }
    (base / "projeto" / "produtos.json").write_text(json.dumps(roteiro), encoding="utf-8")
    depois = medir_projeto(base)
    assert depois["produtos"]["pct"] == 50.0
    assert depois["hash_da_medicao"] != antes["hash_da_medicao"]  # declarar o roteiro muda o estado


def test_roteiro_de_produtos_tambem_exige_metodo(tmp_path: Path) -> None:
    base = _base(tmp_path)
    ruim = {"versao": 1, "fases": [{"id": "P0", "nome": "A", "estado": "x", "peso_concluido": 1.0}]}
    (base / "projeto" / "produtos.json").write_text(json.dumps(ruim), encoding="utf-8")
    with pytest.raises(MedicaoError, match="metodo"):
        medir_projeto(base)


def test_fase_sem_metodo_levanta(tmp_path: Path) -> None:
    ruim = {"versao": 1, "fases": [{"id": "F0", "nome": "A", "estado": "x", "peso_concluido": 1.0}]}
    with pytest.raises(MedicaoError, match="metodo"):
        medir_projeto(_base(tmp_path, fases=ruim))


def test_peso_invalido_levanta(tmp_path: Path) -> None:
    ruim = {"versao": 1, "fases": [{"id": "F0", "nome": "A", "estado": "x", "peso_concluido": 1.5, "metodo": "m"}]}
    with pytest.raises(MedicaoError, match="peso_concluido"):
        medir_projeto(_base(tmp_path, fases=ruim))


def test_sem_fases_declaradas_levanta(tmp_path: Path) -> None:
    with pytest.raises(MedicaoError, match="fases"):
        medir_projeto(tmp_path)  # sem projeto/fases.json


# ------------------------------------------------------------ selagem (em hash)


def test_selagem_e_idempotente_por_estado_e_muda_com_o_estado(tmp_path: Path) -> None:
    from asus_theye.markets.auditoria import abrir_auditoria, cabeca_da_corrente

    base = _base(tmp_path, com_evento=False)
    sdk = abrir_auditoria(
        tmp_path / "ledger.db",
        chave=b"chave-de-teste-32-bytes-ok!!",
        eventos=tmp_path / "corrente.jsonl",
        fingerprint=tmp_path / "chave.fingerprint",
    )
    snap = medir_projeto(base)
    r1 = selar_projeto(sdk, snap, eventos=tmp_path / "corrente.jsonl")
    assert r1["duplicate"] is False
    assert cabeca_da_corrente(sdk) == 1
    # mesmo estado → dedupe, nada novo
    r2 = selar_projeto(sdk, medir_projeto(base), eventos=tmp_path / "corrente.jsonl")
    assert r2["duplicate"] is True
    assert cabeca_da_corrente(sdk) == 1
    # estado novo → evento novo
    novas = json.loads(json.dumps(FASES))
    novas["fases"][1]["peso_concluido"] = 0.8
    (base / "projeto" / "fases.json").write_text(json.dumps(novas), encoding="utf-8")
    r3 = selar_projeto(sdk, medir_projeto(base), eventos=tmp_path / "corrente.jsonl")
    assert r3["duplicate"] is False
    assert cabeca_da_corrente(sdk) == 2


def test_evento_selado_e_verificavel(tmp_path: Path) -> None:
    from asus_theye.audit.schema import verify_event
    from asus_theye.markets.auditoria import abrir_auditoria

    base = _base(tmp_path, com_evento=False)
    sdk = abrir_auditoria(
        tmp_path / "ledger.db",
        chave=b"chave-de-teste-32-bytes-ok!!",
        eventos=tmp_path / "corrente.jsonl",
        fingerprint=tmp_path / "chave.fingerprint",
    )
    selar_projeto(sdk, medir_projeto(base), eventos=tmp_path / "corrente.jsonl")
    selado = json.loads((tmp_path / "corrente.jsonl").read_text(encoding="utf-8").strip())
    assert selado["event_type"] == "project.measurement"
    assert verify_event(selado)


def test_medicao_nao_mede_a_si_mesma_selagem_estabiliza(tmp_path: Path) -> None:
    """O laço fatal, evitado: medir → selar → medir de novo dá o MESMO hash.

    A corrente medida exclui project.measurement; senão cada selagem mudaria o
    estado medido e o hash nunca estabilizaria.
    """
    from asus_theye.markets.auditoria import abrir_auditoria, cabeca_da_corrente

    base = _base(tmp_path, com_evento=False)
    corrente = base / "markets" / "eventos.jsonl"
    sdk = abrir_auditoria(
        tmp_path / "ledger.db",
        chave=b"chave-de-teste-32-bytes-ok!!",
        eventos=corrente,
        fingerprint=tmp_path / "chave.fingerprint",
    )
    snap1 = medir_projeto(base)
    selar_projeto(sdk, snap1, eventos=corrente)  # sela NA MESMA corrente que a medição lê
    snap2 = medir_projeto(base)
    assert snap2["hash_da_medicao"] == snap1["hash_da_medicao"], "a selagem não pode mudar a medição"
    r2 = selar_projeto(sdk, snap2, eventos=corrente)
    assert r2["duplicate"] is True
    assert cabeca_da_corrente(sdk) == 1  # um único evento de medição, sem laço


# ------------------------------------------------------------ painel


def test_painel_projeto_renderiza(tmp_path: Path) -> None:
    from asus_theye.dashboard.projeto import projeto_page

    page = projeto_page(_base(tmp_path))
    assert "MEDIÇÃO DO PROJETO" in page and "75.0%" in page
    assert "hash da medição" in page
    assert "Corridas ML" in page
    assert "Roteiro dos produtos" in page  # card sempre presente ("—" quando não declarado)


def test_painel_renderiza_checklist_dos_produtos(tmp_path: Path) -> None:
    from asus_theye.dashboard.projeto import projeto_page

    base = _base(tmp_path)
    roteiro = {
        "versao": 1,
        "fases": [{"id": "M1", "nome": "WPAM ligado", "estado": "pendente", "peso_concluido": 0.0, "metodo": "m"}],
    }
    (base / "projeto" / "produtos.json").write_text(json.dumps(roteiro), encoding="utf-8")
    page = projeto_page(base)
    assert "checklist vivo" in page and "WPAM ligado" in page


def test_painel_degrada_sem_fases(tmp_path: Path) -> None:
    from asus_theye.dashboard.projeto import projeto_page

    page = projeto_page(tmp_path)
    assert "indisponível" in page
