import json

import pytest

from dominio import DronePulverizacao
from gerador import DIMENSOES, NIVEIS, gerar_instancia, guardar


def test_mesma_semente_gera_a_mesma_instancia():
    assert gerar_instancia("media", 3) == gerar_instancia("media", 3)
    assert gerar_instancia("media", 3) != gerar_instancia("media", 4)


def test_json_ida_e_volta(tmp_path):
    inst = gerar_instancia("pequena", 1)
    with open(guardar(inst, tmp_path), encoding="utf-8") as f:
        assert json.load(f) == inst


@pytest.mark.parametrize("nivel", list(NIVEIS))
def test_instancias_geradas_respeitam_as_regras(nivel):
    inst = gerar_instancia(nivel, 1)
    p = DronePulverizacao(inst)
    k_min, k_max = NIVEIS[nivel]["K"]
    assert tuple(inst["dimensoes"]) == DIMENSOES
    assert k_min <= p.K <= k_max
    assert all(v in (2, 3, 4) for v in p.litros_parcela)
    assert len(p.estacoes) == 2
    assert inst["bateria"] == 100 and inst["tanque"] == 10
    assert inst["d_ref"] > 0 and inst["limite_estados"] == p.limite_estados()


def test_celula_livre_desiste_quando_nao_ha_espaco():
    import random
    from gerador import _celula_livre
    vizinhas = {(x, y) for x in range(4, 7) for y in range(4, 7)}
    assert _celula_livre(random.Random(1), vizinhas, set(), set(), (5, 5), 1) is None
