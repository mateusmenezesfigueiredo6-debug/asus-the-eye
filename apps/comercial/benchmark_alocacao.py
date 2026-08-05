"""Motor quantico disputando o problema REAL da plataforma.

Ate aqui o engine de benchmark comparava classico, QUBO e QAOA no
demo_portfolio_v1: seis itens com valor e peso inventados. Este script troca o
problema pelo que a plataforma precisa resolver de fato — alocacao de esforco
entre nichos, com valor vindo de demanda prevista, conversao medida e ticket
real — e roda a mesma comparacao.

O ponto nao e torcer para o quantico ganhar. E ter, pela primeira vez, um
numero de vantagem quantica medido sobre um problema do projeto, com a mesma
metrica honesta que o engine ja aplica ao demo.

QPU REAL NAO E TOCADA: o QAOA aqui e simulador local. Hardware da IBM exige
THE_EYE_IBM_EXECUTE=1 e autorizacao explicita do dono.

Uso: python3 apps/comercial/benchmark_alocacao.py [capacidade]
Saida: reports/benchmark/alocacao/latest.json
"""
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE / "apps/comercial"))
sys.path.insert(0, str(BASE / "src"))

from alocacao_quantica import como_problema_benchmark, montar_problema, resolver  # noqa: E402

from asus_theye.benchmark.runner import run_benchmark_suite  # noqa: E402

CAPACIDADE_PADRAO = 20.0


def main(capacidade: float = CAPACIDADE_PADRAO) -> None:
    p = montar_problema()
    itens = p["itens"]
    if not itens:
        print("nenhum nicho com dado suficiente — nada a comparar")
        return

    exato = resolver(itens, capacidade)
    problema = como_problema_benchmark(itens, capacidade)
    print(f"problema real: {problema.name} — {len(problema.values)} nichos, "
          f"capacidade {capacidade}")
    print(f"otimo por busca exaustiva: R$ {exato['valor_esperado_kbrl']:,.1f} mil "
          f"({', '.join(exato['escolhidos'])})")
    print()

    relatorio, caminho = run_benchmark_suite(
        problem=problema,
        output_dir=BASE / "reports/benchmark/alocacao",
    )

    res = relatorio["results"]
    met = relatorio["metrics"]
    print("classico :", res["classical"]["score"], "em",
          f"{res['classical']['execution_time_ms']:.3f} ms")
    print("QUBO     :", res["qubo"].get("variables"), "variaveis em",
          f"{res['qubo'].get('execution_time_ms', 0):.3f} ms")
    print("QAOA     :", res["qaoa"]["score"], "com",
          res["qaoa"].get("shots"), "shots")
    print()
    qar = met["qar"]
    print(f"QAR = {qar['qar']} — {qar['interpretation']}")
    print(f"conclusao: {relatorio['conclusion']}")

    # O confronto que so este script permite: o engine encontrou o mesmo otimo
    # que a busca exaustiva sobre o problema do projeto?
    bate = abs(res["classical"]["score"] - exato["valor_esperado_kbrl"]) < 0.5
    print()
    print(f"classico bate com a busca exaustiva: {bate}")
    if not bate:
        print(f"  engine={res['classical']['score']} vs "
              f"exaustiva={exato['valor_esperado_kbrl']} — divergencia merece olhar")

    resumo = {
        "problema": problema.name,
        "n_nichos": len(problema.values),
        "capacidade": capacidade,
        "otimo_busca_exaustiva": exato,
        "engine_concorda_com_exaustiva": bate,
        "qar": qar,
        "conclusao": relatorio["conclusion"],
        "limitacoes": relatorio["limitations"],
        "relatorio_completo": str(caminho),
    }
    dest = BASE / "reports/benchmark/alocacao/resumo.json"
    dest.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nOK {dest}")


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else CAPACIDADE_PADRAO)
