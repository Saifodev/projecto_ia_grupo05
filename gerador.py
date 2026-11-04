"""Geração de instâncias a partir de uma semente (secção 2.4 do enunciado)."""
import random

NUMERO_GRUPO = 5
POS_LABORAL = False  # Pós-Laboral soma +50
SEMENTE = 2026 * 100 + NUMERO_GRUPO + (50 if POS_LABORAL else 0)  # 202605


def gerar_instancia(nivel: str, indice: int, semente: int = SEMENTE) -> dict:
    rng = random.Random(f"{semente}-{nivel}-{indice}")
    raise NotImplementedError
