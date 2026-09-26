"""Moteur de partie.

Pur et déterministe : une donne et une configuration de règles en entrée, un
résultat de partie en sortie. Aucune I/O, aucun aléa.
"""

from collections import deque
from dataclasses import dataclass, field
from enum import Enum

from bataille.rules import DEFAULT_RULES, BattlePickupOrder, RulesConfig, ShortInBattle


class Outcome(Enum):
    WIN = "win"
    # Les deux joueurs manquent de cartes au même moment d'une bataille.
    DRAW = "draw"
    INFINITE = "infinite"
    CAPPED = "capped"


@dataclass(frozen=True)
class TrickRecord:
    # Cartes posées par chaque joueur pendant le pli, dans l'ordre de pose.
    cards_1: tuple[int, ...]
    cards_2: tuple[int, ...]
    # Nombre d'égalités survenues pendant le pli.
    battles: int
    # 1 ou 2, None si le pli n'a pas pu être résolu.
    winner: int | None
    # Joueur à court pendant la bataille (1 ou 2), 0 si les deux, None sinon.
    short_player: int | None = None


@dataclass(frozen=True)
class GameResult:
    outcome: Outcome
    # 1 ou 2 pour une victoire, None sinon.
    winner: int | None
    tricks: int
    # Nombre total d'égalités : une bataille en chaîne de profondeur 2 compte pour 2.
    battles: int
    # Plus grand nombre d'égalités successives au sein d'un même pli.
    max_battle_chain: int
    # Pour une partie infinie : pli où l'état répété a été vu pour la première
    # fois, et période du cycle en plis.
    cycle_start: int | None = None
    cycle_length: int | None = None
    trace: tuple[TrickRecord, ...] | None = field(default=None, repr=False)


def playTrick(deck_1: deque[int], deck_2: deque[int], rules: RulesConfig = DEFAULT_RULES) -> TrickRecord:
    """Joue un pli en modifiant les deux paquets en place.

    Les deux paquets doivent être non vides. Si un joueur est à court pendant
    une bataille, les cartes posées sont retirées du jeu : la partie s'arrête.
    """
    cards_needed = rules.hidden_cards_per_battle + 1
    pile_1 = [deck_1.popleft()]
    pile_2 = [deck_2.popleft()]
    battles = 0

    while pile_1[-1] == pile_2[-1]:
        battles += 1
        short_player = _findShortPlayer(len(deck_1), len(deck_2), cards_needed, rules.short_in_battle)
        if short_player is not None:
            return TrickRecord(tuple(pile_1), tuple(pile_2), battles, None, short_player)
        # Avec PLAYS_LAST_CARD, un joueur à court pose tout ce qui lui reste et
        # sa dernière carte devient la carte visible.
        for _ in range(min(cards_needed, len(deck_1))):
            pile_1.append(deck_1.popleft())
        for _ in range(min(cards_needed, len(deck_2))):
            pile_2.append(deck_2.popleft())

    winner = 1 if pile_1[-1] > pile_2[-1] else 2
    winner_pile, loser_pile = (pile_1, pile_2) if winner == 1 else (pile_2, pile_1)
    winner_deck = deck_1 if winner == 1 else deck_2
    if battles > 0 and rules.battle_pickup_order is BattlePickupOrder.LOSER_THEN_WINNER:
        winner_deck.extend(loser_pile)
        winner_deck.extend(winner_pile)
    else:
        winner_deck.extend(winner_pile)
        winner_deck.extend(loser_pile)

    return TrickRecord(tuple(pile_1), tuple(pile_2), battles, winner)


def playGame(
    hand_1: tuple[int, ...],
    hand_2: tuple[int, ...],
    rules: RulesConfig = DEFAULT_RULES,
    record_trace: bool = False,
) -> GameResult:
    deck_1 = deque(hand_1)
    deck_2 = deque(hand_2)

    seen_states: dict[tuple[tuple[int, ...], tuple[int, ...]], int] = {}
    trace: list[TrickRecord] | None = [] if record_trace else None
    tricks = 0
    battles = 0
    max_battle_chain = 0

    def finish(outcome: Outcome, winner: int | None, cycle_start: int | None = None) -> GameResult:
        return GameResult(
            outcome=outcome,
            winner=winner,
            tricks=tricks,
            battles=battles,
            max_battle_chain=max_battle_chain,
            cycle_start=cycle_start,
            cycle_length=None if cycle_start is None else tricks - cycle_start,
            trace=None if trace is None else tuple(trace),
        )

    while True:
        if not deck_1:
            return finish(Outcome.WIN, 2)
        if not deck_2:
            return finish(Outcome.WIN, 1)

        if rules.detect_cycles:
            state = (tuple(deck_1), tuple(deck_2))
            first_seen = seen_states.get(state)
            if first_seen is not None:
                return finish(Outcome.INFINITE, None, cycle_start=first_seen)
            seen_states[state] = tricks

        if rules.max_tricks is not None and tricks >= rules.max_tricks:
            return finish(Outcome.CAPPED, None)

        record = playTrick(deck_1, deck_2, rules)
        tricks += 1
        battles += record.battles
        max_battle_chain = max(max_battle_chain, record.battles)
        if trace is not None:
            trace.append(record)

        if record.short_player == 0:
            return finish(Outcome.DRAW, None)
        if record.short_player is not None:
            return finish(Outcome.WIN, 3 - record.short_player)


def _findShortPlayer(left_1: int, left_2: int, cards_needed: int, policy: ShortInBattle) -> int | None:
    """Renvoie le joueur à court (1 ou 2), 0 si les deux le sont, None sinon."""
    threshold = cards_needed if policy is ShortInBattle.LOSES else 1
    short_1 = left_1 < threshold
    short_2 = left_2 < threshold
    if short_1 and short_2:
        return 0
    if short_1:
        return 1
    if short_2:
        return 2
    return None
