"""Corre a bateria de testes (limite 60 s / 2 GB) e exporta CSV + gráficos.

Uso (Windows, com o ambiente activado):
    python experiencias.py                      todas as instâncias e gráficos
    python experiencias.py --niveis pequena     só um nível
    python experiencias.py --estudo-delta       estudo da discretização da bateria
    python experiencias.py --estudo-vento       mesmo mapa com 4 direcções de vento
    python experiencias.py --graficos           só refaz gráficos e tabelas a partir dos CSV
"""
import argparse
import csv
import json
import platform
import subprocess
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path

from buscas import executar, factor_ramificacao
from dominio import DIRECCOES, DronePulverizacao, solucao_construtiva
from problema import caminho
from gerador import DIMENSOES, PASTA as PASTA_INSTANCIAS, SEMENTE

PASTA = Path(__file__).parent / "resultados"
LIMITE_TEMPO = 60.0
LIMITE_MEMORIA_MB = 2048
NIVEIS = ("pequena", "media", "grande")

# Um marcador por configuração: a paleta do matplotlib só tem 10 cores.
MARCADORES = "osD^vP*Xh<>"

CONFIGURACOES = [
    ("bfs", None), ("dfs", None), ("ids", None), ("ucs", None),
    ("gulosa", "h1"), ("gulosa", "h2"),
    ("a_estrela", "h0"), ("a_estrela", "h1"), ("a_estrela", "h2"),
    ("ara_estrela", "h1"), ("ara_estrela", "h2"),
]

COLUNAS = [
    "instancia", "nivel", "semente", "vento", "delta", "K", "n_posicoes", "limite_estados",
    "algoritmo", "heuristica", "limite_dfs", "estado", "energia", "comprimento",
    "expandidos", "gerados", "fronteira_max", "reexpandidos", "tempo_execucao_s",
    "memoria_pico_mb", "epsilon_linha", "recargas",
]


def carregar_instancias(niveis):
    """Instância base e instâncias geradas dos níveis pedidos."""
    nomes = (["base"] if "base" in niveis else []) + [
        f"{n}_{i:02d}" for n in niveis if n != "base" for i in range(1, 11)]
    instancias = []
    for nome in nomes:
        ficheiro = PASTA_INSTANCIAS / f"{nome}.json"
        with open(ficheiro, encoding="utf-8") as f:
            inst = json.load(f)
        if tuple(inst["dimensoes"]) != DIMENSOES:
            raise ValueError(f"{nome}: as experiências usam só a grelha {DIMENSOES}")
        instancias.append(inst)
    return instancias


def _linha(inst, problema, r, limite_dfs):
    recargas = None
    if r.no is not None:
        recargas = sum(1 for a, _ in caminho(r.no) if a == "recarregar")
    return {
        "instancia": inst["nome"], "nivel": inst.get("nivel", ""), "semente": inst.get("semente", ""),
        "vento": inst.get("vento"), "delta": problema.delta, "K": problema.K,
        "n_posicoes": len(problema.vizinhos), "limite_estados": problema.limite_estados(),
        "algoritmo": r.algoritmo, "heuristica": r.heuristica or "",
        "limite_dfs": limite_dfs if r.algoritmo == "dfs" else "",
        "estado": r.estado, "energia": r.custo, "comprimento": r.comprimento,
        "expandidos": r.expandidos, "gerados": r.gerados, "fronteira_max": r.fronteira_max,
        "reexpandidos": r.reexpandidos if r.algoritmo == "ids" else "",
        "tempo_execucao_s": round(r.tempo, 4), "memoria_pico_mb": round(r.memoria_pico_mb, 3),
        "epsilon_linha": r.epsilon_linha if r.algoritmo == "ara_estrela" else "",
        "recargas": recargas,
    }


def correr(instancias, ficheiro, configuracoes=CONFIGURACOES, curva=None, limite_tempo=LIMITE_TEMPO):
    """Executa cada configuração em cada instância e escreve uma linha por execução.

    O ficheiro é escrito linha a linha, para não se perder o que já correu.
    """
    PASTA.mkdir(exist_ok=True)
    with open(ficheiro, "w", newline="", encoding="utf-8") as f, \
            (open(curva, "w", newline="", encoding="utf-8") if curva else nullcontext()) as fc:
        escritor = csv.DictWriter(f, fieldnames=COLUNAS)
        escritor.writeheader()
        escritor_curva = None
        if curva:
            escritor_curva = csv.writer(fc)
            escritor_curva.writerow(["instancia", "nivel", "heuristica", "tempo_execucao_s",
                                     "energia", "epsilon", "epsilon_linha", "expandidos"])
        for inst in instancias:
            # Limite da DFS = número de acções de uma solução construtiva conhecida.
            plano = solucao_construtiva(DronePulverizacao(inst))
            limite_dfs = len(plano) if plano else None
            for algoritmo, h in configuracoes:
                # Um objecto novo por execução: a cache da heurística não passa
                # de uma execução para a seguinte.
                problema = DronePulverizacao(inst)
                r = executar(algoritmo, problema, h, limite_tempo=limite_tempo,
                             limite_memoria_mb=LIMITE_MEMORIA_MB, limite_dfs=limite_dfs)
                escritor.writerow(_linha(inst, problema, r, limite_dfs))
                f.flush()
                print(f"{inst['nome']:12s} {algoritmo:11s} {h or '':3s} {r.estado:15s} "
                      f"energia={r.custo} expandidos={r.expandidos} t={r.tempo:.1f}s", flush=True)
                if escritor_curva and algoritmo == "ara_estrela":
                    for t, custo, eps, eps_l, exp in r.curva:
                        escritor_curva.writerow([inst["nome"], inst.get("nivel", ""), h, round(t, 4),
                                                 custo, eps, eps_l, exp])
                    fc.flush()


def estudo_delta(instancias):
    """Mesmas instâncias com delta 0,25; 0,5 e 1 (A*(h2) e UCS)."""
    variantes = []
    for inst in instancias:
        for delta in (0.25, 0.5, 1.0):
            v = dict(inst, delta_bateria=delta)
            variantes.append(v)
    correr(variantes, PASTA / "estudo_delta.csv", [("ucs", None), ("a_estrela", "h2")])


def estudo_vento(instancias):
    """Mesmo mapa com o vento original, o oposto e os dois perpendiculares."""
    nomes = list(DIRECCOES)
    variantes = []
    for inst in instancias:
        i = nomes.index(inst["vento"])
        for k in (0, 4, 2, 6):  # original, oposto, perpendiculares
            variantes.append(dict(inst, vento=nomes[(i + k) % 8]))
    correr(variantes, PASTA / "estudo_vento.csv", [("a_estrela", "h2")])


def _git(*args):
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True,
                              cwd=Path(__file__).parent).stdout.strip()
    except OSError:
        return ""


def registar_execucao(args):
    # Com alterações por commitar, o hash sozinho não identifica o código que correu.
    alteracoes = _git("status", "--porcelain", "--untracked-files=no")
    info = {"data": datetime.now().isoformat(timespec="seconds"), "commit": _git("rev-parse", "HEAD"),
            "alteracoes_por_commitar": bool(alteracoes),
            "python": platform.python_version(), "semente": SEMENTE,
            "limite_tempo_s": LIMITE_TEMPO, "limite_memoria_mb": LIMITE_MEMORIA_MB,
            "argumentos": vars(args)}
    PASTA.mkdir(exist_ok=True)
    modo = "delta" if args.estudo_delta else "vento" if args.estudo_vento else "principal"
    with open(PASTA / f"execucao_{modo}.json", "w", encoding="utf-8") as f:
        json.dump(info, f, indent=1)


# Análise e gráficos

def optimos(df):
    """Custo óptimo por instância: UCS ou A* (h0, h1, h2) que terminaram.

    Se os custos não coincidirem a instância é assinalada e não recebe óptimo.
    """
    exactos = df[df["algoritmo"].isin(["ucs", "a_estrela"]) & (df["estado"] == "ok")]
    res = {}
    for nome, grupo in exactos.groupby("instancia"):
        custos = grupo["energia"].astype(float)
        if custos.max() - custos.min() > 1e-6 * max(1.0, custos.max()):
            print(f"AVISO: custos exactos diferentes em {nome}: {sorted(custos.unique())}")
            continue
        res[nome] = custos.min()
    return res


def graficos():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd

    df = pd.read_csv(PASTA / "execucoes.csv")
    df["config"] = df["algoritmo"] + df["heuristica"].fillna("").map(lambda h: f"({h})" if h else "")
    ok = df[df["estado"].isin(["ok", "limite"])]

    resumo = df.pivot_table(index="config", columns="nivel", values="estado",
                            aggfunc=lambda e: f"{(e == 'ok').sum()}/{len(e)}")
    resumo.to_csv(PASTA / "resumo_terminadas.csv")

    for coluna, ficheiro, titulo in [
        ("expandidos", "expandidos_vs_tamanho.png", "Nós expandidos vs. tamanho"),
        ("tempo_execucao_s", "tempo_vs_tamanho.png", "Tempo de execução vs. tamanho"),
    ]:
        fig, ax = plt.subplots(figsize=(9, 6))
        for i, (config, g) in enumerate(ok.groupby("config")):
            ax.scatter(g["limite_estados"], g[coluna].clip(lower=1e-4), label=config, s=22,
                       alpha=0.75, marker=MARCADORES[i % len(MARCADORES)])
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("limite superior de |S| (N_pos · N_bat · N_tq · 2^K)")
        ax.set_ylabel(coluna)
        ax.set_title(titulo + " (só execuções que terminaram)")
        ax.legend(fontsize=7, ncol=2)
        fig.tight_layout()
        fig.savefig(PASTA / ficheiro, dpi=130)
        plt.close(fig)

    opt = optimos(df)
    com_opt = ok[ok["instancia"].isin(opt)].copy()
    com_opt["optimo"] = com_opt["instancia"].map(opt)
    fig, ax = plt.subplots(figsize=(7, 7))
    for i, (config, g) in enumerate(com_opt.groupby("config")):
        ax.scatter(g["optimo"], g["energia"], label=config, s=22, alpha=0.75,
                   marker=MARCADORES[i % len(MARCADORES)])
    if len(com_opt):
        lim = [com_opt["optimo"].min() * 0.95, com_opt["energia"].max() * 1.05]
        ax.plot(lim, lim, "k--", linewidth=1, label="y = x")
    ax.set_xlabel("custo óptimo (UCS / A*)")
    ax.set_ylabel("custo obtido")
    ax.set_title("Custo obtido vs. custo óptimo")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(PASTA / "custo_vs_optimo.png", dpi=130)
    plt.close(fig)
    com_opt.assign(razao=com_opt["energia"] / com_opt["optimo"]).to_csv(
        PASTA / "custo_vs_optimo.csv", index=False)

    linhas = []
    for nome, g in df[(df["algoritmo"] == "a_estrela") & (df["estado"] == "ok")].groupby("instancia"):
        for _, r in g.iterrows():
            linhas.append({"instancia": nome, "nivel": r["nivel"], "heuristica": r["heuristica"],
                           "N": r["expandidos"], "d": r["comprimento"],
                           "b_estrela": round(factor_ramificacao(int(r["expandidos"]), int(r["comprimento"])), 5)})
    pd.DataFrame(linhas).to_csv(PASTA / "factor_ramificacao.csv", index=False)

    curva_csv = PASTA / "curva_ara.csv"
    if curva_csv.exists():
        curva = pd.read_csv(curva_csv)
        fig, ax = plt.subplots(figsize=(9, 6))
        for (nome, h), g in curva.groupby(["instancia", "heuristica"]):
            if g["nivel"].iloc[0] in ("grande", "base") or nome == "base":
                ax.step(g["tempo_execucao_s"], g["energia"], where="post", marker="o", label=f"{nome} {h}")
        ax.set_xlabel("tempo (s)")
        ax.set_ylabel("custo da solução (energia)")
        ax.set_title("ARA*: custo da solução vs. tempo")
        if ax.lines:
            ax.legend(fontsize=7, ncol=2)
        fig.tight_layout()
        fig.savefig(PASTA / "curva_ara.png", dpi=130)
        plt.close(fig)
    print("Gráficos e tabelas em", PASTA)


def main():
    p = argparse.ArgumentParser(description="Experiências do P5")
    p.add_argument("--niveis", nargs="+", default=["base", *NIVEIS],
                   choices=["base", *NIVEIS])
    p.add_argument("--estudo-delta", action="store_true")
    p.add_argument("--estudo-vento", action="store_true")
    p.add_argument("--graficos", action="store_true", help="só refaz gráficos a partir dos CSV")
    args = p.parse_args()
    if args.graficos:
        graficos()
        return
    registar_execucao(args)
    instancias = carregar_instancias(args.niveis)
    if args.estudo_delta:
        estudo_delta(instancias)
    elif args.estudo_vento:
        estudo_vento(instancias)
    else:
        correr(instancias, PASTA / "execucoes.csv", curva=PASTA / "curva_ara.csv")
        graficos()


if __name__ == "__main__":
    main()
