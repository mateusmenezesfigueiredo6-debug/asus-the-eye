# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
O que se prova aqui não é que HMAC funciona — é que sha256 puro NÃO serve para
este objeto, e que o desenho corrigido serve. O auditor-de-sabotagem pegou o
defeito em 04/09/2026 no plano; este arquivo existe para que ele não volte.
"""
import hashlib
import hmac
import math
import os

import pytest

from asus_theye.audit.commitment import (
    CASAS,
    CHAVE_ABERTURA,
    NONCE_BYTES,
    CommitmentError,
    comprometer,
    comprometer_lote,
    raiz_merkle,
    revelar,
    revelar_lote,
    serializar_canonico,
)

# ---------------------------------------------------------------- canônico


def test_serializacao_ignora_ordem_de_chaves_e_arredonda():
    a = {"b": 0.54321, "a": {"y": 1, "x": [0.123456, 2]}}
    b = {"a": {"x": [0.1235, 2], "y": 1}, "b": 0.5432}
    assert serializar_canonico(a) == serializar_canonico(b)
    assert serializar_canonico(a) == b'{"a":{"x":[0.1235,2],"y":1},"b":0.5432}'


def test_serializacao_rejeita_nan_e_inf():
    for ruim in (math.nan, math.inf, -math.inf):
        with pytest.raises(CommitmentError):
            serializar_canonico({"p": ruim})


def test_serializacao_exige_dict():
    with pytest.raises(CommitmentError):
        serializar_canonico([1, 2])  # type: ignore[arg-type]


def test_bool_nao_vira_float():
    # bool é subclasse de int; round(True) daria 1 e mudaria o payload.
    assert serializar_canonico({"ok": True}) == b'{"ok":true}'


# ---------------------------------------------------------------- comprometer


def test_nonce_curto_e_rejeitado():
    with pytest.raises(CommitmentError):
        comprometer({"p": 0.5}, nonce=b"curto")


def test_mesmo_prognostico_nonces_diferentes_dao_C_diferentes():
    p = {"A": 0.54, "B": 0.46}
    c1, n1 = comprometer(p)
    c2, n2 = comprometer(p)
    assert n1 != n2
    assert c1 != c2
    assert len(n1) == NONCE_BYTES


def test_revelar_bate_com_nonce_certo_e_falha_com_errado():
    p = {"A": 0.54, "B": 0.46}
    c, n = comprometer(p)
    assert revelar(c, p, n) is True
    assert revelar(c, p, os.urandom(NONCE_BYTES)) is False
    assert revelar(c, {"A": 0.55, "B": 0.45}, n) is False
    assert revelar(c, p, b"curto") is False  # não levanta, devolve False


def test_terceiro_recomputa_so_com_stdlib():
    """A revelação tem de ser verificável sem importar nada nosso."""
    p = {"A": 0.54, "B": 0.46}
    c, n = comprometer(p)
    import json

    canon = json.dumps(p, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    assert hmac.new(n, canon, hashlib.sha256).hexdigest() == c


# ---------------------------------------------------------------- força bruta


def _espaco_plausivel():
    """10 rótulos × 10.001 probabilidades a 4 casas ≈ 10^5 mensagens."""
    for nome in "ABCDEFGHIJ":
        for i in range(10_001):
            yield {nome: i / 10_000}


def test_sha256_puro_e_quebrado_por_forca_bruta_em_10e5():
    """A metade que prova o defeito: sem nonce, o hash é lido em segundos."""
    alvo = {"G": 0.6123}
    h = hashlib.sha256(serializar_canonico(alvo)).hexdigest()
    achado = None
    for cand in _espaco_plausivel():
        if hashlib.sha256(serializar_canonico(cand)).hexdigest() == h:
            achado = cand
            break
    assert achado == alvo, "sha256 puro deveria ter sido quebrado — o espaço é minúsculo"


def test_hmac_com_nonce_resiste_a_mesma_forca_bruta():
    """A metade que prova a correção: sem o nonce, o mesmo espaço não rende nada."""
    alvo = {"G": 0.6123}
    c, _nonce_secreto = comprometer(alvo)
    # O atacante não tem o nonce. O melhor que consegue é chutar um.
    chute = bytes(NONCE_BYTES)
    for cand in _espaco_plausivel():
        assert hmac.new(chute, serializar_canonico(cand), hashlib.sha256).hexdigest() != c
        assert hashlib.sha256(serializar_canonico(cand)).hexdigest() != c


# ---------------------------------------------------------------- merkle


def test_raiz_merkle_deterministica_e_independente_da_ordem():
    f = ["a" * 64, "b" * 64, "c" * 64]
    assert raiz_merkle(f) == raiz_merkle(list(reversed(f)))
    assert raiz_merkle([]) == "0" * 64
    assert raiz_merkle(["x" * 64]) == "x" * 64  # folha única é a própria raiz


def test_raiz_merkle_muda_se_uma_folha_muda():
    f = ["a" * 64, "b" * 64, "c" * 64]
    g = ["a" * 64, "b" * 64, "d" * 64]
    assert raiz_merkle(f) != raiz_merkle(g)


def test_raiz_merkle_bate_com_ancorar_politica():
    """A âncora externa já existente usa este desenho; se divergir, ela não
    entende nossa raiz."""
    import importlib.util
    from pathlib import Path

    src = Path.home() / ".the-eye" / "ancorar_politica.py"
    if not src.exists():
        pytest.skip("ancorar_politica.py ausente nesta máquina")
    spec = importlib.util.spec_from_file_location("anc", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    f = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(7)]
    assert mod.raiz_merkle(f) == raiz_merkle(f)


# ---------------------------------------------------------------- lote


def _lote():
    progs = {
        "presidente": {"A": 0.54, "B": 0.46},
        "governador-sp": {"X": 0.61, "Y": 0.39},
        "senador-mg": {"P": 0.33, "Q": 0.33, "R": 0.34},
    }
    lote, nonces = comprometer_lote(progs, data_calculo="2026-09-04", data_abertura="2026-10-26")
    return progs, lote, nonces


def test_lote_publica_n_folhas_e_esquema_mas_nao_o_prognostico():
    progs, lote, nonces = _lote()
    pl = lote.payload()
    assert pl["n_folhas"] == 3
    assert pl["esquema_nomes"] == sorted(progs)
    assert pl["data_abertura"] == "2026-10-26"
    texto = str(pl)
    assert "0.54" not in texto and "0.61" not in texto, "prognóstico vazou no payload"
    for n in nonces.values():
        assert n.hex() not in texto, "nonce vazou no payload"


def test_lote_injeta_data_de_abertura_no_payload_comprometido():
    """Regra 8 do plano: revelar com outra data não bate."""
    progs, lote, nonces = _lote()
    pl = lote.payload()
    assert all(revelar_lote(pl, progs, nonces).values())
    pl_outra = dict(pl, data_abertura="2026-10-05")
    assert not any(revelar_lote(pl_outra, progs, nonces).values())


def test_lote_rejeita_abertura_divergente_dentro_de_uma_corrida():
    progs = {"x": {"A": 0.5, CHAVE_ABERTURA: "2026-01-01"}}
    with pytest.raises(CommitmentError):
        comprometer_lote(progs, data_calculo="2026-09-04", data_abertura="2026-10-26")


def test_revelacao_parcial_aparece_como_false_nunca_some():
    progs, lote, nonces = _lote()
    pl = lote.payload()
    so_duas = {k: v for k, v in progs.items() if k != "senador-mg"}
    r = revelar_lote(pl, so_duas, nonces)
    assert set(r) == set(progs), "toda corrida do esquema tem de aparecer no resultado"
    assert r["senador-mg"] is False
    assert r["presidente"] is True


def test_raiz_adulterada_derruba_o_lote_inteiro():
    progs, lote, nonces = _lote()
    pl = lote.payload()
    pl["raiz_merkle"] = "f" * 64
    assert not any(revelar_lote(pl, progs, nonces).values())


def test_lote_vazio_e_datas_ausentes_sao_erro():
    with pytest.raises(CommitmentError):
        comprometer_lote({}, data_calculo="2026-09-04", data_abertura="2026-10-26")
    with pytest.raises(CommitmentError):
        comprometer_lote({"x": {"A": 1.0}}, data_calculo="", data_abertura="2026-10-26")


def test_casas_e_bytes_sao_os_publicados():
    # Se alguém mudar estas constantes, toda revelação passada quebra.
    assert CASAS == 4
    assert NONCE_BYTES == 32
