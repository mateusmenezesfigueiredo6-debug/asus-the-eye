"""Primeira varredura dos campos da MISSAO — o motor da etapa 1 em movimento.

Ate aqui os conectores academicos so haviam rodado sobre termos juridicos, que
sao classificador e nao assunto. Este modulo os roda sobre os campos que a
missao declara: inovacoes em IA, ML, predicao, series temporais, causalidade,
decision intelligence, agentes, robotica, AI for Science, hardware de IA e
computacao quantica.

DESCOBERTA, NAO CONFIRMACAO
A missao e explicita: o objetivo nao e confirmar o ja conhecido. Por isso a
varredura registra, alem do volume por campo, dois sinais de descoberta:

  emergente   campo com poucos trabalhos no Crossref mas muitos preprints no
              arXiv — assinatura de area nova, ainda antes da revisao por pares
  subexposto  campo com producao relevante e poucos periodicos de acesso aberto
              dedicados no DOAJ — material existe mas circula fechado

Nenhum dos dois prova coisa alguma sozinho; sao pistas para investigacao
humana, e o relatorio diz isso.

TERMOS EM INGLES: ROR, Crossref, arXiv e DOAJ sao fontes internacionais. Buscar
"causalidade" nelas devolve quase nada; "causal inference" devolve o campo.

Uso: python3 apps/observatorio/varredura_missao.py
Saida: reports/observatorio/varredura_missao.json
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE / "src"))

from asus_theye.source_graph.connectors.academico import coletar  # noqa: E402

# Os campos vem da MISSAO no AGENTS.md, na ordem em que ela os lista.
CAMPOS = [
    ("artificial intelligence", "IA"),
    ("machine learning", "machine learning"),
    ("prediction", "predicao"),
    ("forecasting", "forecasting"),
    ("time series", "series temporais"),
    ("causal inference", "causalidade"),
    ("decision intelligence", "decision intelligence"),
    ("autonomous agents", "agentes"),
    ("multimodal models", "modelos multimodais"),
    ("robotics", "robotica"),
    ("AI for science", "AI for Science"),
    ("AI hardware accelerator", "hardware de IA"),
    ("quantum computing", "computacao quantica"),
    ("quantum machine learning", "quantum ML"),
    ("hybrid quantum-classical algorithm", "algoritmos hibridos"),
    ("cloud quantum computing", "quantica em nuvem"),
]


def sinais(r: dict) -> dict:
    """Duas pistas de descoberta. Pista nao e prova."""
    cr = (r["resultados"].get("crossref") or {}).get("total") or 0
    ax = (r["resultados"].get("arxiv") or {}).get("total") or 0
    dj = (r["resultados"].get("doaj") or {}).get("total") or 0
    razao = (ax / cr) if cr else None
    return {
        "crossref_titulo": cr, "arxiv_frase": ax, "doaj": dj,
        "razao_preprint_publicado": None if razao is None else round(razao, 5),
    }


def marcar(linhas: list[dict]) -> None:
    """Limiar RELATIVO a distribuicao medida, nao numero escolhido a dedo.

    A primeira versao usava 5% fixo e marcou 16 de 16 campos como emergentes —
    sinal que dispara para tudo nao separa nada. Agora emergente e o campo cuja
    razao passa o terceiro quartil da propria varredura.
    """
    import statistics
    razoes = [x["razao_preprint_publicado"] for x in linhas
              if x["razao_preprint_publicado"] is not None]
    corte = statistics.quantiles(razoes, n=4)[2] if len(razoes) >= 4 else None
    doajs = sorted(x["doaj"] for x in linhas)
    corte_doaj = doajs[len(doajs) // 4] if doajs else 0
    for x in linhas:
        r = x["razao_preprint_publicado"]
        x["emergente"] = bool(corte and r is not None and r > corte)
        x["subexposto"] = bool(x["crossref_titulo"] > 100_000 and x["doaj"] <= corte_doaj)
    return corte, corte_doaj


def main() -> None:
    agora = datetime.now(timezone.utc).isoformat()
    linhas = []
    print(f"varrendo {len(CAMPOS)} campos da missao\n")
    print(f"{'campo':<26} {'crossref':>10} {'arxiv':>8} {'doaj':>6}  sinais")
    print("-" * 72)

    for termo, rotulo in CAMPOS:
        r = coletar(termo, limite=3)
        s = sinais(r)
        linhas.append({
            "termo": termo, "rotulo": rotulo, **s,
            "instituicoes_ror": (r["resultados"].get("ror") or {}).get("total"),
            "conectores_com_falha": r["conectores_com_falha"],
            "amostra_arxiv": [i.get("titulo") for i in
                              (r["resultados"].get("arxiv") or {}).get("itens", [])[:2]],
            "proveniencia": {k: v["proveniencia"] for k, v in r["resultados"].items()},
        })
        print(f"{rotulo:<26} {s['crossref_titulo']:>10,} {s['arxiv_frase']:>8,} "
              f"{s['doaj']:>6}")

    corte, corte_doaj = marcar(linhas)
    print(f"\nlimiares desta varredura: razao > {corte:.4f} (Q3), doaj <= {corte_doaj}")
    for x in linhas:
        marcas = [m for m, v in (("emergente", x["emergente"]),
                                 ("subexposto", x["subexposto"])) if v]
        if marcas:
            print(f"  {x['rotulo']:<26} {' '.join(marcas)}")

    emergentes = [x for x in linhas if x["emergente"]]
    subexpostos = [x for x in linhas if x["subexposto"]]
    saida = {
        "gerado_em_utc": agora,
        "origem_dos_campos": "MISSAO declarada no topo do AGENTS.md",
        "fontes": ["ROR", "Crossref", "arXiv", "DOAJ"],
        "nota_metodo": (
            "razao preprint/publicado e contagem de periodicos abertos sao PISTAS "
            "de descoberta, nunca prova. Volume de publicacao nao mede qualidade "
            "nem importancia, e a missao proibe ranquear por metrica social."),
        "campos": len(linhas),
        "limiar_emergente_q3": corte,
        "limiar_doaj_q1": corte_doaj,
        "casamento": {"arxiv": "frase exata", "crossref": "titulo, palavras soltas",
                      "aviso": ("o Crossref nao suporta busca por frase; os numeros "
                                "dele sao maiores que a realidade do termo")},
        "emergentes": [x["rotulo"] for x in emergentes],
        "subexpostos": [x["rotulo"] for x in subexpostos],
        "linhas": sorted(linhas, key=lambda x: -(x["razao_preprint_publicado"] or 0)),
    }
    dest = BASE / "reports/observatorio/varredura_missao.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nOK {dest.relative_to(BASE)}")
    print(f"  emergentes (muito preprint p/ pouco publicado): {saida['emergentes']}")
    print(f"  subexpostos (producao alta, pouco acesso aberto): {saida['subexpostos']}")


if __name__ == "__main__":
    main()
