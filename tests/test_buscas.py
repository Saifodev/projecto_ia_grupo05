import pytest

from buscas import (a_estrela, ara_estrela, bfs, dfs, executar, factor_ramificacao, gulosa, ids, ucs)
from conftest import ProblemaGrafo, instancia_ta, instancia_tb, instancia_tc, problema
from dominio import DIRECCOES
from problema import Problema, caminho

# A -> G custa 10 numa acção; A -> B -> C -> G custa 3 em três acções.
ARESTAS = {"A": {"B": 1, "G": 10}, "B": {"C": 1}, "C": {"G": 1}}


def grafo():
    return ProblemaGrafo(ARESTAS, "A", {"G"}, h={"A": 3, "B": 2, "C": 1, "G": 0})


def estados(no):
    return [s for _, s in caminho(no)]


def test_bfs_minimiza_accoes_e_nao_o_custo():
    assert estados(bfs(grafo())) == ["G"] and bfs(grafo()).g == 10
    assert ucs(grafo()).g == 3


def test_dfs_respeita_o_limite_de_profundidade():
    cadeia = ProblemaGrafo({"A": {"B": 1}, "B": {"C": 1}, "C": {"D": 1}}, "A", {"D"})
    assert dfs(cadeia, limite=2) is None
    assert estados(dfs(cadeia, limite=3)) == ["B", "C", "D"]


def test_dfs_nao_repete_estados_no_caminho():
    ciclo = ProblemaGrafo({"A": {"B": 1}, "B": {"A": 1, "C": 1}, "C": {}}, "A", {"Z"})
    assert dfs(ciclo) is None  # termina apesar do ciclo A <-> B


def test_ids_conta_reexpansoes():
    cadeia = ProblemaGrafo({"A": {"B": 1}, "B": {"C": 1}}, "A", {"C"})
    r = executar("ids", cadeia)
    # limites 0, 1, 2: 0 + 1 + 2 expansões; as anteriores à última são 1.
    assert estados(r.no) == ["B", "C"]
    assert (r.expandidos, r.reexpandidos) == (3, 1)


def test_gulosa_e_a_estrela_no_grafo():
    assert gulosa(grafo(), "h1") is not None
    assert a_estrela(grafo(), "h1").g == 3


def test_instancia_sem_solucao():
    p = problema(instancia_tc())
    for nome, h in [("bfs", None), ("ucs", None), ("a_estrela", "h2"), ("ara_estrela", "h2")]:
        assert executar(nome, p, h).estado == "sem_solucao"


@pytest.mark.parametrize("vento", list(DIRECCOES))
def test_a_estrela_e_ucs_devolvem_o_mesmo_custo(vento):
    p = problema(instancia_ta(vento))
    optimo = ucs(p).g
    for h in ("h0", "h1", "h2"):
        assert a_estrela(p, h).g == pytest.approx(optimo)


def test_a_estrela_e_ucs_com_subidas():
    p = problema(instancia_tb())
    assert a_estrela(p, "h2").g == pytest.approx(ucs(p).g)


def test_solucao_devolvida_e_valida():
    p = problema(instancia_ta())
    no = a_estrela(p, "h2")
    s, g = p.estado_inicial(), 0.0
    for a, s2 in caminho(no):
        assert a in p.accoes(s) and p.resultado(s, a) == s2
        g += p.custo(s, a, s2)
        s = s2
    assert p.e_objectivo(s) and g == pytest.approx(no.g)


@pytest.mark.parametrize("h", ["h1", "h2"])
def test_ara_estrela_melhora_e_respeita_o_limite(h):
    p = problema(instancia_ta("NE"))
    optimo = ucs(p).g
    r = executar("ara_estrela", p, h)
    custos = [c for _, c, _, _, _ in r.curva]
    assert all(a >= b for a, b in zip(custos, custos[1:]))
    assert r.custo == pytest.approx(optimo)
    for _, custo, eps, eps_linha, _ in r.curva:
        assert custo <= eps * optimo + 1e-9
        if eps_linha is not None:
            assert custo <= eps_linha * optimo + 1e-9


def test_ara_estrela_com_peso_1_coincide_com_a_estrela():
    p = problema(instancia_ta())
    assert ara_estrela(p, "h2", pesos=(1.0,)).g == pytest.approx(a_estrela(p, "h2").g)


class Infinito(Problema):
    def estado_inicial(self):
        return 0

    def accoes(self, s):
        return [1, 2]

    def resultado(self, s, a):
        return 2 * s + a

    def custo(self, s, a, s2):
        return 1.0

    def e_objectivo(self, s):
        return False


def test_limite_de_tempo_fica_registado_como_falha():
    r = executar("bfs", Infinito(), limite_tempo=0.05)
    assert r.estado == "falhou_tempo" and r.no is None


def test_limite_de_memoria_fica_registado_como_falha():
    r = executar("bfs", Infinito(), limite_tempo=30, limite_memoria_mb=1)
    assert r.estado == "falhou_memoria"


def test_factor_de_ramificacao():
    assert factor_ramificacao(5, 1) == pytest.approx(5)
    assert factor_ramificacao(6, 2) == pytest.approx(2)   # 1 + 2 + 4 = 7
    assert factor_ramificacao(3, 5) == 1.0


def test_buscas_nao_informadas_no_drone():
    from conftest import instancia_td
    p = problema(instancia_td())
    optimo = ucs(p).g
    for no in (bfs(p), dfs(p, limite=20), ids(p)):
        s = p.estado_inicial()
        for a, s2 in caminho(no):
            assert a in p.accoes(s)
            s = s2
        assert p.e_objectivo(s) and no.g >= optimo - 1e-9


class Contador(ProblemaGrafo):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.expansoes = {}

    def accoes(self, s):
        self.expansoes[s] = self.expansoes.get(s, 0) + 1
        return super().accoes(s)


def test_gulosa_nao_reabre_estados_fechados():
    # B é fechado primeiro (h = 0) com g = 10; depois C encontra B com g = 2.
    arestas = {"A": {"B": 10, "C": 1}, "C": {"B": 1}, "B": {"D": 1}, "D": {}}
    p = Contador(arestas, "A", {"D"}, h={"A": 9, "B": 0, "C": 1, "D": 5})
    gulosa(p, "h1")
    assert p.expansoes.get("B", 0) == 1


def test_curva_do_ara_sem_pontos_repetidos():
    p = problema(instancia_ta("NE"))
    r = executar("ara_estrela", p, "h2")
    pares = [(c, el) for _, c, _, el, _ in r.curva]
    assert all(a != b for a, b in zip(pares, pares[1:]))


def test_factor_de_ramificacao_com_solucoes_longas():
    b = factor_ramificacao(100000, 200)
    assert 1.0 < b < 1.1
