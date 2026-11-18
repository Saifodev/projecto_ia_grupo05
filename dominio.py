"""P5 - Drone de pulverização agrícola em terreno 3D com vento.

Convenções:
- x cresce para Este, y para Norte, z vai de 1 (nível mais baixo de voo) a 5.
- O vento é identificado pela direcção de onde vem. O vector w aponta para
  essa direcção ("vento contrário"); voar no sentido de w custa 1,5.
- Bateria guardada em unidades de delta; cada acção gasta ceil(custo/delta).
- Recarga, pulverização e reabastecimento têm custo energético 0.
"""
from __future__ import annotations

import heapq
import json
import math
from dataclasses import dataclass

import heuristicas
from problema import Problema

DIRECCOES = {
    "N": (0, 1), "NE": (1, 1), "E": (1, 0), "SE": (1, -1),
    "S": (0, -1), "SO": (-1, -1), "O": (-1, 0), "NO": (-1, 1),
}
CUSTO_SUBIR = 2.0
CUSTO_DESCER = 0.5
FACTOR_VENTO = 0.5
# Margem para que um valor exacto como 0,5/0,25 = 2 não seja arredondado para 3.
TOLERANCIA = 1e-9


@dataclass(frozen=True, slots=True)
class Estado:
    x: int
    y: int
    z: int
    bateria: int   # unidades de delta
    litros: int
    feitas: int    # bit i a 1 se a parcela i já foi pulverizada


def vector_vento(nome: str | None) -> tuple[float, float]:
    if not nome:
        return (0.0, 0.0)
    dx, dy = DIRECCOES[nome]
    norma = math.hypot(dx, dy)
    return (dx / norma, dy / norma)


def custo_horizontal(dx: int, dy: int, w: tuple[float, float]) -> float:
    """1 x (1 + 0,5 cos θ), multiplicado por √2 na diagonal.

    Com w unitário, |m|·(1 + 0,5 cos θ) = |m| + 0,5·(m·w).
    """
    return math.hypot(dx, dy) + FACTOR_VENTO * (dx * w[0] + dy * w[1])


def unidades(custo: float, delta: float) -> int:
    return math.ceil(custo / delta - TOLERANCIA)


def _rectangulos(lista):
    for r in lista:
        x0, x1 = r["x"]
        y0, y1 = r["y"]
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                yield (x, y), r


class DronePulverizacao(Problema):
    def __init__(self, instancia: dict, poda: bool = True):
        self.instancia = instancia
        self.largura, self.comprimento, self.niveis = instancia["dimensoes"]
        self.proibidas = {c for c, _ in _rectangulos(instancia.get("proibidas", []))}
        self.relevo = {c: r["altura"] for c, r in _rectangulos(instancia.get("relevo", []))}
        self.base = tuple(instancia["base"])
        self.estacoes = [tuple(e) for e in instancia["estacoes"]]
        self.pontos_recarga = {self.base, *self.estacoes}
        self.parcelas = [(p["x"], p["y"]) for p in instancia["parcelas"]]
        self.litros_parcela = [p["litros"] for p in instancia["parcelas"]]
        self.parcela_em = {c: i for i, c in enumerate(self.parcelas)}
        self.K = len(self.parcelas)
        self.todas = (1 << self.K) - 1
        self.w = vector_vento(instancia.get("vento"))
        self.delta = instancia.get("delta_bateria", 0.25)
        self.tanque = instancia.get("tanque", 10)
        capacidade = instancia.get("bateria", 100) / self.delta
        if abs(capacidade - round(capacidade)) > TOLERANCIA:
            raise ValueError("bateria/delta tem de ser inteiro")
        self.capacidade = round(capacidade)
        self._validar()

        self.vizinhos = {p: self._movimentos(p) for p in self.posicoes()}
        self.anteriores = {}
        for p, movs in self.vizinhos.items():
            for accao, mov in movs.items():
                self.anteriores.setdefault(mov[0], []).append((p, accao, mov))
        # Energia mínima (em unidades) para chegar a um ponto de recarga; os
        # estados com menos bateria do que isto já não têm solução.
        self.poda = poda
        recarga = [(x, y, 1) for x, y in self.pontos_recarga]
        self.e_min = self.dijkstra(recarga, inverso=True)[0] if poda else {}
        self.tabelas = {
            "h1": heuristicas.preparar(self, heuristicas.peso_sem_vento),
            "h2": heuristicas.preparar(self, heuristicas.peso_real),
        }
        self._cache_h = {}

    @classmethod
    def de_ficheiro(cls, caminho, **kwargs) -> "DronePulverizacao":
        with open(caminho, encoding="utf-8") as f:
            return cls(json.load(f), **kwargs)

    def _validar(self):
        pontos = [self.base, *self.estacoes, *self.parcelas]
        for x, y in pontos:
            if not self.livre(x, y, 1):
                raise ValueError(f"({x}, {y}) tem de estar livre no nível 1")
        if len(set(self.parcelas)) != self.K:
            raise ValueError("duas parcelas na mesma célula")
        if set(self.parcelas) & self.pontos_recarga:
            raise ValueError("parcela em cima da base ou de uma estação")

    def livre(self, x, y, z) -> bool:
        return (0 <= x < self.largura and 0 <= y < self.comprimento and 1 <= z <= self.niveis
                and (x, y) not in self.proibidas and z > self.relevo.get((x, y), 0))

    def posicoes(self):
        for x in range(self.largura):
            for y in range(self.comprimento):
                for z in range(1, self.niveis + 1):
                    if self.livre(x, y, z):
                        yield (x, y, z)

    def _movimentos(self, p) -> dict:
        """Movimentos possíveis a partir de p, sem olhar para a bateria.

        Devolve {accao: (destino, unidades de bateria, custo)}.
        """
        x, y, z = p
        res = {}
        for nome, (dx, dy) in DIRECCOES.items():
            if not self.livre(x + dx, y + dy, z):
                continue
            # Não cortar cantos de células bloqueadas.
            if dx and dy and not (self.livre(x + dx, y, z) and self.livre(x, y + dy, z)):
                continue
            c = custo_horizontal(dx, dy, self.w)
            res[nome] = ((x + dx, y + dy, z), unidades(c, self.delta), c)
        if self.livre(x, y, z + 1):
            res["subir"] = ((x, y, z + 1), unidades(CUSTO_SUBIR, self.delta), CUSTO_SUBIR)
        if self.livre(x, y, z - 1):
            res["descer"] = ((x, y, z - 1), unidades(CUSTO_DESCER, self.delta), CUSTO_DESCER)
        return res

    def dijkstra(self, origens, inverso=False, peso=None):
        """Dijkstra sobre posições, ignorando a bateria.

        peso(accao, mov) dá o peso de cada movimento; por omissão, as unidades
        de bateria gastas. Com inverso=True devolve a distância de cada posição
        até às origens. Devolve (distancias, pais) com pais[p] = (posição
        anterior, acção).
        """
        peso = peso or (lambda accao, mov: mov[1])
        dist = {o: 0 for o in origens}
        pais = {o: None for o in origens}
        fila = [(0, o) for o in origens]
        heapq.heapify(fila)
        while fila:
            d, p = heapq.heappop(fila)
            if d > dist[p]:
                continue
            if inverso:
                seguintes = self.anteriores.get(p, [])
            else:
                seguintes = [(mov[0], accao, mov) for accao, mov in self.vizinhos.get(p, {}).items()]
            for q, accao, mov in seguintes:
                c = peso(accao, mov)
                if d + c < dist.get(q, math.inf):
                    dist[q] = d + c
                    pais[q] = (p, accao)
                    heapq.heappush(fila, (d + c, q))
        return dist, pais

    # Interface Problema

    def estado_inicial(self) -> Estado:
        return Estado(self.base[0], self.base[1], 1, self.capacidade, self.tanque, 0)

    def accoes(self, s: Estado) -> list[str]:
        res = []
        for accao, (destino, gasto, _) in self.vizinhos[(s.x, s.y, s.z)].items():
            resto = s.bateria - gasto
            if resto >= 0 and (not self.poda or resto >= self.e_min.get(destino, math.inf)):
                res.append(accao)
        if s.z == 1:
            i = self.parcela_em.get((s.x, s.y))
            if i is not None and not s.feitas >> i & 1 and s.litros >= self.litros_parcela[i]:
                res.append("pulverizar")
            if (s.x, s.y) in self.pontos_recarga and s.bateria < self.capacidade:
                res.append("recarregar")
            if (s.x, s.y) == self.base and s.litros < self.tanque:
                res.append("reabastecer")
        return res

    def resultado(self, s: Estado, a: str) -> Estado:
        if a == "pulverizar":
            i = self.parcela_em[(s.x, s.y)]
            return Estado(s.x, s.y, s.z, s.bateria, s.litros - self.litros_parcela[i], s.feitas | 1 << i)
        if a == "recarregar":
            return Estado(s.x, s.y, s.z, self.capacidade, s.litros, s.feitas)
        if a == "reabastecer":
            return Estado(s.x, s.y, s.z, s.bateria, self.tanque, s.feitas)
        (x, y, z), gasto, _ = self.vizinhos[(s.x, s.y, s.z)][a]
        return Estado(x, y, z, s.bateria - gasto, s.litros, s.feitas)

    def custo(self, s: Estado, a: str, s2: Estado) -> float:
        mov = self.vizinhos[(s.x, s.y, s.z)].get(a)
        return mov[2] if mov else 0.0

    def e_objectivo(self, s: Estado) -> bool:
        return s.feitas == self.todas and (s.x, s.y, s.z) == (*self.base, 1)

    def heuristica(self, s: Estado, nome: str = "h0") -> float:
        if nome == "h0":
            return 0.0
        # h não depende da bateria; muitos estados diferem só nela, por isso
        # guarda-se o valor calculado.
        chave = (nome, s.x, s.y, s.z, s.litros, s.feitas)
        valor = self._cache_h.get(chave)
        if valor is None:
            valor = heuristicas.limite_percurso(self, s, self.tabelas[nome])
            self._cache_h[chave] = valor
        return valor

    # Apoio às experiências e à visualização

    def limite_estados(self) -> int:
        """Limite superior de |S| = N_pos · N_bat · N_tq · 2^K."""
        return len(self.vizinhos) * (self.capacidade + 1) * (self.tanque + 1) * 2 ** self.K

    def energia(self, s: Estado) -> float:
        return s.bateria * self.delta

    def desenhar(self, s: Estado | None = None) -> str:
        """Vista de cima. # proibida, 1-4 altura do relevo, B base, E estação,
        P parcela pendente, p parcela feita, @ drone."""
        linhas = []
        for y in range(self.comprimento - 1, -1, -1):
            linha = []
            for x in range(self.largura):
                c = "."
                if (x, y) in self.proibidas:
                    c = "#"
                elif self.relevo.get((x, y)):
                    c = str(self.relevo[(x, y)])
                if (x, y) == self.base:
                    c = "B"
                elif (x, y) in self.estacoes:
                    c = "E"
                elif (x, y) in self.parcela_em:
                    feita = s is not None and s.feitas >> self.parcela_em[(x, y)] & 1
                    c = "p" if feita else "P"
                if s is not None and (x, y) == (s.x, s.y):
                    c = "@"
                linha.append(c)
            linhas.append(f"{y:2d} " + " ".join(linha))
        linhas.append("   " + " ".join(str(x % 10) for x in range(self.largura)))
        if s is not None:
            linhas.append(f"drone em ({s.x}, {s.y}, {s.z})  bateria {self.energia(s):.2f}"
                          f"  tanque {s.litros} L  parcelas {bin(s.feitas).count('1')}/{self.K}")
        return "\n".join(linhas)


def solucao_construtiva(problema: DronePulverizacao) -> list[str] | None:
    """Solução "uma parcela por viagem", usada para validar instâncias e como
    limite por omissão da DFS. Devolve a lista de acções ou None.

    Cada viagem: base -> (estações) -> parcela -> (estações) -> base, com
    recarga em cada ponto de recarga e reabastecimento na base.
    """
    cap = problema.capacidade
    recarga = sorted(problema.pontos_recarga)
    caminhos = {c: problema.dijkstra([(*c, 1)]) for c in recarga}

    def troco(origem, destino):
        dist, pais = caminhos[origem]
        alvo = (*destino, 1)
        if alvo not in dist:
            return None, math.inf
        accoes = []
        p = alvo
        while pais[p] is not None:
            p, a = pais[p]
            accoes.append(a)
        accoes.reverse()
        return accoes, dist[alvo]

    # Pontos de recarga alcançáveis a partir da base, com o caminho de saltos.
    rota = {problema.base: []}
    pendentes = [problema.base]
    while pendentes:
        c = pendentes.pop(0)
        for d in recarga:
            accoes, gasto = troco(c, d)
            if d not in rota and gasto <= cap:
                rota[d] = rota[c] + [(c, d)]
                pendentes.append(d)

    def ir(c):
        return [a for o, d in rota[c] for a in troco(o, d)[0] + ["recarregar"]]

    def voltar(c):
        res = []
        for o, d in reversed(rota[c]):
            res += troco(d, o)[0] + ["recarregar"]
        return res

    plano = []
    for i, q in enumerate(problema.parcelas):
        if problema.litros_parcela[i] > problema.tanque:
            return None
        melhor = None
        dist_q = problema.dijkstra([(*q, 1)])
        for c1 in rota:
            ida, g1 = troco(c1, q)
            if ida is None:
                continue
            for c2 in rota:
                alvo = (*c2, 1)
                if alvo in dist_q[0] and g1 + dist_q[0][alvo] <= cap:
                    volta = []
                    p = alvo
                    while dist_q[1][p] is not None:
                        p, a = dist_q[1][p]
                        volta.append(a)
                    volta.reverse()
                    viagem = ir(c1) + ida + ["pulverizar"] + volta + ["recarregar"] + voltar(c2)
                    if melhor is None or len(viagem) < len(melhor):
                        melhor = viagem
        if melhor is None:
            return None
        plano += melhor + ["reabastecer"]
    # A última viagem não precisa de recarregar nem reabastecer na base.
    while plano and plano[-1] in ("reabastecer", "recarregar"):
        plano.pop()
    return _limpar(problema, plano)


def _limpar(problema, plano):
    """Retira recargas e reabastecimentos que não são permitidos (bateria ou
    tanque já cheios) e confirma que o plano chega ao objectivo."""
    s = problema.estado_inicial()
    limpo = []
    for a in plano:
        if a in ("recarregar", "reabastecer") and a not in problema.accoes(s):
            continue
        if a not in problema.accoes(s):
            return None
        s = problema.resultado(s, a)
        limpo.append(a)
    return limpo if problema.e_objectivo(s) else None
