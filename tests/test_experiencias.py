import csv

import pandas as pd

import experiencias
from conftest import instancia_td


def test_csv_tem_uma_linha_por_execucao(tmp_path):
    inst = dict(instancia_td(), nome="td", nivel="teste")
    ficheiro = tmp_path / "execucoes.csv"
    curva = tmp_path / "curva.csv"
    configs = [("ucs", None), ("a_estrela", "h2"), ("ara_estrela", "h2")]
    experiencias.correr([inst], ficheiro, configs, curva=curva)
    with open(ficheiro, encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    assert [l["algoritmo"] for l in linhas] == ["ucs", "a_estrela", "ara_estrela"]
    assert set(linhas[0]) == set(experiencias.COLUNAS)
    assert all(l["estado"] == "ok" for l in linhas)
    assert len({round(float(l["energia"]), 9) for l in linhas}) == 1
    with open(curva, encoding="utf-8") as f:
        assert len(list(csv.DictReader(f))) >= 1


def test_optimo_so_quando_os_algoritmos_exactos_concordam():
    df = pd.DataFrame([
        {"instancia": "a", "algoritmo": "ucs", "estado": "ok", "energia": 10.0},
        {"instancia": "a", "algoritmo": "a_estrela", "estado": "ok", "energia": 10.0},
        {"instancia": "a", "algoritmo": "gulosa", "estado": "ok", "energia": 12.0},
        {"instancia": "b", "algoritmo": "ucs", "estado": "ok", "energia": 5.0},
        {"instancia": "b", "algoritmo": "a_estrela", "estado": "ok", "energia": 6.0},
        {"instancia": "c", "algoritmo": "ucs", "estado": "falhou_tempo", "energia": None},
    ])
    assert experiencias.optimos(df) == {"a": 10.0}
