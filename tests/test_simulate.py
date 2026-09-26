import pytest

from bataille.cards import DECK_SIZE
from bataille.engine import playGame
from bataille.rules import BattlePickupOrder, RulesConfig, ShortInBattle
from bataille.simulate import cardDeltaSnapshots, dealForGame, handSizesFromTrace, runCampaign, selectTypicalGame
from bataille.storage import loadCampaign, loadGameTrace, saveCampaign, saveGameTrace


def testDealForGameDependsOnlyOnSeedAndIndex():
    assert dealForGame(2026, 5) == dealForGame(2026, 5)
    assert dealForGame(2026, 5) != dealForGame(2026, 6)
    assert dealForGame(2026, 5) != dealForGame(2027, 5)


def testCampaignGameCanBeReplayedAlone():
    rows = runCampaign(20, seed=3)
    replay = playGame(*dealForGame(3, 13))
    assert rows[13]["tricks"] == replay.tricks
    assert rows[13]["winner"] == replay.winner


def testSelectTypicalGameTakesMedianOfFinishedGames():
    rows = [
        {"game_index": 0, "outcome": "win", "tricks": 100},
        {"game_index": 1, "outcome": "win", "tricks": 300},
        {"game_index": 2, "outcome": "infinite", "tricks": 200},
        {"game_index": 3, "outcome": "win", "tricks": 5000},
        {"game_index": 4, "outcome": "win", "tricks": 290},
        {"game_index": 5, "outcome": "win", "tricks": 280},
    ]
    # Médiane des parties terminées : 290.
    assert selectTypicalGame(rows) == 4


def testSelectTypicalGameWithoutFinishedGame():
    with pytest.raises(ValueError):
        selectTypicalGame([{"game_index": 0, "outcome": "infinite", "tricks": 10}])


def testHandSizesConserveCardsAndReachEnd():
    hand_1, hand_2 = dealForGame(2026, 0)
    result = playGame(hand_1, hand_2, record_trace=True)
    sizes = handSizesFromTrace(len(hand_1), len(hand_2), result.trace)
    assert sizes[0] == (0, 26, 26, 0)
    assert len(sizes) == result.tricks + 1
    assert all(size_1 + size_2 == DECK_SIZE for _, size_1, size_2, _ in sizes)
    final_sizes = (sizes[-1][1], sizes[-1][2])
    assert final_sizes == ((DECK_SIZE, 0) if result.winner == 1 else (0, DECK_SIZE))


def testRulesRoundTrip():
    rules = RulesConfig(
        hidden_cards_per_battle=2,
        battle_pickup_order=BattlePickupOrder.LOSER_THEN_WINNER,
        short_in_battle=ShortInBattle.PLAYS_LAST_CARD,
        detect_cycles=False,
        max_tricks=None,
    )
    assert RulesConfig.fromDict(rules.toDict()) == rules


def testStorageRoundTrip(tmp_path):
    rows = runCampaign(5, seed=1)
    saveCampaign("unit", rows, seed=1, rules=RulesConfig(), results_dir=tmp_path)
    games, metadata = loadCampaign("unit", results_dir=tmp_path)
    assert list(games["tricks"]) == [row["tricks"] for row in rows]
    assert metadata["seed"] == 1
    assert RulesConfig.fromDict(metadata["rules"]) == RulesConfig()

    saveGameTrace("unit", 2, [(0, 26, 26, 0), (1, 27, 25, 0)], {"game_index": 2}, results_dir=tmp_path)
    trace, details = loadGameTrace("unit", 2, results_dir=tmp_path)
    assert list(trace["hand_1"]) == [26, 27]
    assert details == {"game_index": 2}


def testSnapshotsMatchHandSizesAndSkipFinishedGames():
    hand_1, hand_2 = dealForGame(2026, 0)
    result = playGame(hand_1, hand_2, record_trace=True)
    sizes = handSizesFromTrace(len(hand_1), len(hand_2), result.trace)
    checkpoints = (0, 10, result.tricks - 1, result.tricks, result.tricks + 50)
    snapshots = cardDeltaSnapshots(hand_1, hand_2, RulesConfig(), checkpoints)
    assert snapshots == [(k, sizes[k][1] - sizes[k][2]) for k in checkpoints[:3]]
    assert snapshots[0] == (0, 0)
