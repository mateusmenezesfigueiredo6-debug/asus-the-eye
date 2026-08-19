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
T0 = "2026-08-19T12:00:00Z"
T1 = "2026-08-19T13:00:00+00:00"


def _corrida(**sobrescreve: Any) -> Corrida:
    campos: dict[str, Any] = {
        "modelo_id": "m1",
        "versao": "1.0.0",
        "params": {"seed": 42},
        "metricas": {"brier": 0.25},
        "artefatos": [{"caminho": "x.json", "sha256": "a" * 64}],
        "executada_em": T0,
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


def test_arroba_em_modelo_ou_versao_levanta(tmp_path: Path) -> None:
    """'@' quebraria a inambiguidade de versao_id = modelo@versao."""
    with pytest.raises(MLOpsError, match="inamb"):
        registrar_modelo(Modelo(modelo_id="a@b", nome="A", area="x", objetivo="y"), base=tmp_path)
    registrar_modelo(MODELO, base=tmp_path)
    with pytest.raises(MLOpsError, match="inamb"):
        registrar_versao(Versao(modelo_id="m1", versao="1@0", origem="tests"), base=tmp_path)


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


def test_corrida_identidade_e_o_conteudo_declarado(tmp_path: Path) -> None:
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


def test_relogio_e_artefato_ficam_fora_da_identidade(tmp_path: Path) -> None:
    """Reexecução com MESMO resultado deduplica mesmo com timestamp/artefato novos.

    (Achado da revisão: o produtor do benchmark embute relógio e telemetria —
    se entrassem na identidade, nenhuma reexecução deduplicaria e a cadeia
    cresceria por invocação.)
    """
    _preparar(tmp_path)
    r1 = registrar_corrida(_corrida(), base=tmp_path)
    r2 = registrar_corrida(
        _corrida(executada_em=T1, artefatos=[{"caminho": "outro.json", "sha256": "b" * 64}]),
        base=tmp_path,
    )
    assert r2["duplicate"] is True
    assert r2["registro"] == r1["registro"]  # o PRIMEIRO registro vence
    assert len((tmp_path / "corridas.jsonl").read_text(encoding="utf-8").splitlines()) == 1


def test_timestamp_sem_timezone_levanta_antes_do_append(tmp_path: Path) -> None:
    """Achado alta: timestamp frouxo passava, a selagem estourava DEPOIS do append."""
    _preparar(tmp_path)
    for ruim in ("2026-08-19", "t1", "2026-08-19T12:00:00"):
        with pytest.raises(MLOpsError, match="timezone"):
            registrar_corrida(_corrida(executada_em=ruim), base=tmp_path)
    assert not (tmp_path / "corridas.jsonl").exists()  # nada foi apendado


def test_corrida_metrica_nao_numerica_levanta(tmp_path: Path) -> None:
    _preparar(tmp_path)
    with pytest.raises(MLOpsError, match="num"):
        registrar_corrida(_corrida(metricas={"brier": "0.25"}), base=tmp_path)


def test_nan_e_infinito_levantam_na_porta(tmp_path: Path) -> None:
    """Achado: NaN/inf passava a validação e estourava como CanonicalizationError."""
    _preparar(tmp_path)
    with pytest.raises(MLOpsError, match="finito"):
        registrar_corrida(_corrida(metricas={"brier": float("nan")}), base=tmp_path)
    with pytest.raises(MLOpsError, match="finito"):
        registrar_corrida(_corrida(params={"aninhado": {"x": float("inf")}}), base=tmp_path)
    assert not (tmp_path / "corridas.jsonl").exists()


def test_corrida_artefato_sem_sha256_levanta(tmp_path: Path) -> None:
    _preparar(tmp_path)
    with pytest.raises(MLOpsError, match="sha256"):
        registrar_corrida(_corrida(artefatos=[{"caminho": "x.json", "sha256": "curto"}]), base=tmp_path)
    # fullmatch: '\n' no fim não passa (o '$' do re.match passava)
    with pytest.raises(MLOpsError, match="sha256"):
        registrar_corrida(_corrida(artefatos=[{"caminho": "x.json", "sha256": "a" * 64 + "\n"}]), base=tmp_path)


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


def test_selagem_que_levanta_nao_deixa_linha_orfa(tmp_path: Path) -> None:
    """Achado alta: sela PRIMEIRO, apenda DEPOIS — falha na selagem = store intacto.

    O redator da cadeia trata 'password' como sensível: o hash selado divergiria
    do artefato, então selar_registro levanta. O store não pode ficar com uma
    linha que a corrente nunca aceitou.
    """
    from asus_theye.markets.auditoria import AuditoriaError

    _preparar(tmp_path)
    sdk = _sdk(tmp_path)
    with pytest.raises(AuditoriaError):
        registrar_corrida(
            _corrida(params={"password": "nao-e-segredo-mas-o-redator-nao-sabe"}),
            base=tmp_path,
            sdk=sdk,
            eventos=tmp_path / "corrente.jsonl",
        )
    assert not (tmp_path / "corridas.jsonl").exists()  # nenhuma linha órfã


# ------------------------------------------------------------ campeão/desafiante


def test_promocao_exige_papel_motivo_instante_e_versao(tmp_path: Path) -> None:
    _preparar(tmp_path)
    comum = {"modelo_id": "m1", "versao": "1.0.0", "promovido_em": T0, "base": tmp_path}
    with pytest.raises(MLOpsError, match="papel"):
        promover(papel="rei", motivo="x", **comum)
    with pytest.raises(MLOpsError, match="motivo"):
        promover(papel="campeao", motivo="  ", **comum)
    with pytest.raises(MLOpsError, match="timezone"):
        promover(modelo_id="m1", versao="1.0.0", papel="campeao", motivo="x", promovido_em="t", base=tmp_path)
    with pytest.raises(MLOpsError, match="não se promove"):
        promover(modelo_id="m1", versao="9.9.9", papel="campeao", motivo="x", promovido_em=T0, base=tmp_path)


def test_promocao_selada_vira_evento_ml_promotion(tmp_path: Path) -> None:
    from asus_theye.audit.schema import verify_event
    from asus_theye.markets.auditoria import cabeca_da_corrente

    _preparar(tmp_path)
    sdk = _sdk(tmp_path)
    corrente = tmp_path / "corrente.jsonl"
    r = promover(
        modelo_id="m1",
        versao="1.0.0",
        papel="campeao",
        motivo="baseline",
        promovido_em=T0,
        base=tmp_path,
        sdk=sdk,
        eventos=corrente,
    )
    assert r["selagem"] is not None and r["selagem"]["duplicate"] is False
    selado = json.loads(corrente.read_text(encoding="utf-8").strip())
    assert selado["event_type"] == "ml.promotion"
    assert verify_event(selado)
    assert cabeca_da_corrente(sdk) == 1


def test_campeao_atual_ignora_desafiante_e_pega_a_ultima(tmp_path: Path) -> None:
    _preparar(tmp_path)
    registrar_versao(Versao(modelo_id="m1", versao="2.0.0", origem="tests"), base=tmp_path)
    assert campeao_atual("m1", base=tmp_path) is None
    promover(modelo_id="m1", versao="1.0.0", papel="campeao", motivo="baseline", promovido_em=T0, base=tmp_path)
    promover(modelo_id="m1", versao="2.0.0", papel="desafiante", motivo="testando", promovido_em=T1, base=tmp_path)
    atual = campeao_atual("m1", base=tmp_path)
    assert atual is not None and atual["versao"] == "1.0.0"  # desafiante NÃO vira campeão
    promover(modelo_id="m1", versao="2.0.0", papel="campeao", motivo="brier menor", promovido_em=T1, base=tmp_path)
    atual = campeao_atual("m1", base=tmp_path)
    assert atual is not None and atual["versao"] == "2.0.0"


# ------------------------------------------------------------ produtor: benchmark


def test_corrida_do_benchmark_traduz_o_relatorio(tmp_path: Path) -> None:
    from asus_theye.mlops.producers import corrida_do_benchmark

    report_path = tmp_path / "latest.json"
    report_path.write_text('{"ok": true}', encoding="utf-8")
    report = {
        "date": "2026-08-19T12:00:00+00:00",
        "problem": {"name": "demo"},
        "results": {"classical": {"score": 10.0}, "qaoa": {"score": 9.0}},
        "metrics": {"qar": {"qar": 0.9}, "stability": {"standard_deviation": 0.1}},
    }
    corrida = corrida_do_benchmark(report, report_path, shots=64, layers=1, seed=7, stability_runs=2)
    assert corrida.modelo_id == "qaoa-benchmark"
    assert corrida.metricas["qar"] == 0.9
    assert corrida.params == {"problema": "demo", "shots": 64, "layers": 1, "seed": 7, "stability_runs": 2}
    assert corrida.artefatos[0]["sha256"] == hashlib.sha256(report_path.read_bytes()).hexdigest()
    # identidade NÃO inclui o relógio nem o artefato: reexecutar com o mesmo
    # resultado (timestamp/telemetria novos) é a MESMA corrida
    report2 = dict(report, date="2026-08-20T12:00:00+00:00")
    corrida2 = corrida_do_benchmark(report2, report_path, shots=64, layers=1, seed=7, stability_runs=2)
    assert corrida2.identidade() == corrida.identidade()


# ------------------------------------------------------------ CLI


def test_cli_mlops_benchmark_erro_sai_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Caminho de erro da CLI: divergência no registry → mensagem + exit 1."""
    from asus_theye import cli

    monkeypatch.chdir(tmp_path)
    report_path = tmp_path / "latest.json"
    report_path.write_text("{}", encoding="utf-8")
    report = {
        "date": "2026-08-19T12:00:00+00:00",
        "problem": {"name": "demo"},
        "results": {"classical": {"score": 1.0}, "qaoa": {"score": 1.0}},
        "metrics": {"qar": {"qar": 1.0}, "stability": {"standard_deviation": 0.0}},
    }
    monkeypatch.setattr(cli, "run_benchmark_suite", lambda **kw: (report, report_path))
    # registry pré-existente com o MESMO modelo_id e conteúdo DIFERENTE → MLOpsError
    (tmp_path / "reports" / "mlops").mkdir(parents=True)
    (tmp_path / "reports" / "mlops" / "modelos.jsonl").write_text(
        '{"modelo_id": "qaoa-benchmark", "nome": "outro", "area": "x", "objetivo": "y"}\n',
        encoding="utf-8",
    )
    assert cli.main(["mlops-benchmark", "--no-audit"]) == 1


def test_cli_mlops_benchmark_no_audit_rastreia(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from asus_theye import cli

    monkeypatch.chdir(tmp_path)
    report_path = tmp_path / "latest.json"
    report_path.write_text("{}", encoding="utf-8")
    report = {
        "date": "2026-08-19T12:00:00+00:00",
        "problem": {"name": "demo"},
        "results": {"classical": {"score": 1.0}, "qaoa": {"score": 1.0}},
        "metrics": {"qar": {"qar": 1.0}, "stability": {"standard_deviation": 0.0}},
    }
    monkeypatch.setattr(cli, "run_benchmark_suite", lambda **kw: (report, report_path))
    assert cli.main(["mlops-benchmark", "--no-audit"]) == 0
    corridas = (tmp_path / "reports" / "mlops" / "corridas.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(corridas) == 1


# ------------------------------------------------------------ servidor


def test_rota_projeto_esta_montada_no_app() -> None:
    """Achado da exploração: register_projeto_routes existia mas nunca era montada."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from asus_theye.dashboard.app import create_dashboard_app

    resposta = TestClient(create_dashboard_app()).get("/projeto")
    assert resposta.status_code == 200
    assert "MEDIÇÃO DO PROJETO" in resposta.text
