# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""O painel de garantias não pode vazar (CPF, conteúdo de elo) nem abrir rede."""
import re

from asus_theye.audit.dados_pessoais import achar_cpf
from asus_theye.dashboard.garantias import garantias_page


def _snapshot(**sobrescreve):
    s = {
        "gerado_em": "2026-09-04T09:00:00+00:00",
        "corrente": {"elos": 352, "integridade": "íntegra", "vigilia": 139, "sessoes": 2028,
                     "ultimos": [{"seq": 351, "ts": "2026-09-04T04:55:10", "event": "portal_civico.andamento_pdf.fundo_explicito"}]},
        "vigia": {"estado": "active", "baseline": "baseline: 1219 arquivos", "imediatos": 0, "digests": 0},
        "sentinela": "active",
        "email": {"smtp": False, "fila": 95},
        "permissoes": {"abertos": 0},
        "rede": {"fora_loopback": ["0.0.0.0:22"], "portas_eye": ["127.0.0.1:3210"]},
        "vermelhos": {"conectores_ligados": 56, "conectores_total": 89},
        "ancoras": {"ots_instalado": True, "onchain_autorizada": False, "ultima": None},
        "termo": {"arquivo": None, "sha256": None},
        "achados": None,
    }
    s.update(sobrescreve)
    return s


def test_renderiza_sem_script_sem_rede_sem_cpf():
    h = garantias_page(_snapshot())
    assert "<script" not in h.lower()
    assert not re.search(r'(src|href)="https?://', h), "painel não pode carregar nada de fora"
    assert achar_cpf(h) == []
    assert "352 elos" in h and "íntegra" in h
    assert "SEM smtp.env" in h and "95 alerta" in h
    assert "56/89" in h


def test_achados_da_auditoria_entram_como_tabela_com_comando_escapado():
    ach = [{"gravidade": "vermelho", "dimensao": "git", "titulo": "56 conectores ligados por sessão-irmã",
            "quem_resolve": "titular", "comando": "git checkout a113557~1 -- data/source-graph/connectors.json && git commit -m 'x'"}]
    h = garantias_page(_snapshot(achados=ach))
    assert "Achados da auditoria" in h
    assert "sessão-irmã" in h
    assert "&amp;&amp;" in h, "comando tem de sair escapado"


def test_vermelho_e_verde_mudam_a_cor_do_card():
    h_ok = garantias_page(_snapshot(vermelhos={"conectores_ligados": 0, "conectores_total": 89}))
    h_ko = garantias_page(_snapshot())
    assert h_ok.count("#2e7d32") > h_ko.count("#2e7d32")
    assert h_ko.count("#c62828") > h_ok.count("#c62828")


def test_termo_ausente_e_presente():
    assert "ainda não redigido" in garantias_page(_snapshot())
    h = garantias_page(_snapshot(termo={"arquivo": "TERMO-EXCLUSIVIDADE-2026-09-04.md", "sha256": "ab" * 32}))
    assert "TERMO-EXCLUSIVIDADE" in h and "abababab" in h
