"""h1 (ignora a direcção do vento) e h2 (vento real) para o P5.

Ambas resolvem exactamente um problema relaxado: sem bateria, mas com os
obstáculos, o relevo e o tanque. A partir da posição actual e dos litros no
tanque, o drone pulveriza todas as parcelas pendentes no nível 1, volta à
base para reabastecer sempre que precisa e acaba na base.

Cada troço custa a distância mínima entre as duas posições, calculada com
Dijkstra sobre as posições de voo. Diferem só no peso dos movimentos:

    h1: horizontal 0,5·|m| (o menor factor de vento possível); vertical 2 e 0,5
    h2: o custo real de cada movimento, com o vento da instância

As distâncias são dirigidas (com vento, ir de a a b não custa o mesmo que
voltar) e o plano óptimo é calculado por programação dinâmica em subconjuntos.
"""
import math

import dominio


def peso_sem_vento(accao, mov):
    if accao in dominio.DIRECCOES:
        dx, dy = dominio.DIRECCOES[accao]
        return 0.5 * math.hypot(dx, dy)
    return mov[2]


def peso_real(accao, mov):
    return mov[2]


def preparar(problema, peso):
    """Distâncias até cada alvo (base e parcelas) e tabelas da DP.

    Com S uma máscara de bits de parcelas, C a capacidade do tanque e d(a, b)
    a distância mínima de a para b:

    R[S]       menor custo para, partindo da base com o tanque cheio,
               pulverizar as parcelas de S e acabar na base;
    T[S][i][l] menor custo para, acabada de pulverizar a parcela i (fora de S)
               e com l litros, pulverizar as parcelas de S e acabar na base.

        T[∅][i][l] = d(q_i, B)
        T[S][i][l] = min( d(q_i, B) + R[S],
                          min_{j ∈ S, v_j ≤ l} d(q_i, q_j) + T[S∖j][j][l − v_j] )
        R[∅] = 0
        R[S] = min_{j ∈ S, v_j ≤ C} d(B, q_j) + T[S∖j][j][C − v_j]

    Na base reabastece-se sempre, porque ter mais litros nunca piora o custo.
    """
    base = (*problema.base, 1)
    alvos = [(x, y, 1) for x, y in problema.parcelas]
    # ate[b][a] = distância mínima de a para b
    ate = {b: problema.dijkstra([b], inverso=True, peso=peso)[0] for b in [base, *alvos]}
    litros = problema.litros_parcela
    cheio = problema.tanque
    K = len(alvos)
    entre = [[ate[alvos[j]].get(alvos[i], math.inf) for j in range(K)] for i in range(K)]
    para_base = [ate[base].get(alvos[i], math.inf) for i in range(K)]
    da_base = [ate[alvos[j]].get(base, math.inf) for j in range(K)]

    R = [math.inf] * (1 << K)
    T = [[[math.inf] * (cheio + 1) for _ in range(K)] for _ in range(1 << K)]
    R[0] = 0.0
    for i in range(K):
        T[0][i] = [para_base[i]] * (cheio + 1)
    # S sem j é sempre um número menor do que S, por isso já está calculado.
    for S in range(1, 1 << K):
        R[S] = min((da_base[j] + T[S & ~(1 << j)][j][cheio - litros[j]]
                    for j in range(K) if S >> j & 1 and litros[j] <= cheio), default=math.inf)
        for i in range(K):
            if S >> i & 1:
                continue
            for l in range(cheio + 1):
                melhor = para_base[i] + R[S]
                for j in range(K):
                    if S >> j & 1 and litros[j] <= l:
                        melhor = min(melhor, entre[i][j] + T[S & ~(1 << j)][j][l - litros[j]])
                T[S][i][l] = melhor
    return {"ate": ate, "T": T, "R": R}


def limite_percurso(problema, s, tabelas):
    ate, T, R = tabelas["ate"], tabelas["T"], tabelas["R"]
    p = (s.x, s.y, s.z)
    base = (*problema.base, 1)
    pendentes = problema.todas & ~s.feitas
    ate_base = ate[base].get(p, math.inf)
    if not pendentes:
        return ate_base
    melhor = ate_base + R[pendentes]
    for i, (x, y) in enumerate(problema.parcelas):
        if pendentes >> i & 1 and problema.litros_parcela[i] <= s.litros:
            resto = T[pendentes & ~(1 << i)][i][s.litros - problema.litros_parcela[i]]
            melhor = min(melhor, ate[(x, y, 1)].get(p, math.inf) + resto)
    return melhor
