"""Testes da auth mínima do dashboard — a garantia fail-closed da F5."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from asus_theye.dashboard.app import create_dashboard_app  # noqa: E402
from asus_theye.dashboard.auth import AuthConfigError, registrar_auth  # noqa: E402

TOKEN = "token-forte-de-teste-0123456789"


def test_require_auth_sem_token_recusa_subir(monkeypatch: pytest.MonkeyPatch) -> None:
    """A trava central: exigir auth sem token configurado LEVANTA — nunca sobe aberto."""
    monkeypatch.delenv("THE_EYE_DASHBOARD_TOKEN", raising=False)
    with pytest.raises(AuthConfigError, match="autenticação"):
        create_dashboard_app(require_auth=True)


def test_sem_token_e_sem_require_sobe_local_sem_guarda(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("THE_EYE_DASHBOARD_TOKEN", raising=False)
    app = create_dashboard_app(require_auth=False)  # dev local explícito
    client = TestClient(app)
    assert client.get("/health").status_code == 200


def test_com_token_bloqueia_sem_bearer_e_libera_com_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("THE_EYE_DASHBOARD_TOKEN", TOKEN)
    app = create_dashboard_app(require_auth=True)
    client = TestClient(app)
    # /health é sempre livre (liveness não expõe dado)
    assert client.get("/health").status_code == 200
    # rota protegida sem token -> 401
    assert client.get("/markets").status_code == 401
    # token errado -> 401
    assert client.get("/markets", headers={"authorization": "Bearer errado"}).status_code == 401
    # token certo -> passa (200; a página degrada sozinha se não houver banco)
    ok = client.get("/markets", headers={"authorization": f"Bearer {TOKEN}"})
    assert ok.status_code == 200


def test_registrar_auth_sem_require_e_sem_token_e_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("THE_EYE_DASHBOARD_TOKEN", raising=False)
    from fastapi import FastAPI

    app = FastAPI()
    registrar_auth(app, require=False)  # não deve levantar nem instalar guarda
    assert TestClient(app).get("/health").status_code in (200, 404)  # sem rotas ainda
