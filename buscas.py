"""Os 7 algoritmos: BFS, DFS, IDS, UCS, Gulosa, A*, ARA* (a implementar de raiz)."""
from problema import Problema, No, caminho  # noqa: F401


def bfs(problema: Problema): raise NotImplementedError
def dfs(problema: Problema, limite=None): raise NotImplementedError
def ids(problema: Problema): raise NotImplementedError
def ucs(problema: Problema): raise NotImplementedError
def gulosa(problema: Problema, h="h1"): raise NotImplementedError
def a_estrela(problema: Problema, h="h1"): raise NotImplementedError
def ara_estrela(problema: Problema, h="h1", pesos=(3.0, 2.0, 1.5, 1.0)): raise NotImplementedError
