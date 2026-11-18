"""Os 7 algoritmos: BFS, DFS, IDS, UCS, Gulosa, A*, ARA*.

Os algoritmos só usam a interface Problema. As métricas e os limites de
execução ficam no objecto Controlo, que cada algoritmo actualiza.
"""
from __future__ import annotations

import heapq
import math
import time
import tracemalloc
from collections import deque
from dataclasses import dataclass, field

from problema import Problema, No, caminho  # noqa: F401

VERIFICAR_CADA = 500   # expansões entre verificações de tempo e memória


class LimiteExcedido(Exception):
    def __init__(self, motivo):
        super().__init__(motivo)
        self.motivo = motivo


class Controlo:
    """Contadores das métricas e verificação dos limites de tempo e memória."""

    def __init__(self, limite_tempo=None, limite_memoria_mb=None):
        self.limite_tempo = limite_tempo
        self.limite_memoria = None if limite_memoria_mb is None else limite_memoria_mb * 2**20
        self.inicio = time.perf_counter()
        self.expandidos = 0
        self.gerados = 0
        self.fronteira_max = 0
        self.reexpandidos = 0
        # Só o ARA* usa estes campos: melhor solução conhecida e curva.
        self.melhor = None
        self.epsilon_linha = None
        self.curva = []

    def tempo(self):
        return time.perf_counter() - self.inicio

    def expandir(self, problema, no):
        self.expandidos += 1
        if self.expandidos % VERIFICAR_CADA == 0:
            self.verificar()
        filhos = []
        s = no.estado
        for a in problema.accoes(s):
            s2 = problema.resultado(s, a)
            filhos.append(No(s2, no, a, no.g + problema.custo(s, a, s2), no.profundidade + 1))
        self.gerados += len(filhos)
        return filhos

    def fronteira(self, tamanho):
        if tamanho > self.fronteira_max:
            self.fronteira_max = tamanho

    def verificar(self):
        if self.limite_tempo is not None and self.tempo() > self.limite_tempo:
            raise LimiteExcedido("tempo")
        if self.limite_memoria is not None and tracemalloc.is_tracing():
            if tracemalloc.get_traced_memory()[0] > self.limite_memoria:
                raise LimiteExcedido("memoria")


def _no_caminho(no, estado):
    while no is not None:
        if no.estado == estado:
            return True
        no = no.pai
    return False


def bfs(problema: Problema, ctl=None):
    """Busca em largura em grafo, com teste de objectivo na geração."""
    ctl = ctl or Controlo()
    raiz = No(problema.estado_inicial())
    if problema.e_objectivo(raiz.estado):
        return raiz
    fila = deque([raiz])
    visitados = {raiz.estado}
    while fila:
        no = fila.popleft()
        for filho in ctl.expandir(problema, no):
            if filho.estado in visitados:
                continue
            if problema.e_objectivo(filho.estado):
                return filho
            visitados.add(filho.estado)
            fila.append(filho)
        ctl.fronteira(len(fila))
    return None


def _profundidade_limitada(problema, limite, ctl):
    """DFS iterativa com controlo de ciclos no caminho.

    Devolve (nó objectivo ou None, se algum nó foi cortado pelo limite).
    """
    raiz = No(problema.estado_inicial())
    pilha = [raiz]
    cortou = False
    while pilha:
        no = pilha.pop()
        if problema.e_objectivo(no.estado):
            return no, cortou
        if limite is not None and no.profundidade >= limite:
            cortou = True
            continue
        filhos = ctl.expandir(problema, no)
        for filho in reversed(filhos):
            if not _no_caminho(no, filho.estado):
                pilha.append(filho)
        ctl.fronteira(len(pilha))
    return None, cortou


def dfs(problema: Problema, limite=None, ctl=None):
    ctl = ctl or Controlo()
    return _profundidade_limitada(problema, limite, ctl)[0]


def ids(problema: Problema, ctl=None):
    """Aprofundamento iterativo. ctl.reexpandidos = expansões das iterações
    anteriores à última."""
    ctl = ctl or Controlo()
    limite = 0
    while True:
        ctl.reexpandidos = ctl.expandidos
        no, cortou = _profundidade_limitada(problema, limite, ctl)
        if no is not None or not cortou:
            return no
        limite += 1


def _melhor_primeiro(problema, f, ctl, reabrir=True):
    """Busca em grafo pela fila de prioridade f(nó), com teste de objectivo na
    expansão. Entradas obsoletas do heap são descartadas ao sair.

    Com reabrir=False um estado fechado nunca volta à fila (gulosa)."""
    raiz = No(problema.estado_inicial())
    contador = 0
    fila = [(f(raiz), contador, raiz)]
    melhor_g = {raiz.estado: 0.0}
    fechados = set()
    while fila:
        _, _, no = heapq.heappop(fila)
        s = no.estado
        if s in fechados or no.g > melhor_g[s]:
            continue
        if problema.e_objectivo(s):
            return no
        fechados.add(s)
        for filho in ctl.expandir(problema, no):
            s2 = filho.estado
            if s2 in fechados and not reabrir:
                continue
            if filho.g < melhor_g.get(s2, math.inf):
                # Só acontece num fechado se h não for consistente.
                fechados.discard(s2)
                melhor_g[s2] = filho.g
                contador += 1
                heapq.heappush(fila, (f(filho), contador, filho))
        ctl.fronteira(len(fila))
    return None


def ucs(problema: Problema, ctl=None):
    return _melhor_primeiro(problema, lambda no: no.g, ctl or Controlo())


def gulosa(problema: Problema, h="h1", ctl=None):
    return _melhor_primeiro(problema, lambda no: problema.heuristica(no.estado, h), ctl or Controlo(),
                            reabrir=False)


def a_estrela(problema: Problema, h="h1", ctl=None):
    return _melhor_primeiro(problema, lambda no: no.g + problema.heuristica(no.estado, h),
                            ctl or Controlo())


def ara_estrela(problema: Problema, h="h1", pesos=(3.0, 2.0, 1.5, 1.0), ctl=None):
    """ARA*: A* ponderado com pesos decrescentes que reaproveita a busca anterior.

    O objectivo é um predicado, por isso guarda-se G, o custo da melhor solução
    encontrada; ImprovePath pára quando G <= min f(OPEN). Cada melhoria de G
    entra na curva com o ε' que é válido nesse momento.
    """
    ctl = ctl or Controlo()
    s0 = problema.estado_inicial()
    hs = {}

    def hv(s):
        if s not in hs:
            hs[s] = problema.heuristica(s, h)
        return hs[s]

    nos = {s0: No(s0)}
    abertos, fechados, incons = {s0}, set(), set()
    fila = []
    contador = 0
    G = math.inf
    # Limite inferior válido do custo óptimo: h(s0) até acabar uma iteração.
    lb_valido = hv(s0)
    if problema.e_objectivo(s0):
        G = 0.0
        ctl.melhor = nos[s0]

    def publicar(eps, eps_linha):
        ctl.epsilon_linha = eps_linha
        # Só entra na curva o que muda: o custo ou o limite de qualidade.
        if not ctl.curva or ctl.curva[-1][1] != G or ctl.curva[-1][3] != eps_linha:
            ctl.curva.append((ctl.tempo(), G, eps, eps_linha, ctl.expandidos))

    def chave(s, eps):
        return nos[s].g + eps * hv(s)

    def improve_path(eps):
        nonlocal G, contador
        while fila:
            f, _, s = fila[0]
            if s not in abertos or f != chave(s, eps):
                heapq.heappop(fila)
                continue
            if G <= f:
                return
            heapq.heappop(fila)
            abertos.discard(s)
            fechados.add(s)
            for filho in ctl.expandir(problema, nos[s]):
                s2 = filho.estado
                if s2 in nos and filho.g >= nos[s2].g:
                    continue
                nos[s2] = filho
                if problema.e_objectivo(s2) and filho.g < G:
                    G = filho.g
                    ctl.melhor = filho
                    publicar(eps, G / lb_valido if lb_valido > 0 else None)
                if s2 in fechados:
                    incons.add(s2)
                else:
                    abertos.add(s2)
                    contador += 1
                    heapq.heappush(fila, (chave(s2, eps), contador, s2))
            ctl.fronteira(len(abertos))

    for eps in pesos:
        for s in incons:
            abertos.add(s)
        incons.clear()
        fechados.clear()
        fila = [(chave(s, eps), i, s) for i, s in enumerate(abertos)]
        heapq.heapify(fila)
        contador = len(fila)
        improve_path(eps)
        if G == math.inf:
            return None
        resto = abertos | incons
        lb = min((nos[s].g + hv(s) for s in resto), default=G)
        lb_valido = max(lb_valido, min(lb, G))
        eps_linha = min(eps, G / lb_valido) if lb_valido > 0 else eps
        publicar(eps, eps_linha)
        if eps_linha <= 1.0:
            break
    return ctl.melhor


@dataclass
class Resultado:
    algoritmo: str
    heuristica: str | None
    estado: str              # ok, sem_solucao, falhou_tempo, falhou_memoria, limite
    no: No | None
    expandidos: int
    gerados: int
    fronteira_max: int
    reexpandidos: int
    tempo: float
    memoria_pico_mb: float
    epsilon_linha: float | None = None
    curva: list = field(default_factory=list)

    @property
    def custo(self):
        return self.no.g if self.no else None

    @property
    def comprimento(self):
        return self.no.profundidade if self.no else None


ALGORITMOS = {
    "bfs": bfs, "dfs": dfs, "ids": ids, "ucs": ucs,
    "gulosa": gulosa, "a_estrela": a_estrela, "ara_estrela": ara_estrela,
}


def executar(nome, problema, h=None, limite_tempo=60.0, limite_memoria_mb=2048,
             limite_dfs=None, pesos=(3.0, 2.0, 1.5, 1.0)) -> Resultado:
    """Corre um algoritmo com limites e devolve as métricas.

    Uma execução que excede o limite fica registada como falhou_tempo ou
    falhou_memoria; o ARA* com solução fica como 'limite'.
    """
    kwargs = {}
    if nome in ("gulosa", "a_estrela", "ara_estrela"):
        kwargs["h"] = h
    if nome == "dfs":
        kwargs["limite"] = limite_dfs
    if nome == "ara_estrela":
        kwargs["pesos"] = pesos
    ja_media = tracemalloc.is_tracing()
    if not ja_media:
        tracemalloc.start()
    tracemalloc.reset_peak()
    ctl = Controlo(limite_tempo, limite_memoria_mb)
    try:
        no = ALGORITMOS[nome](problema, ctl=ctl, **kwargs)
        estado = "ok" if no is not None else "sem_solucao"
    except LimiteExcedido as e:
        no = ctl.melhor
        estado = "limite" if no is not None else "falhou_" + e.motivo
    except MemoryError:
        no, estado = None, "falhou_memoria"
    tempo = ctl.tempo()
    pico = tracemalloc.get_traced_memory()[1] / 2**20
    if not ja_media:
        tracemalloc.stop()
    return Resultado(nome, h, estado, no, ctl.expandidos, ctl.gerados, ctl.fronteira_max,
                     ctl.reexpandidos, tempo, pico, ctl.epsilon_linha, ctl.curva)


def factor_ramificacao(n_expandidos, d, tolerancia=1e-9):
    """b* tal que N + 1 = 1 + b* + (b*)^2 + ... + (b*)^d, por bissecção."""
    if d <= 0 or n_expandidos <= d:
        return 1.0

    alvo = n_expandidos + 1

    def soma(b):
        # Pára assim que passa o alvo, para b^i não crescer até dar overflow.
        total, termo = 0.0, 1.0
        for _ in range(d + 1):
            total += termo
            if total > alvo:
                break
            termo *= b
        return total

    baixo, alto = 1.0, float(n_expandidos)
    while alto - baixo > tolerancia:
        meio = (baixo + alto) / 2
        if soma(meio) < alvo:
            baixo = meio
        else:
            alto = meio
    return (baixo + alto) / 2
