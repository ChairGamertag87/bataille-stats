"""Probabilité qu'une partie se termine dans les W plis suivants, selon la durée déjà jouée.

Pour une partie qui a déjà duré k plis : P(T <= k + W | T > k). Calculé sur les
durées enregistrées, sans rien rejouer.

    python analysis/termination.py --name <nom> [--window 100]
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

import style
from bataille.storage import RESULTS_DIR, loadCampaign
from campaign_summary import tailDecadeLength, wilsonInterval

# En dessous, trop peu de parties encore en cours pour que la proportion soit lisible.
MIN_GAMES_ALIVE = 200
TABLE_STEP = 100


def terminationWithin(tricks: np.ndarray, window: int, elapsed: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Pour chaque k de elapsed : nombre de parties encore en cours après k plis, et
    nombre de celles qui se terminent au plus tard au pli k + window."""
    sorted_tricks = np.sort(tricks)
    alive = len(sorted_tricks) - np.searchsorted(sorted_tricks, elapsed, side="right")
    still_alive_after = len(sorted_tricks) - np.searchsorted(sorted_tricks, elapsed + window, side="right")
    return alive, alive - still_alive_after


def exponentialReference(tricks: np.ndarray, window: int) -> float:
    # Avec un risque de terminaison constant par pli (loi géométrique), la probabilité
    # ne dépend plus de la durée écoulée.
    return 1 - 10 ** (-window / tailDecadeLength(tricks))


def plotTermination(tricks: np.ndarray, window: int, metadata: dict) -> plt.Figure:
    elapsed = np.arange(0, tricks.max() + 1)
    alive, ended = terminationWithin(tricks, window, elapsed)
    keep = alive >= MIN_GAMES_ALIVE
    elapsed, alive, ended = elapsed[keep], alive[keep], ended[keep]
    probability = ended / alive
    bounds = np.array([wilsonInterval(int(e), int(a)) for e, a in zip(ended, alive)])
    reference = exponentialReference(tricks, window)

    fig, ax = plt.subplots()
    ax.fill_between(elapsed, bounds[:, 0], bounds[:, 1], color=style.SINGLE_SERIES,
                    alpha=style.AREA_ALPHA * 2, linewidth=0, zorder=2)
    ax.plot(elapsed, probability, color=style.SINGLE_SERIES, zorder=3)
    ax.axhline(reference, color=style.INK_SECONDARY, linewidth=style.HAIRLINE, zorder=4)
    # Placée au-dessus de la zone où la bande de confiance est encore étroite, pour ne masquer aucune donnée.
    ax.annotate(f"risque constant ajusté sur la traîne : {style.formatPercent(reference)}",
                xy=(200, reference), xytext=(0, 14), textcoords="offset points",
                color=style.INK_SECONDARY, fontsize=9, ha="left", va="bottom", zorder=5)

    ax.set_xlim(0, elapsed[-1])
    ax.set_ylim(0, max(0.5, probability.max() * 1.15))
    ax.yaxis.set_major_formatter(lambda value, _: style.formatPercent(value, 0))
    ax.set_xlabel("Plis déjà joués (k)")
    ax.set_ylabel(f"Probabilité de finir dans les {window} plis suivants")
    ax.set_title(f"Probabilité qu'une partie se termine dans les {window} plis suivants", pad=24)
    style.addSubtitle(
        ax,
        f"Parmi les parties qui ont déjà duré k plis. Bande : IC 95 % de Wilson. "
        f"Courbe arrêtée quand moins de {MIN_GAMES_ALIVE} parties restent en cours (k = {elapsed[-1]}).",
    )
    style.addSource(fig, f"Campagne « {metadata['name']} », seed {metadata['seed']}, "
                         f"{style.formatInt(len(tricks))} parties terminées.")
    return fig


def printTable(tricks: np.ndarray, window: int) -> None:
    elapsed = np.arange(0, tricks.max() + 1, TABLE_STEP)
    alive, ended = terminationWithin(tricks, window, elapsed)
    print(f"P(game ends within {window} tricks | already lasted k tricks)")
    print(f"  exponential tail reference: {exponentialReference(tricks, window):.2%}")
    for k, a, e in zip(elapsed, alive, ended):
        if a < MIN_GAMES_ALIVE:
            break
        low, high = wilsonInterval(int(e), int(a))
        print(f"  k = {k:5d} | alive {a:6d} | ended {e:6d} | {e / a:6.2%}  [95% CI {low:.2%} ; {high:.2%}]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot the probability of ending within a window of tricks.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--window", type=int, default=100)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    args = parser.parse_args()

    games, metadata = loadCampaign(args.name, results_dir=args.results_dir)
    tricks = games.loc[games["outcome"] == "win", "tricks"].to_numpy()
    printTable(tricks, args.window)
    style.applyStyle()
    path = style.saveFigure(plotTermination(tricks, args.window, metadata), f"termination_within_{args.window}")
    print(f"Figure saved to {path}")


if __name__ == "__main__":
    main()
