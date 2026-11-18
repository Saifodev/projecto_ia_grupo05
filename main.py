"""Menu: escolher instância, algoritmo, heurística e limites."""
from buscas import executar
from dominio import DronePulverizacao, solucao_construtiva
from gerador import NIVEIS, PASTA as PASTA_INSTANCIAS, gerar_instancia
from problema import caminho

ALGORITMOS = ["bfs", "dfs", "ids", "ucs", "gulosa", "a_estrela", "ara_estrela"]
COM_HEURISTICA = {"gulosa": ["h1", "h2"], "a_estrela": ["h0", "h1", "h2"], "ara_estrela": ["h1", "h2"]}


def escolher(pergunta, opcoes, omissao=None):
    for i, o in enumerate(opcoes, 1):
        print(f"  {i}. {o}")
    while True:
        texto = input(f"{pergunta}" + (f" [{omissao}]" if omissao else "") + ": ").strip()
        if not texto and omissao:
            return omissao
        if texto.isdigit() and 1 <= int(texto) <= len(opcoes):
            return opcoes[int(texto) - 1]
        if texto in opcoes:
            return texto
        print("Opção inválida.")


def ler_numero(pergunta, omissao, tipo=float):
    while True:
        texto = input(f"{pergunta} [{omissao}]: ").strip()
        if not texto:
            return omissao
        try:
            return tipo(texto)
        except ValueError:
            print("Valor inválido.")


def escolher_instancia():
    origem = escolher("Instância", ["ficheiro em instancias/", "gerar com a semente do grupo"], "ficheiro em instancias/")
    if origem.startswith("ficheiro"):
        ficheiros = sorted(p.name for p in PASTA_INSTANCIAS.glob("*.json"))
        if not ficheiros:
            print("Não há instâncias. Corre primeiro: python gerador.py")
            return None
        nome = escolher("Ficheiro", ficheiros, "base.json" if "base.json" in ficheiros else None)
        return DronePulverizacao.de_ficheiro(PASTA_INSTANCIAS / nome)
    nivel = escolher("Nível", list(NIVEIS), "pequena")
    indice = ler_numero("Índice", 1, int)
    return DronePulverizacao(gerar_instancia(nivel, indice))


def mostrar_solucao(problema, no, com_mapa):
    s = problema.estado_inicial()
    print(f"\n{'passo':>5}  {'acção':11s} {'posição':12s} {'bateria':>8s} {'tanque':>6s} {'energia acum.':>13s}")
    print(f"{0:5d}  {'início':11s} {str((s.x, s.y, s.z)):12s} {problema.energia(s):8.2f} {s.litros:6d} {0:13.3f}")
    g = 0.0
    for i, (accao, s2) in enumerate(caminho(no), 1):
        g += problema.custo(s, accao, s2)
        s = s2
        print(f"{i:5d}  {accao:11s} {str((s.x, s.y, s.z)):12s} {problema.energia(s):8.2f} {s.litros:6d} {g:13.3f}")
        if com_mapa:
            print(problema.desenhar(s) + "\n")


def mostrar_metricas(r):
    print("\nResultado:", r.estado)
    if r.no is not None:
        print(f"  energia total      {r.custo:.4f}")
        print(f"  número de acções   {r.comprimento}")
    print(f"  nós expandidos     {r.expandidos}")
    print(f"  nós gerados        {r.gerados}")
    print(f"  fronteira máxima   {r.fronteira_max}")
    if r.algoritmo == "ids":
        print(f"  nós re-expandidos  {r.reexpandidos}")
    if r.algoritmo == "ara_estrela":
        print(f"  ε' final           {r.epsilon_linha}")
        for t, custo, eps, eps_l, exp in r.curva:
            print(f"    t={t:7.3f}s  custo={custo:.4f}  ε={eps}  ε'={eps_l}  expandidos={exp}")
    print(f"  tempo              {r.tempo:.3f} s")
    print(f"  memória de pico    {r.memoria_pico_mb:.2f} MB")


def main():
    print("Projecto IA - Grupo 05 - Drone de pulverização (ARA*)")
    while True:
        problema = escolher_instancia()
        if problema is None:
            return
        print(problema.desenhar(problema.estado_inicial()))
        print(f"vento de {problema.instancia.get('vento')}, K = {problema.K}, "
              f"limite superior |S| = {problema.limite_estados():,}")
        algoritmo = escolher("Algoritmo", ALGORITMOS, "a_estrela")
        h = escolher("Heurística", COM_HEURISTICA[algoritmo], "h2") if algoritmo in COM_HEURISTICA else None
        limite_tempo = ler_numero("Limite de tempo (s)", 60.0)
        limite_memoria = ler_numero("Limite de memória (MB)", 2048.0)
        limite_dfs = None
        if algoritmo == "dfs":
            d_ref = problema.instancia.get("d_ref") or len(solucao_construtiva(problema) or [])
            limite_dfs = ler_numero("Limite de profundidade da DFS", d_ref, int)
        print("A procurar...")
        r = executar(algoritmo, problema, h, limite_tempo, limite_memoria, limite_dfs)
        mostrar_metricas(r)
        if r.no is not None and input("Mostrar a solução passo a passo? (s/n) [s]: ").strip().lower() != "n":
            com_mapa = input("Desenhar o mapa em cada passo? (s/n) [n]: ").strip().lower() == "s"
            mostrar_solucao(problema, r.no, com_mapa)
            print(problema.desenhar(r.no.estado))
        if input("\nOutra execução? (s/n) [s]: ").strip().lower() == "n":
            break


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nFim.")
