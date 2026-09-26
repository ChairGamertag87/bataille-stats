from collections import Counter, deque

import numpy as np
import pytest

from bataille.cards import DECK_SIZE, generateDeal, makeDeck
from bataille.engine import Outcome, playGame, playTrick
from bataille.rules import BattlePickupOrder, RulesConfig, ShortInBattle


def playOneTrick(hand_1, hand_2, rules=RulesConfig()):
    deck_1, deck_2 = deque(hand_1), deque(hand_2)
    record = playTrick(deck_1, deck_2, rules)
    return record, list(deck_1), list(deck_2)


# Pli simple

def testSimpleTrickWinnerPutsOwnCardFirst():
    record, deck_1, deck_2 = playOneTrick([9, 2], [5, 7])
    assert record.winner == 1
    assert record.battles == 0
    assert deck_1 == [2, 9, 5]
    assert deck_2 == [7]


def testSimpleTrickWonByPlayerTwo():
    record, deck_1, deck_2 = playOneTrick([3, 2], [12, 7])
    assert record.winner == 2
    assert deck_1 == [2]
    assert deck_2 == [7, 12, 3]


def testBattlePickupOrderDoesNotAffectSimpleTrick():
    rules = RulesConfig(battle_pickup_order=BattlePickupOrder.LOSER_THEN_WINNER)
    _, deck_1, _ = playOneTrick([9, 2], [5, 7], rules)
    assert deck_1 == [2, 9, 5]


# Bataille simple et en chaîne

def testSimpleBattle():
    record, deck_1, deck_2 = playOneTrick([5, 8, 10, 3], [5, 6, 4, 2])
    assert record.winner == 1
    assert record.battles == 1
    assert record.cards_1 == (5, 8, 10)
    assert record.cards_2 == (5, 6, 4)
    assert deck_1 == [3, 5, 8, 10, 5, 6, 4]
    assert deck_2 == [2]


def testSimpleBattleLoserThenWinner():
    rules = RulesConfig(battle_pickup_order=BattlePickupOrder.LOSER_THEN_WINNER)
    _, deck_1, _ = playOneTrick([5, 8, 10, 3], [5, 6, 4, 2], rules)
    assert deck_1 == [3, 5, 6, 4, 5, 8, 10]


def testChainedBattle():
    record, deck_1, deck_2 = playOneTrick([5, 8, 7, 9, 11, 3], [5, 6, 7, 2, 4, 6])
    assert record.winner == 1
    assert record.battles == 2
    assert deck_1 == [3, 5, 8, 7, 9, 11, 5, 6, 7, 2, 4]
    assert deck_2 == [6]


def testBattleWithTwoHiddenCards():
    rules = RulesConfig(hidden_cards_per_battle=2)
    record, deck_1, deck_2 = playOneTrick([5, 2, 3, 9], [5, 4, 6, 7], rules)
    assert record.winner == 1
    assert deck_1 == [5, 2, 3, 9, 5, 4, 6, 7]
    assert deck_2 == []


def testBattleWithoutHiddenCard():
    rules = RulesConfig(hidden_cards_per_battle=0)
    record, deck_1, _ = playOneTrick([5, 3], [5, 9], rules)
    assert record.winner == 2
    assert deck_1 == []


# Joueur à court pendant une bataille

def testShortPlayerLoses():
    result = playGame((5, 8), (5, 6, 9))
    assert result.outcome is Outcome.WIN
    assert result.winner == 2
    assert result.tricks == 1
    assert result.battles == 1


def testBothShortIsDraw():
    result = playGame((5, 8), (5, 6))
    assert result.outcome is Outcome.DRAW
    assert result.winner is None


def testShortPlayerPlaysLastCard():
    rules = RulesConfig(short_in_battle=ShortInBattle.PLAYS_LAST_CARD)
    record, deck_1, deck_2 = playOneTrick([5, 8], [5, 6, 4], rules)
    assert record.winner == 1
    assert record.cards_1 == (5, 8)
    assert deck_1 == [5, 8, 5, 6, 4]
    assert deck_2 == []
    result = playGame((5, 8), (5, 6, 4), rules)
    assert result.outcome is Outcome.WIN
    assert result.winner == 1


def testShortPlayerWithNoCardLeftLosesEvenWhenPlayingLastCard():
    rules = RulesConfig(short_in_battle=ShortInBattle.PLAYS_LAST_CARD)
    result = playGame((5,), (5, 6, 4), rules)
    assert result.winner == 2


# Parties infinies et garde-fou

# Donne vérifiée à la main : après deux plis, l'état (4, 2) / (2, 4, 3, 2, 2, 2)
# revient toutes les 8 plis.
KNOWN_CYCLE = ((2, 2, 2, 4), (2, 4, 3, 2))


def testKnownCycleIsDetected():
    result = playGame(*KNOWN_CYCLE)
    assert result.outcome is Outcome.INFINITE
    assert result.winner is None
    assert result.cycle_start == 2
    assert result.cycle_length == 8
    assert result.tricks == 10


def testCapStopsGameWithoutCycleDetection():
    rules = RulesConfig(detect_cycles=False, max_tricks=50)
    result = playGame(*KNOWN_CYCLE, rules)
    assert result.outcome is Outcome.CAPPED
    assert result.tricks == 50


def testInvalidRules():
    with pytest.raises(ValueError):
        RulesConfig(hidden_cards_per_battle=-1)
    with pytest.raises(ValueError):
        RulesConfig(max_tricks=0)


# Parties complètes sur des donnes aléatoires

def testDealIsAFullDeckSplitInTwo():
    hand_1, hand_2 = generateDeal(np.random.default_rng(0))
    assert len(hand_1) == len(hand_2) == DECK_SIZE // 2
    assert Counter(hand_1 + hand_2) == Counter(makeDeck())


def testDealIsReproducibleFromSeed():
    assert generateDeal(np.random.default_rng(42)) == generateDeal(np.random.default_rng(42))


def testTraceIsConsistentWithResult():
    hand_1, hand_2 = generateDeal(np.random.default_rng(1))
    result = playGame(hand_1, hand_2, record_trace=True)
    assert len(result.trace) == result.tricks
    assert sum(record.battles for record in result.trace) == result.battles
    for record in result.trace:
        if record.winner is not None:
            assert len(record.cards_1) == len(record.cards_2)


def testCycleDetectionDoesNotChangeFiniteGames():
    rng = np.random.default_rng(7)
    for _ in range(50):
        deal = generateDeal(rng)
        with_detection = playGame(*deal)
        if with_detection.outcome is not Outcome.WIN:
            continue
        without_detection = playGame(*deal, RulesConfig(detect_cycles=False))
        assert without_detection == with_detection
