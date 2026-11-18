import math

import pytest

from buscas import ucs
from conftest import instancia_ta, instancia_tb, instancia_td, problema
from dominio import DIRECCOES, Estado, custo_horizontal, solucao_construtiva, unidades, vector_vento


def test_sucessores_do_estado_inicial_conhecido():
    p = problema(instancia_ta())
    assert set(p.accoes(p.estado_inicial())) == {"N", "NE", "E", "subir"}


def test_custos_do_vento_contra_a_favor_e_perpendicular():
    w = vector_vento("E")  # vento de Leste: sopra para Oeste
    assert custo_horizontal(1, 0, w) == pytest.approx(1.5)
    assert custo_horizontal(-1, 0, w) == pytest.approx(0.5)
    assert custo_horizontal(0, 1, w) == pytest.approx(1.0)
    assert custo_horizontal(1, 1, w) == pytest.approx(math.sqrt(2) * (1 + 0.5 * math.cos(math.pi / 4)))


def test_custos_com_vento_diagonal():
    w = vector_vento("NE")
    assert custo_horizontal(1, 1, w) == pytest.approx(1.5 * math.sqrt(2))
    assert custo_horizontal(-1, -1, w) == pytest.approx(0.5 * math.sqrt(2))
    assert custo_horizontal(1, 0, w) == pytest.approx(1 + 0.5 * math.sqrt(2) / 2)


@pytest.mark.parametrize("vento", list(DIRECCOES))
def test_ida_e_volta_soma_o_custo_simetrico(vento):
    w = vector_vento(vento)
    for dx, dy in DIRECCOES.values():
        ida_volta = custo_horizontal(dx, dy, w) + custo_horizontal(-dx, -dy, w)
        assert ida_volta == pytest.approx(2 * math.hypot(dx, dy))


def test_subir_e_descer():
    p = problema(instancia_tb())
    s = p.estado_inicial()
    s2 = p.resultado(s, "subir")
    assert (s2.z, p.custo(s, "subir", s2)) == (2, 2.0)
    s3 = p.resultado(s2, "descer")
    assert (s3.z, p.custo(s2, "descer", s3)) == (1, 0.5)


def test_percurso_fechado_custa_o_mesmo_com_qualquer_vento():
    percurso = ["E", "NE", "N", "O", "SO", "S"]
    custos = []
    for vento in DIRECCOES:
        p = problema(instancia_ta(vento, bateria=100))
        s, g = p.estado_inicial(), 0.0
        for a in percurso:
            s2 = p.resultado(s, a)
            g += p.custo(s, a, s2)
            s = s2
        assert (s.x, s.y) == (0, 0)
        custos.append(g)
    assert max(custos) - min(custos) == pytest.approx(0.0, abs=1e-12)


def test_limites_de_altitude_e_relevo():
    p = problema(instancia_tb())
    s = p.estado_inicial()  # (0, 1, 1), parede de relevo em x = 1
    assert "E" not in p.accoes(s) and "descer" not in p.accoes(s)
    topo = Estado(0, 1, 3, s.bateria, s.litros, 0)
    assert "subir" not in p.accoes(topo)
    alto = Estado(0, 1, 2, s.bateria, s.litros, 0)
    assert "E" in p.accoes(alto)


def test_zona_proibida_em_todos_os_niveis_e_cantos():
    inst = instancia_ta(proibidas=[{"x": [1, 1], "y": [0, 0]}])
    p = problema(inst)
    for z in (1, 2):
        assert not p.livre(1, 0, z)
    s = p.estado_inicial()
    # (1, 0) bloqueada: a diagonal NE corta o canto e fica proibida.
    assert "NE" not in p.accoes(s) and "E" not in p.accoes(s)


def test_pulverizar_so_no_nivel_1_com_liquido():
    p = problema(instancia_ta())
    cheio = p.capacidade
    sobre = Estado(2, 1, 1, cheio, 4, 0)
    assert "pulverizar" in p.accoes(sobre)
    assert "pulverizar" not in p.accoes(Estado(2, 1, 2, cheio, 4, 0))
    assert "pulverizar" not in p.accoes(Estado(2, 1, 1, cheio, 1, 0))
    assert "pulverizar" not in p.accoes(Estado(2, 1, 1, cheio, 4, 0b01))
    depois = p.resultado(sobre, "pulverizar")
    assert (depois.litros, depois.feitas) == (2, 0b01)


def test_recarregar_e_reabastecer():
    p = problema(instancia_ta())
    assert "recarregar" in p.accoes(Estado(3, 3, 1, 5, 4, 0))
    assert "reabastecer" not in p.accoes(Estado(3, 3, 1, 5, 1, 0))
    na_base = Estado(0, 0, 1, 5, 1, 0)
    assert {"recarregar", "reabastecer"} <= set(p.accoes(na_base))
    assert p.resultado(na_base, "recarregar").bateria == p.capacidade
    assert p.resultado(na_base, "reabastecer").litros == 4
    assert "recarregar" not in p.accoes(p.estado_inicial())


def test_consumo_arredondado_por_excesso():
    assert unidades(0.5, 0.25) == 2
    assert unidades(2.0, 0.25) == 8
    assert unidades(1 - 0.5 * math.sqrt(2) / 2, 0.25) == 3
    p = problema(instancia_td())
    pouca = Estado(0, 0, 1, 5, 10, 0)  # 1,25 de energia; E custa 1,5
    assert "E" not in p.accoes(pouca)


def test_estado_imutavel_e_hashable():
    a = Estado(1, 2, 1, 10, 4, 3)
    assert a == Estado(1, 2, 1, 10, 4, 3) and hash(a) == hash(Estado(1, 2, 1, 10, 4, 3))
    with pytest.raises(AttributeError):
        a.x = 5


def test_objectivo_exige_parcelas_e_base_no_nivel_1():
    p = problema(instancia_ta())
    assert p.e_objectivo(Estado(0, 0, 1, 0, 0, 0b11))
    assert not p.e_objectivo(Estado(0, 0, 2, 0, 0, 0b11))
    assert not p.e_objectivo(Estado(1, 0, 1, 0, 0, 0b11))
    assert not p.e_objectivo(Estado(0, 0, 1, 0, 0, 0b01))


def test_poda_nao_altera_o_custo_optimo():
    com = ucs(problema(instancia_ta(), poda=True))
    sem = ucs(problema(instancia_ta(), poda=False))
    assert com.g == pytest.approx(sem.g)


def test_solucao_construtiva_chega_ao_objectivo():
    p = problema(instancia_ta())
    plano = solucao_construtiva(p)
    s = p.estado_inicial()
    for a in plano:
        assert a in p.accoes(s)
        s = p.resultado(s, a)
    assert p.e_objectivo(s)
