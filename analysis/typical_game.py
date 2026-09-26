"""Écart de cartes entre les deux joueurs au fil d'une partie typique.

Lit la campagne et la trace produites par bataille.simulate, sans rien rejouer.

    python -m bataille.simulate campaign --name <nom> --games 10000 --seed <seed>
    python -m bataille.simulate trace --name <nom>
    python analysis/typical_game.py --name <nom>
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt

import style
from bataille.cards import DECK_SIZE
from bataille.storage import RESULTS_DIR, findGameTraces, loadCampaign, loadGameTrace


_PICKUP_LABELS = {
    "winner_then_loser": "cartes du gagnant puis du perdant",
    "loser_then_winner": "cartes du perdant puis du gagnant",
}
_SHORT_LABELS = {
    "loses": "joueur à court en bataille perdant",
    "plays_last_card": "joueur à court en bataille jouant sa dernière carte",
}


def describeRules(rules: dict) -> str:
    return (
        f"{rules['hidden_cards_per_battle']} carte cachée par bataille, "
        f"ramassage {_PICKUP_LABELS[rules['battle_pickup_order']]}, "
        f"{_SHORT_LABELS[rules['short_in_battle']]}"
    )


def plotCardDelta(trace, details: dict, games, metadata: dict) -> plt.Figure:
    finished = games[games["outcome"] == "win"]
    median_tricks = finished["tricks"].median()
    tricks = trace["trick"]
    # Les deux mains totalisent toujours 52 cartes : l'écart porte toute l'information.
    delta = trace["hand_1"] - trace["hand_2"]

    fig, ax = plt.subplots()
    ax.fill_between(tricks, delta, 0, where=delta >= 0, interpolate=True,
                    color=style.PLAYER_1, alpha=style.AREA_ALPHA, linewidth=0, zorder=1)
    ax.fill_between(tricks, delta, 0, where=delta <= 0, interpolate=True,
                    color=style.PLAYER_2, alpha=style.AREA_ALPHA, linewidth=0, zorder=1)
    ax.axhline(0, color=style.BASELINE, linewidth=style.HAIRLINE, zorder=2)
    ax.plot(tricks, delta, color=style.INK_SECONDARY, zorder=3)

    battle_tricks = tricks[trace["battles"] > 0]
    ax.plot(
        battle_tricks, [-DECK_SIZE + 0.8] * len(battle_tricks), linestyle="none", marker="|",
        markersize=7, color=style.INK_MUTED, markeredgewidth=style.HAIRLINE, label="Pli avec bataille",
        zorder=2,
    )

    for y, text in ((DECK_SIZE - 3, "Avantage joueur 1"), (-DECK_SIZE + 5, "Avantage joueur 2")):
        ax.text(4, y, text, color=style.INK_SECONDARY, fontsize=9, va="center")
    for y, color in ((DECK_SIZE - 3, style.PLAYER_1), (-DECK_SIZE + 5, style.PLAYER_2)):
        ax.plot([1.5], [y], marker="s", markersize=7, color=color, alpha=0.6, linestyle="none", zorder=3)

    last_trick, last_delta = tricks.iloc[-1], delta.iloc[-1]
    ax.annotate(
        f"{int(last_delta):+d}", xy=(last_trick, last_delta), xytext=(8, 0),
        textcoords="offset points", va="center", color=style.INK_SECONDARY, fontsize=9,
    )

    ax.set_xlim(0, last_trick)
    ax.set_ylim(-DECK_SIZE, DECK_SIZE)
    ax.set_yticks(range(-DECK_SIZE, DECK_SIZE + 1, 13))
    ax.yaxis.set_major_formatter(lambda value, _: f"{int(value):+d}" if value else "0")
    ax.set_xlabel("Plis joués")
    ax.set_ylabel("Cartes du joueur 1 moins cartes du joueur 2")
    ax.set_title("Écart de cartes entre les deux joueurs au fil d'une partie typique", pad=24)
    style.addSubtitle(
        ax,
        f"Partie {details['game_index']} : {details['tricks']} plis, {details['battles']} batailles, "
        f"victoire du joueur {details['winner']}. Durée médiane des {style.formatInt(len(finished))} "
        f"parties terminées : {style.formatInt(median_tricks)} plis.",
    )
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.11))
    style.addSource(
        fig,
        f"Campagne « {metadata['name']} », seed {metadata['seed']}, "
        f"{style.formatInt(metadata['n_games'])} donnes. Règles : {describeRules(metadata['rules'])}.",
    )
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot the card difference between players over a typical game.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--game-index", type=int, help="defaults to the only saved trace")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    args = parser.parse_args()

    games, metadata = loadCampaign(args.name, results_dir=args.results_dir)
    game_index = args.game_index
    if game_index is None:
        saved = findGameTraces(args.name, results_dir=args.results_dir)
        if len(saved) != 1:
            raise SystemExit(f"Expected exactly one saved trace, found {saved}: pass --game-index")
        game_index = saved[0]
    trace, details = loadGameTrace(args.name, game_index, results_dir=args.results_dir)

    style.applyStyle()
    path = style.saveFigure(plotCardDelta(trace, details, games, metadata), "typical_game_card_delta")
    print(f"Figure saved to {path}")


if __name__ == "__main__":
    main()
