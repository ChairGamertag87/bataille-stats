"""Distribution de la durée des parties terminées, en plis.

    python analysis/durations.py --name <nom>
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

import style
from bataille.storage import RESULTS_DIR, loadCampaign
from campaign_summary import tailDecadeLength

BIN_WIDTH = 20
# Au-delà, l'histogramme n'a plus que quelques parties par classe : la traîne est
# montrée sur la courbe de survie, en échelle logarithmique.
HISTOGRAM_QUANTILE = 0.995


def plotDurationHistogram(tricks: np.ndarray, metadata: dict) -> plt.Figure:
    upper = int(np.ceil(np.quantile(tricks, HISTOGRAM_QUANTILE) / BIN_WIDTH) * BIN_WIDTH)
    bins = np.arange(0, upper + BIN_WIDTH, BIN_WIDTH)
    overflow = int((tricks > upper).sum())
    shares = np.histogram(tricks, bins=bins)[0] / len(tricks)

    fig, ax = plt.subplots()
    ax.bar(bins[:-1], shares, width=BIN_WIDTH, align="edge", color=style.SINGLE_SERIES,
           edgecolor=style.SURFACE, linewidth=0.8, zorder=3)
    median, mean = np.median(tricks), tricks.mean()
    style.addReferenceLine(ax, median, f"médiane {style.formatInt(median)}")
    style.addReferenceLine(ax, mean, f"moyenne {style.formatDecimal(mean)}", y_position=0.89)

    ax.set_xlim(0, upper)
    ax.yaxis.set_major_formatter(lambda value, _: style.formatPercent(value, 0))
    ax.set_xlabel(f"Durée de la partie (plis, classes de {BIN_WIDTH})")
    ax.set_ylabel("Part des parties")
    ax.set_title("Durée des parties", pad=24)
    style.addSubtitle(
        ax,
        f"{style.formatInt(len(tricks))} parties terminées. {style.formatInt(overflow)} parties "
        f"({style.formatPercent(overflow / len(tricks))}) dépassent {style.formatInt(upper)} plis et sortent du cadre.",
    )
    style.addSource(fig, f"Campagne « {metadata['name']} », seed {metadata['seed']}.")
    return fig


def plotDurationSurvival(tricks: np.ndarray, metadata: dict) -> plt.Figure:
    sorted_tricks = np.sort(tricks)
    # Part des parties qui durent au moins x plis : la plus longue partie garde 1/n.
    survival = 1 - np.arange(len(sorted_tricks)) / len(sorted_tricks)

    fig, ax = plt.subplots()
    ax.step(sorted_tricks, survival, where="post", color=style.SINGLE_SERIES, zorder=3)
    for quantile, label in ((0.5, "médiane"), (0.9, "90e centile"), (0.99, "99e centile")):
        value = np.quantile(tricks, quantile)
        style.addReferenceLine(ax, value, f"{label} {style.formatInt(value)}")

    ax.set_yscale("log")
    ax.set_ylim(0.5 / len(tricks), 1)
    ax.set_xlim(0, sorted_tricks[-1])
    ax.yaxis.set_major_formatter(lambda value, _: style.formatLogPercent(value))
    ax.grid(axis="y", which="major")
    ax.set_xlabel("Durée (plis)")
    ax.set_ylabel("Part des parties d'au moins n plis (échelle log)")
    ax.set_title("Part des parties qui durent au moins n plis", pad=24)
    style.addSubtitle(
        ax,
        f"{style.formatInt(len(tricks))} parties terminées. Droite en échelle log : traîne exponentielle, "
        f"la part est divisée par 10 tous les {style.formatInt(tailDecadeLength(tricks))} plis environ.",
    )
    style.addSource(fig, f"Campagne « {metadata['name']} », seed {metadata['seed']}.")
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot the distribution of game durations.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    args = parser.parse_args()

    games, metadata = loadCampaign(args.name, results_dir=args.results_dir)
    tricks = games.loc[games["outcome"] == "win", "tricks"].to_numpy()
    style.applyStyle()
    for figure, name in (
        (plotDurationHistogram(tricks, metadata), "duration_histogram"),
        (plotDurationSurvival(tricks, metadata), "duration_survival"),
    ):
        print(f"Figure saved to {style.saveFigure(figure, name)}")


if __name__ == "__main__":
    main()
