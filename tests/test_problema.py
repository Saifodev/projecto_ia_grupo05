import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from problema import No, caminho
from gerador import SEMENTE


def test_semente_grupo_05():
    assert SEMENTE == 202605


def test_caminho_reconstroi_solucao():
    raiz = No("A")
    n1 = No("B", raiz, "ir", 1.0, 1)
    n2 = No("C", n1, "ir", 2.0, 2)
    assert caminho(n2) == [("ir", "B"), ("ir", "C")]
