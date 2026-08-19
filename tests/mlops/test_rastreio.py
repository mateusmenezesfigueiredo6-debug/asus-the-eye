"""Testes do rastreio ML — identidade, integridade referencial e selagem."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from asus_theye.mlops import (
    Corrida,
    MLOpsError,
    Modelo,
    Versao,
    campeao_atual,
    promover,
    registrar_corrida,
    registrar_modelo,
    registrar_versao,
)

MODELO = Modelo(modelo_id="m1", nome="Modelo Um", area="macroeconomia", objetivo="prever X contra fonte oficial")
VERSAO = Versao(modelo_id="m1", versao="1.0.0", origem="tests")


def _corrida(**sobrescreve: Any) -> Corrida:
    campos: dict[str, Any] = {
        "modelo_id": "m1",
        "versao": "1.0.0",
        "params": {"seed": 42},
        "metricas": {"brier": 0.25},
        "artefatos": [{"caminho": "x.json", "sha256": "a" * 64}],
        "executada_em": "2026-08-19T12:00:00Z",
    }
    campos.update(sobrescreve)
    return Corrida(**campos)


def _sdk(tmp: Path) -> Any:
    from asus_theye.markets.auditoria import abrir_auditoria

    return abrir_auditoria(
        tmp / "ledger.db",
        chave=b"chave-de-teste-32-bytes-ok!!",
        eventos=tmp / "corrente.jsonl",
        fingerprint=tmp / "chave.fingerprint",
    )


# ------------------------------------------------------------ registry


def test_modelo_novo_dedupe_e_divergencia(tmp_path: Path) -> None:
    assert registrar_modelo(MODELO, base=tmp_path)["duplicate"] is False
    assert registrar_modelo(MODELO, base=tmp_path)["duplicate"] is True  # idempotente
    with pytest.raises(MLOpsError, match="DIFERENTE"):
        registrar_modelo(
            Modelo(modelo_id="m1", nome="OUTRO nome", area="x", objetivo="y"),
            base=tmp_path,
        )


def test_modelo_sem_objetivo_levanta(tmp_path: Path) -> None:
    with pytest.raises(MLOpsError, match="objetivo"):
        registrar_modelo(Modelo(modelo_id="m1", nome="A", area="x", objetivo="  "), base=tmp_path)


def test_versao_exige_modelo_registrado(tmp_path: Path) -> None:
    with pytest.raises(MLOpsError, match="integridade referencial"):
        registrar_versao(VERSAO, base=tmp_path)
    registrar_modelo(MODELO, base=tmp_path)
    assert registrar_versao(VERSAO, base=tmp_path)["duplicate"] is False
    assert registrar_versao(VERSAO, base=tmp_path)["duplicate"] is True


# ------------------------------------------------------------ corridas


def _preparar(tmp: Path) -> None:
    registrar_modelo(MODELO, base=tmp)
    registrar_versao(VERSAO, base=tmp)


def test_corrida_exige_versao_registrada(tmp_path: Path) -> None:
    with pytest.raises(MLOpsError, match="fantasma"):
        registrar_corrida(_corrida(), base=tmp_path)


def test_corrida_identidade_e_o_conteudo(tmp_path: Path) -> None:
    _preparar(tmp_path)
    r1 = registrar_corrida(_corrida(), base=tmp_path)
    assert r1["duplicate"] is False
    # mesmo conteúdo → dedupe, mesma corrida_id
    r2 = registrar_corrida(_corrida(), base=tmp_path)
    assert r2["duplicate"] is True
    assert r2["registro"]["corrida_id"] == r1["registro"]["corrida_id"]
    # métrica diferente → corrida NOVA
    r3 = registrar_corrida(_corrida(metricas={"brier": 0.09}), base=tmp_path)
    assert r3["duplicate"] is False
    assert r3["registro"]["corrida_id"] != r1["registro"]["corrida_id"]
    assert len((tmp_path / "corridas.jsonl").read_text(encoding="utf-8").splitlines()) == 2


def test_corrida_metrica_nao_numerica_levanta(tmp_path: Path) -> None:
    _preparar(tmp_path)
    with pytest.raises(MLOpsError, match="num"):
        registrar_corrida(_corrida(metricas={"brier": "0.25"}), base=tmp_path)


def test_corrida_artefato_sem_sha256_levanta(tmp_path: Path) -> None:
    _preparar(tmp_path)
    with pytest.raises(MLOpsError, match="sha256"):
        registrar_corrida(_corrida(artefatos=[{"caminho": "x.json", "sha256": "curto"}]), base=tmp_path)


# ------------------------------------------------------------ selagem (em hash)


def test_corrida_selada_vira_evento_ml_run_verificavel(tmp_path: Path) -> None:
    from asus_theye.audit.schema import verify_event
    from asus_theye.markets.auditoria import cabeca_da_corrente

    _preparar(tmp_path)
    sdk = _sdk(tmp_path)
    corrente = tmp_path / "corrente.jsonl"
    r1 = registrar_corrida(_corrida(), base=tmp_path, sdk=sdk, eventos=corrente)
    assert r1["selagem"] is not None and r1["selagem"]["duplicate"] is False
    selado = json.loads(corrente.read_text(encoding="utf-8").strip())
    assert selado["event_type"] == "ml.run"
    assert verify_event(selado)
    # re-registro do mesmo conteúdo: dedupe no store E na cadeia — corrente estável
    r2 = registrar_corrida(_corrida(), base=tmp_path, sdk=sdk, eventos=corrente)
    assert r2["duplicate"] is True and r2["selagem"]["duplicate"] is True
    assert cabeca_da_corrente(sdk) == 1


def test_selagem_repara_corrente_que_perdeu_o_evento(tmp_path: Path) -> None:
    """Dedupe local NÃO pula a selagem: corrida já no store sela na cadeia vazia."""
    _preparar(tmp_path)
    registrar_corrida(_corrida(), base=tmp_path)  # primeiro sem SDK (cadeia nunca viu)
    sdk = _sdk(tmp_path)
    corrente = tmp_path / "corrente.jsonl"
    r = registrar_corrida(_corrida(), base=tmp_path, sdk=sdk, eventos=corrente)
    assert r["duplicate"] is True  # dedupe no store...
    assert r["selagem"] is not None and r["selagem"]["duplicate"] is False  # ...mas a cadeia ganhou o evento


# ------------------------------------------------------------ campeão/desafiante


def test_promocao_exige_papel_motivo_e_versao(tmp_path: Path) -> None:
    _preparar(tmp_path)
    comum = {"modelo_id": "m1", "versao": "1.0.0", "promovido_em": "2026-08-19T12:00:00Z", "base": tmp_path}
    with pytest.raises(MLOpsError, match="papel"):
        promover(papel="rei", motivo="x", **comum)
    with pytest.raises(MLOpsError, match="motivo"):
        promover(papel="campeao", motivo="  ", **comum)
    with pytest.raises(MLOpsError, match="não se promove"):
        promover(modelo_id="m1", versao="9.9.9", papel="campeao", motivo="x", promovido_em="t", base=tmp_path)


def test_campeao_atual_e_a_ultima_promocao(tmp_path: Path) -> None:
    _preparar(tmp_path)
    registrar_versao(Versao(modelo_id="m1", versao="2.0.0", origem="tests"), base=tmp_path)
    assert campeao_atual("m1", base=tmp_path) is None
    promover(
        modelo_id="m1", versao="1.0.0", papel="campeao", motivo="baseline", promovido_em="t1", base=tmp_path
    )
    promover(
        modelo_id="m1", versao="2.0.0", papel="campeao", motivo="brier menor", promovido_em="t2", base=tmp_path
    )
    atual = campeao_atual("m1", base=tmp_path)
    assert atual is not None and atual["versao"] == "2.0.0"


# ------------------------------------------------------------ produtor: benchmark


def test_corrida_do_benchmark_traduz_o_relatorio(tmp_path: Path) -> None:
    from asus_theye.mlops.producers import corrida_do_benchmark

    report_path = tmp_path / "latest.json"
    report_path.write_text('{"ok": true}', encoding="utf-8")
    report = {
        "date": "2026-08-19",
        "problem": {"name": "demo"},
        "results": {"classical": {"score": 10.0}, "qaoa": {"score": 9.0}},
        "metrics": {"qar": {"qar": 0.9}, "stability": {"standard_deviation": 0.1}},
    }
    corrida = corrida_do_benchmark(report, report_path, shots=64, layers=1, seed=7, stability_runs=2)
    assert corrida.modelo_id == "qaoa-benchmark"
    assert corrida.metricas["qar"] == 0.9
    assert corrida.params == {"problema": "demo", "shots": 64, "layers": 1, "seed": 7, "stability_runs": 2}
    assert corrida.artefatos[0]["sha256"] == hashlib.sha256(report_path.read_bytes()).hexdigest()
