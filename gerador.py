"""Geração de instâncias a partir de uma semente.

Todas as instâncias experimentais usam a grelha 20 x 20 x 5.
Os níveis diferem na complexidade (número de parcelas, distância à base,
obstáculos), com parâmetros calibrados.

Uso:  python gerador.py            gera instancias/<nivel>_<indice>.json
"""
import json
import random
from pathlib import Path

from dominio import DIRECCOES, DronePulverizacao, solucao_construtiva

NUMERO_GRUPO = 5
POS_LABORAL = False  # Pós-Laboral soma +50
SEMENTE = 2026 * 100 + NUMERO_GRUPO + (50 if POS_LABORAL else 0)  # 202605

DIMENSOES = (20, 20, 5)
BATERIA = 100
TANQUE = 10
DELTA = 0.25
INSTANCIAS_POR_NIVEL = 10
TENTATIVAS_CELULA = 200
PASTA = Path(__file__).parent / "instancias"

# raio: distância máxima (em células, Chebyshev) de cada parcela à base;
# None = qualquer posição.
NIVEIS = {
    "pequena": {"K": (1, 2), "raio": 1, "colinas": (1, 2)},
    "media": {"K": (3, 4), "raio": 5, "colinas": (2, 3)},
    "grande": {"K": (6, 6), "raio": None, "colinas": (3, 4)},
}


def _celula_livre(rng, ocupadas, proibidas, relevo, perto=None, raio=None):
    """Célula livre ao acaso, ou None se não encontrar nenhuma (por exemplo,
    se o raio à volta da base estiver todo ocupado)."""
    largura, comprimento, _ = DIMENSOES
    for _ in range(TENTATIVAS_CELULA):
        if raio is None:
            x, y = rng.randrange(largura), rng.randrange(comprimento)
        else:
            x = perto[0] + rng.randint(-raio, raio)
            y = perto[1] + rng.randint(-raio, raio)
            if not (0 <= x < largura and 0 <= y < comprimento):
                continue
        if (x, y) not in ocupadas and (x, y) not in proibidas and (x, y) not in relevo:
            return (x, y)
    return None


def _celulas(rect):
    return {(x, y) for x in range(rect["x"][0], rect["x"][1] + 1)
            for y in range(rect["y"][0], rect["y"][1] + 1)}


def _sortear(rng, nivel):
    largura, comprimento, niveis = DIMENSOES
    p = NIVEIS[nivel]
    # Linha de alta tensão: recta vertical ou horizontal com uma passagem.
    pos = rng.randint(5, 14)
    passagem = rng.randint(0, 17)
    if rng.random() < 0.5:
        linha = [{"nome": "linha_alta_tensao", "x": [pos, pos], "y": [0, passagem - 1]},
                 {"nome": "linha_alta_tensao", "x": [pos, pos], "y": [passagem + 2, comprimento - 1]}]
    else:
        linha = [{"nome": "linha_alta_tensao", "x": [0, passagem - 1], "y": [pos, pos]},
                 {"nome": "linha_alta_tensao", "x": [passagem + 2, largura - 1], "y": [pos, pos]}]
    linha = [r for r in linha if r["x"][0] <= r["x"][1] and r["y"][0] <= r["y"][1]]
    ax, ay = rng.randint(0, largura - 4), rng.randint(0, comprimento - 4)
    aldeia = {"nome": "aldeia", "x": [ax, ax + rng.randint(1, 3)], "y": [ay, ay + rng.randint(1, 3)]}
    proibidas = linha + [aldeia]
    celulas_proibidas = set().union(*(_celulas(r) for r in proibidas))

    relevo = []
    for _ in range(rng.randint(*p["colinas"])):
        cx, cy = rng.randint(0, largura - 3), rng.randint(0, comprimento - 3)
        relevo.append({"x": [cx, cx + rng.randint(1, 3)], "y": [cy, cy + rng.randint(1, 3)],
                       "altura": rng.randint(1, niveis - 1)})
    celulas_relevo = set().union(*(_celulas(r) for r in relevo))

    ocupadas = set()
    base = _celula_livre(rng, ocupadas, celulas_proibidas, celulas_relevo)
    if base is None:
        return None
    ocupadas.add(base)
    estacoes = []
    for _ in range(2):
        e = _celula_livre(rng, ocupadas, celulas_proibidas, celulas_relevo)
        if e is None:
            return None
        ocupadas.add(e)
        estacoes.append(list(e))
    parcelas = []
    for _ in range(rng.randint(*p["K"])):
        c = _celula_livre(rng, ocupadas, celulas_proibidas, celulas_relevo, base, p["raio"])
        if c is None:
            return None
        ocupadas.add(c)
        parcelas.append({"x": c[0], "y": c[1], "litros": rng.choice((2, 3, 4))})
    return {
        "dimensoes": list(DIMENSOES),
        "base": list(base),
        "estacoes": estacoes,
        "vento": rng.choice(list(DIRECCOES)),
        "parcelas": parcelas,
        "proibidas": proibidas,
        "relevo": relevo,
        "bateria": BATERIA,
        "tanque": TANQUE,
        "delta_bateria": DELTA,
    }


def gerar_instancia(nivel: str, indice: int, semente: int = SEMENTE) -> dict:
    """Sorteia até obter uma instância com solução construtiva (condição
    suficiente de solubilidade). O número de tentativas fica registado."""
    rng = random.Random(f"{semente}-{nivel}-{indice}")
    tentativas = 0
    while True:
        tentativas += 1
        inst = _sortear(rng, nivel)
        if inst is None:
            continue
        problema = DronePulverizacao(inst)
        plano = solucao_construtiva(problema)
        if plano is not None:
            inst.update({
                "nome": f"{nivel}_{indice:02d}", "nivel": nivel, "indice": indice,
                "semente": semente, "tentativas": tentativas,
                "d_ref": len(plano), "n_posicoes": len(problema.vizinhos),
                "limite_estados": problema.limite_estados(),
            })
            return inst


def guardar(inst, pasta=PASTA):
    pasta.mkdir(exist_ok=True)
    caminho = pasta / f"{inst['nome']}.json"
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        json.dump(inst, f, ensure_ascii=False, indent=1)
    return caminho


def main():
    for nivel in NIVEIS:
        for indice in range(1, INSTANCIAS_POR_NIVEL + 1):
            inst = gerar_instancia(nivel, indice)
            print(guardar(inst), "K =", len(inst["parcelas"]), "d_ref =", inst["d_ref"])


if __name__ == "__main__":
    main()
