"""Instâncias reduzidas e um problema de grafo genérico, só para testes.

As instâncias reduzidas (TA, TB, TC, TD) não são instâncias experimentais:
servem para enumerar todos os estados e verificar regras e heurísticas.
"""
import heapq
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dominio import DronePulverizacao  # noqa: E402
from problema import Problema  # noqa: E402


def instancia_ta(vento="E", **extra):
    """4x4x2; reabastecimento e recarga obrigatórios entre as duas viagens."""
    inst = {
        "dimensoes": [4, 4, 2], "base": [0, 0], "estacoes": [[3, 3]], "vento": vento,
        "parcelas": [{"x": 2, "y": 1, "litros": 2}, {"x": 1, "y": 3, "litros": 3}],
        "proibidas": [], "relevo": [], "bateria": 8, "tanque": 4, "delta_bateria": 0.25,
    }
    inst.update(extra)
    return inst


def instancia_tb(vento="N"):
    """3x3x3 com uma parede de relevo de altura 1 em x = 1: obriga a subir."""
    return {
        "dimensoes": [3, 3, 3], "base": [0, 1], "estacoes": [], "vento": vento,
        "parcelas": [{"x": 2, "y": 1, "litros": 2}],
        "proibidas": [], "relevo": [{"x": [1, 1], "y": [0, 2], "altura": 1}],
        "bateria": 10, "tanque": 10, "delta_bateria": 0.25,
    }


def instancia_tc():
    """Parcela cercada por células proibidas: sem solução."""
    return {
        "dimensoes": [4, 4, 1], "base": [0, 0], "estacoes": [], "vento": "N",
        "parcelas": [{"x": 3, "y": 3, "litros": 2}],
        "proibidas": [{"x": [2, 2], "y": [2, 3]}, {"x": [3, 3], "y": [2, 2]}],
        "relevo": [], "bateria": 100, "tanque": 10, "delta_bateria": 0.25,
    }


def instancia_td(vento="E"):
    """Corredor 5x1x1 com a parcela na ponta."""
    return {
        "dimensoes": [5, 1, 1], "base": [0, 0], "estacoes": [], "vento": vento,
        "parcelas": [{"x": 4, "y": 0, "litros": 2}],
        "proibidas": [], "relevo": [], "bateria": 100, "tanque": 10, "delta_bateria": 0.25,
    }


def problema(inst, **kwargs):
    return DronePulverizacao(inst, **kwargs)


class ProblemaGrafo(Problema):
    """Grafo explícito, sem nada do drone, para testar os algoritmos."""

    def __init__(self, arestas, inicio, objectivos, h=None):
        self.arestas = arestas
        self.inicio = inicio
        self.objectivos = set(objectivos)
        self.h = h or {}

    def estado_inicial(self):
        return self.inicio

    def accoes(self, s):
        return sorted(self.arestas.get(s, {}))

    def resultado(self, s, a):
        return a

    def custo(self, s, a, s2):
        return self.arestas[s][a]

    def e_objectivo(self, s):
        return s in self.objectivos

    def heuristica(self, s, nome="h0"):
        return 0.0 if nome == "h0" else self.h.get(s, 0.0)


def alcancaveis(prob):
    """Todos os estados alcançáveis e as arestas (s, a, s2, custo)."""
    s0 = prob.estado_inicial()
    vistos = {s0}
    pilha = [s0]
    arestas = []
    while pilha:
        s = pilha.pop()
        for a in prob.accoes(s):
            s2 = prob.resultado(s, a)
            arestas.append((s, a, s2, prob.custo(s, a, s2)))
            if s2 not in vistos:
                vistos.add(s2)
                pilha.append(s2)
    return vistos, arestas


def custos_optimos(prob):
    """h*(s) para todos os estados alcançáveis: Dijkstra a partir dos
    objectivos sobre as arestas invertidas, com o custo original c(s -> s2)."""
    estados, arestas = alcancaveis(prob)
    inversas = {}
    for s, _, s2, c in arestas:
        inversas.setdefault(s2, []).append((s, c))
    dist = {s: 0.0 for s in estados if prob.e_objectivo(s)}
    fila = [(0.0, i, s) for i, s in enumerate(dist)]
    heapq.heapify(fila)
    n = len(fila)
    while fila:
        d, _, s = heapq.heappop(fila)
        if d > dist[s]:
            continue
        for anterior, c in inversas.get(s, []):
            if d + c < dist.get(anterior, math.inf):
                dist[anterior] = d + c
                n += 1
                heapq.heappush(fila, (d + c, n, anterior))
    return {s: dist.get(s, math.inf) for s in estados}, arestas
