"""Classe abstracta Problema e estrutura No (secção 2.1 do enunciado)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Hashable, Iterable, Optional


class Problema(ABC):
    """Interface genérica: os algoritmos de busca só conhecem esta classe."""

    @abstractmethod
    def estado_inicial(self) -> Hashable: ...

    @abstractmethod
    def accoes(self, s: Hashable) -> Iterable[Any]: ...

    @abstractmethod
    def resultado(self, s: Hashable, a: Any) -> Hashable: ...

    @abstractmethod
    def custo(self, s: Hashable, a: Any, s2: Hashable) -> float: ...

    @abstractmethod
    def e_objectivo(self, s: Hashable) -> bool: ...

    def heuristica(self, s: Hashable, nome: str = "h0") -> float:
        """h0 = 0 por omissão; o domínio sobrepõe para h1, h2."""
        return 0.0


@dataclass
class No:
    estado: Hashable
    pai: Optional["No"] = None
    accao: Any = None
    g: float = 0.0
    profundidade: int = 0


def caminho(no: No) -> list[tuple[Any, Hashable]]:
    """Reconstrói a solução como lista de (acção, estado), do início ao fim."""
    passos = []
    while no.pai is not None:
        passos.append((no.accao, no.estado))
        no = no.pai
    passos.reverse()
    return passos
