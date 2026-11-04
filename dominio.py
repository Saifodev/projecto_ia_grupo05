"""P5 - Drone de pulverização agrícola em terreno 3D com vento.

TODO: definir o estado (imutável e hashable), por exemplo um
@dataclass(frozen=True) com posição (x, y, z), bateria discretizada,
litros no tanque e parcelas já pulverizadas (frozenset/bitmask).
"""
from problema import Problema


class DronePulverizacao(Problema):
    def estado_inicial(self):
        raise NotImplementedError

    def accoes(self, s):
        raise NotImplementedError

    def resultado(self, s, a):
        raise NotImplementedError

    def custo(self, s, a, s2):
        raise NotImplementedError

    def e_objectivo(self, s):
        raise NotImplementedError
