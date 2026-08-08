"""Integração offline dos conectores acadêmicos com o fetcher educado."""

from __future__ import annotations

import hashlib

from asus_theye.source_graph.connectors import academico
from asus_theye.source_graph.fetcher import FetchError, FetchResult, PoliteFetcher


class FakeFetcher:
    def __init__(self, result: FetchResult | Exception) -> None:
        self.result = result
        self.urls: list[str] = []

    def get(self, url: str) -> FetchResult:
        self.urls.append(url)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def resultado(conector: str, url: str, body: bytes) -> FetchResult:
    return FetchResult(
        url=url,
        status=200,
        retrieved_at="2026-08-08T12:00:00Z",
        content_hash_sha256=hashlib.sha256(body).hexdigest(),
        content_type="application/json",
        byte_length=len(body),
        body=body,
        license_id="CC0-1.0",
        robots_decision="api_terms:https://example.invalid/terms",
        connector_id=conector,
        retries=0,
        waited_seconds=0.0,
    )


def test_ror_usa_polite_fetcher_e_preserva_proveniencia_exata(monkeypatch):
    body = b'{"number_of_results": 1, "items": []}'
    url_final = "https://api.ror.org/organizations?query=causal%20inference"
    fake = FakeFetcher(resultado("ror", url_final, body))
    monkeypatch.setitem(academico.FETCHERS, "ror", fake)

    resposta = academico.ror("causal inference")

    assert fake.urls == [url_final]
    assert resposta["proveniencia"] == {
        "conector": "ror",
        "url": url_final,
        "coletado_em_utc": "2026-08-08T12:00:00Z",
        "sha256_resposta": hashlib.sha256(body).hexdigest(),
    }


def test_arxiv_mantem_aspas_da_frase_exata_no_fetcher(monkeypatch):
    body = b"<feed><opensearch:totalResults>0</opensearch:totalResults></feed>"
    fake = FakeFetcher(resultado("arxiv", "https://export.arxiv.org/result", body))
    monkeypatch.setitem(academico.FETCHERS, "arxiv", fake)

    resposta = academico.arxiv("quantum machine learning")

    assert "search_query=all:%22quantum%20machine%20learning%22" in fake.urls[0]
    assert resposta["casamento"] == "frase exata"


def test_crossref_mantem_declaracao_de_que_nao_suporta_frase(monkeypatch):
    body = b'{"message": {"total-results": 0, "items": []}}'
    fake = FakeFetcher(resultado("crossref", "https://api.crossref.org/result", body))
    monkeypatch.setitem(academico.FETCHERS, "crossref", fake)

    resposta = academico.crossref("AI for Science")

    assert "nao suporta frase" in resposta["casamento"]


def test_fetchers_de_producao_sao_educados():
    assert set(academico.FETCHERS) == {"ror", "crossref", "arxiv", "doaj"}
    assert all(isinstance(fetcher, PoliteFetcher) for fetcher in academico.FETCHERS.values())


def test_falha_de_um_conector_fica_registrada_sem_derrubar_os_outros(monkeypatch):
    def falha(_termo, _limite):
        raise academico.ConectorError("fonte indisponivel")

    def sucesso(_termo, _limite):
        return {"total": 1}

    monkeypatch.setattr(academico, "CONECTORES", {"falho": falha, "ok": sucesso})

    resposta = academico.coletar("teste")

    assert resposta["conectores_ok"] == ["ok"]
    assert resposta["conectores_com_falha"] == {"falho": "fonte indisponivel"}
    assert resposta["resultados"] == {"ok": {"total": 1}}


def test_falha_do_polite_fetcher_vira_falha_registrada_do_conector(monkeypatch):
    fake = FakeFetcher(FetchError("tempo esgotado"))
    monkeypatch.setitem(academico.FETCHERS, "ror", fake)
    monkeypatch.setattr(academico, "CONECTORES", {"ror": academico.ror})

    resposta = academico.coletar("teste")

    assert resposta["conectores_ok"] == []
    assert "FetchError" in resposta["conectores_com_falha"]["ror"]
    assert resposta["resultados"] == {}
