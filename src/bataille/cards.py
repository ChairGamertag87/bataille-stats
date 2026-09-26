"""Représentation du paquet et génération des donnes.

Une carte est réduite à sa valeur entière, de 2 (le 2) à 14 (l'As) : les
couleurs n'ont aucune influence sur le jeu, les garder ne ferait que ralentir
la détection de cycle sans rien changer au déroulé.

Une main est un tuple dont l'indice 0 est le dessus du paquet.
"""

import numpy as np

MIN_VALUE = 2
MAX_VALUE = 14
SUITS_COUNT = 4
DECK_SIZE = (MAX_VALUE - MIN_VALUE + 1) * SUITS_COUNT

_FACE_NAMES = {11: "V", 12: "D", 13: "R", 14: "A"}


def makeDeck() -> tuple[int, ...]:
    return tuple(value for value in range(MIN_VALUE, MAX_VALUE + 1) for _ in range(SUITS_COUNT))


def splitDeck(deck: tuple[int, ...]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    # Paquet uniformément mélangé : couper en deux moitiés équivaut en loi à une
    # distribution alternée, et reste plus simple à relire sur une donne construite.
    half = len(deck) // 2
    return tuple(deck[:half]), tuple(deck[half:])


def generateDeal(rng: np.random.Generator) -> tuple[tuple[int, ...], tuple[int, ...]]:
    deck = rng.permutation(np.array(makeDeck(), dtype=np.int64))
    return splitDeck(tuple(int(value) for value in deck))


def cardName(value: int) -> str:
    return _FACE_NAMES.get(value, str(value))
