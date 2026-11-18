"""Admissibilidade e consistência de h1 e h2 em todos os estados alcançáveis
de instâncias reduzidas, com h* calculado pelo próprio projecto."""
import pytest

import heuristicas
from conftest import custos_optimos, instancia_ta, instancia_tb, instancia_td, problema
from dominio import DIRECCOES, Estado

CASOS = [instancia_ta(v) for v in DIRECCOES] + [instancia_tb(v) for v in ("N", "E", "SO")]


@pytest.fixture(scope="module", params=range(len(CASOS)))
def caso(request):
    p = problema(CASOS[request.param])
    h_estrela, arestas = custos_optimos(p)
    return p, h_estrela, arestas


@pytest.mark.parametrize("nome", ["h1", "h2"])
def test_admissivel_em_todos_os_estados(caso, nome):
    p, h_estrela, _ = caso
    for s, custo in h_estrela.items():
        assert p.heuristica(s, nome) <= custo + 1e-9, (s, nome)


@pytest.mark.parametrize("nome", ["h1", "h2"])
def test_consistente_em_todas_as_arestas(caso, nome):
    p, _, arestas = caso
    for s, a, s2, c in arestas:
        assert p.heuristica(s, nome) <= c + p.heuristica(s2, nome) + 1e-9, (s, a, nome)


def test_zero_nos_objectivos_e_dominancia(caso):
    p, h_estrela, _ = caso
    for s in h_estrela:
        if p.e_objectivo(s):
            assert p.heuristica(s, "h1") == pytest.approx(0) and p.heuristica(s, "h2") == pytest.approx(0)
        assert p.heuristica(s, "h2") >= p.heuristica(s, "h1") - 1e-9


def test_h2_igual_ao_percurso_simetrico_mais_potencial():
    """h2(s) = L_sim(s) + φ(B) − φ(p), com φ = 0,5·(x, y)·w + 0,75·z e L_sim
    calculado com os pesos simétricos |m| no plano e 1,25 na vertical."""
    p = problema(instancia_tb("SE"))

    def peso_simetrico(accao, mov):
        if accao in ("subir", "descer"):
            return 1.25
        return heuristicas.peso_sem_vento(accao, mov) * 2

    def phi(x, y, z):
        return 0.5 * (x * p.w[0] + y * p.w[1]) + 0.75 * z

    tabelas = heuristicas.preparar(p, peso_simetrico)
    for s in [Estado(0, 1, 2, 0, 10, 0), Estado(2, 0, 3, 0, 10, 0), Estado(2, 1, 1, 0, 10, 1)]:
        esperado = heuristicas.limite_percurso(p, s, tabelas) + phi(0, 1, 1) - phi(s.x, s.y, s.z)
        assert p.heuristica(s, "h2") == pytest.approx(esperado)


def test_contra_exemplo_da_heuristica_sem_vento():
    """Com custo horizontal 1 (sem vento), a estimativa sobrestima a favor do
    vento: não é admissível."""
    p = problema(instancia_td("E"))
    s = Estado(1, 0, 1, p.capacidade, 10, 1)
    h_estrela = p.custo(s, "O", p.resultado(s, "O"))
    sem_vento = 1.0  # um movimento horizontal de comprimento 1
    assert h_estrela == pytest.approx(0.5) and sem_vento > h_estrela
    assert p.heuristica(s, "h2") <= h_estrela + 1e-9


def test_distancias_dirigidas_e_com_obstaculos():
    p = problema(instancia_ta("E"))
    ate = p.tabelas["h2"]["ate"]
    assert ate[(2, 1, 1)][(0, 0, 1)] != ate[(0, 0, 1)][(2, 1, 1)]
    # TB: a parede de relevo obriga a subir e descer (2 + 0,5) além do troço plano.
    q = problema(instancia_tb("N"))
    assert q.tabelas["h2"]["ate"][(2, 1, 1)][(0, 1, 1)] == pytest.approx(2 + 2.5)


def test_heuristica_conta_os_regressos_para_reabastecer():
    # TA: parcelas de 2 L e 3 L, tanque de 4 L. Sem líquido, o drone tem de
    # ir à base antes de pulverizar, o que custa mais do que pulverizar já.
    p = problema(instancia_ta("N", bateria=100))
    com_liquido = Estado(2, 1, 1, p.capacidade, 4, 0)
    sem_liquido = Estado(2, 1, 1, p.capacidade, 0, 0)
    for nome in ("h1", "h2"):
        assert p.heuristica(sem_liquido, nome) > p.heuristica(com_liquido, nome)
