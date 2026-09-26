"""Campagnes Monte Carlo et gestion des seeds.

Chaque partie tire sa donne d'un flux aléatoire propre, dérivé de la seed de
campagne et de l'indice de la partie : n'importe quelle partie se rejoue seule,
sans relancer celles qui la précèdent.
"""

import argparse
import statistics
from pathlib import Path

import numpy as np

from bataille.cards import generateDeal
from bataille.engine import GameResult, Outcome, TrickRecord, playGame
from bataille.rules import DEFAULT_RULES, RulesConfig
from bataille.storage import RESULTS_DIR, loadCampaign, saveCampaign, saveGameTrace, saveSnapshots


def dealForGame(seed: int, game_index: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    rng = np.random.default_rng(np.random.SeedSequence(seed, spawn_key=(game_index,)))
    return generateDeal(rng)


def resultToRow(game_index: int, result: GameResult) -> dict:
    return {
        "game_index": game_index,
        "outcome": result.outcome.value,
        "winner": result.winner,
        "tricks": result.tricks,
        "battles": result.battles,
        "max_battle_chain": result.max_battle_chain,
        "cycle_start": result.cycle_start,
        "cycle_length": result.cycle_length,
    }


def runCampaign(n_games: int, seed: int, rules: RulesConfig = DEFAULT_RULES) -> list[dict]:
    return [resultToRow(index, playGame(*dealForGame(seed, index), rules)) for index in range(n_games)]


def selectTypicalGame(rows: list[dict]) -> int:
    """Indice de la partie terminée dont la durée est la plus proche de la médiane.

    La médiane plutôt que la moyenne : la distribution des durées a une longue
    traîne à droite, qui tire la moyenne vers des parties peu représentatives.
    À durée égale, la plus petite valeur d'indice l'emporte pour rester déterministe.
    """
    finished = [row for row in rows if row["outcome"] == Outcome.WIN.value]
    if not finished:
        raise ValueError("no finished game in campaign")
    median_tricks = statistics.median(row["tricks"] for row in finished)
    best = min(finished, key=lambda row: (abs(row["tricks"] - median_tricks), row["game_index"]))
    return best["game_index"]


def handSizesFromTrace(
    size_1: int, size_2: int, trace: tuple[TrickRecord, ...]
) -> list[tuple[int, int, int, int]]:
    """Taille de chaque main après chaque pli, pli 0 compris : (pli, main 1, main 2, batailles)."""
    rows = [(0, size_1, size_2, 0)]
    for index, record in enumerate(trace, start=1):
        size_1 -= len(record.cards_1)
        size_2 -= len(record.cards_2)
        pot = len(record.cards_1) + len(record.cards_2)
        if record.winner == 1:
            size_1 += pot
        elif record.winner == 2:
            size_2 += pot
        rows.append((index, size_1, size_2, record.battles))
    return rows


def cardDeltaSnapshots(
    hand_1: tuple[int, ...], hand_2: tuple[int, ...], rules: RulesConfig, checkpoints: tuple[int, ...]
) -> list[tuple[int, int]]:
    """Écart de cartes (main 1 moins main 2) après k plis, pour chaque k de checkpoints
    auquel la partie est encore en cours."""
    result = playGame(hand_1, hand_2, rules, record_trace=True)
    sizes = handSizesFromTrace(len(hand_1), len(hand_2), result.trace)
    # Une partie terminée au pli k n'est plus en cours après k plis : elle est exclue.
    return [(k, sizes[k][1] - sizes[k][2]) for k in checkpoints if k < result.tricks]


def _runCampaignCommand(args: argparse.Namespace) -> None:
    rules = DEFAULT_RULES
    print(f"Running {args.games} games with seed {args.seed}")
    rows = runCampaign(args.games, args.seed, rules)
    path = saveCampaign(args.name, rows, seed=args.seed, rules=rules, results_dir=args.results_dir)
    print(f"Campaign saved to {path}")


def _traceGameCommand(args: argparse.Namespace) -> None:
    games, metadata = loadCampaign(args.name, results_dir=args.results_dir)
    rules = RulesConfig.fromDict(metadata["rules"])
    if args.game_index is None:
        game_index = selectTypicalGame(games.to_dict("records"))
    else:
        game_index = args.game_index
    hand_1, hand_2 = dealForGame(metadata["seed"], game_index)
    result = playGame(hand_1, hand_2, rules, record_trace=True)
    sizes = handSizesFromTrace(len(hand_1), len(hand_2), result.trace)
    selection = "typical" if args.game_index is None else "requested"
    path = saveGameTrace(
        args.name,
        game_index,
        sizes,
        details={"selection": selection, "hand_1": hand_1, "hand_2": hand_2, **resultToRow(game_index, result)},
        results_dir=args.results_dir,
    )
    print(f"Game {game_index} ({selection}, {result.tricks} tricks) trace saved to {path}")


def _snapshotsCommand(args: argparse.Namespace) -> None:
    games, metadata = loadCampaign(args.name, results_dir=args.results_dir)
    rules = RulesConfig.fromDict(metadata["rules"])
    checkpoints = tuple(sorted(args.tricks))
    print(f"Replaying {len(games)} games for snapshots at tricks {checkpoints}")
    rows = [
        (game_index, trick, delta)
        for game_index in range(metadata["n_games"])
        for trick, delta in cardDeltaSnapshots(*dealForGame(metadata["seed"], game_index), rules, checkpoints)
    ]
    path = saveSnapshots(args.name, rows, checkpoints, results_dir=args.results_dir)
    print(f"{len(rows)} snapshots saved to {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run War card game simulations.")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    commands = parser.add_subparsers(dest="command", required=True)

    campaign = commands.add_parser("campaign", help="play a batch of random deals")
    campaign.add_argument("--name", required=True)
    campaign.add_argument("--games", type=int, required=True)
    campaign.add_argument("--seed", type=int, required=True)
    campaign.set_defaults(handler=_runCampaignCommand)

    trace = commands.add_parser("trace", help="replay one game of a campaign and save its trace")
    trace.add_argument("--name", required=True)
    trace.add_argument("--game-index", type=int, help="defaults to the median-length finished game")
    trace.set_defaults(handler=_traceGameCommand)

    snapshots = commands.add_parser("snapshots", help="record the card difference of ongoing games at given tricks")
    snapshots.add_argument("--name", required=True)
    snapshots.add_argument("--tricks", type=int, nargs="+", required=True)
    snapshots.set_defaults(handler=_snapshotsCommand)

    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
