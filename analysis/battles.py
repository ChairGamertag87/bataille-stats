"""Batailles : nombre par partie, plus longue chaîne, fréquence des égalités par pli.

    python analysis/battles.py --name <nom>
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MultipleLocator

import style
from bataille.storage import RESULTS_DIR, loadCampaign

HISTOGRAM_QUANTILE = 0.995
# Probabilité d'égalité si les deux cartes retournées étaient tirées au hasard
# dans un paquet complet : 3 cartes de même valeur parmi les 51 restantes.
INDEPENDENT_TIE_RATE = 3 / 51
TIE_RATE_BIN = 0.005


def plotBattlesHistogram(battles: np.ndarray, metadata: dict) -> plt.Figure:
    upper = int(np.ceil(np.quantile(battles, HISTOGRAM_QUANTILE)))
    bins = np.arange(0, upper + 2)
    overflow = int((battles > upper).sum())
    shares = np.histogram(battles, bins=bins)[0] / len(battles)

    fig, ax = plt.subplots()
    ax.bar(bins[:-1], shares, width=1, align="center", color=style.SINGLE_SERIES,
           edgecolor=style.SURFACE, linewidth=0.8, zorder=3)
    median, mean = np.median(battles), battles.mean()
    style.addReferenceLine(ax, median, f"médiane {style.formatInt(median)}")
    style.addReferenceLine(ax, mean, f"moyenne {style.formatDecimal(mean)}", y_position=0.89)

    ax.set_xlim(-0.5, upper + 0.5)
    ax.yaxis.set_major_locator(MultipleLocator(0.01))
    ax.yaxis.set_major_formatter(lambda value, _: style.formatPercent(value, 0))
    ax.set_xlabel("Nombre de batailles dans la partie")
    ax.set_ylabel("Part des parties")
    ax.set_title("Nombre de batailles par partie", pad=24)
    style.addSubtitle(
        ax,
        f"{style.formatInt(len(battles))} parties terminées. Une bataille en chaîne de profondeur 2 compte pour 2. "
        f"{style.formatInt(overflow)} parties dépassent {upper} batailles et sortent du cadre.",
    )
    style.addSource(fig, f"Campagne « {metadata['name']} », seed {metadata['seed']}.")
    return fig


def plotLongestChain(chains: np.ndarray, metadata: dict) -> plt.Figure:
    values, counts = np.unique(chains, return_counts=True)
    shares = counts / len(chains)

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(values, shares, width=0.5, color=style.SINGLE_SERIES, zorder=3)
    for value, share, count in zip(values, shares, counts):
        ax.text(value, share, f"{style.formatSmallPercent(share)}\n({style.formatInt(count)})",
                ha="center", va="bottom", color=style.INK_SECONDARY, fontsize=9)

    ax.set_xticks(values)
    ax.set_ylim(0, shares.max() * 1.2)
    ax.yaxis.set_major_formatter(lambda value, _: style.formatPercent(value, 0))
    ax.set_xlabel("Plus longue chaîne de batailles de la partie (égalités successives dans un même pli)")
    ax.set_ylabel("Part des parties")
    ax.set_title("Plus longue bataille en chaîne de chaque partie", pad=24)
    style.addSubtitle(ax, f"{style.formatInt(len(chains))} parties terminées.")
    style.addSource(fig, f"Campagne « {metadata['name']} », seed {metadata['seed']}.")
    return fig


def plotTieRate(battles: np.ndarray, tricks: np.ndarray, metadata: dict) -> plt.Figure:
    rates = battles / tricks
    pooled = battles.sum() / tricks.sum()
    upper = np.quantile(rates, HISTOGRAM_QUANTILE)
    bins = np.arange(0, upper + TIE_RATE_BIN, TIE_RATE_BIN)
    shares = np.histogram(rates, bins=bins)[0] / len(rates)

    fig, ax = plt.subplots()
    ax.bar(bins[:-1], shares, width=TIE_RATE_BIN, align="edge", color=style.SINGLE_SERIES,
           edgecolor=style.SURFACE, linewidth=0.8, zorder=3)
    style.addReferenceLine(ax, INDEPENDENT_TIE_RATE, f"tirage indépendant 3/51 = {style.formatPercent(INDEPENDENT_TIE_RATE)}")
    style.addReferenceLine(ax, pooled, f"observé, toutes parties = {style.formatPercent(pooled)}", y_position=0.89)

    ax.set_xlim(0, bins[-1])
    ax.xaxis.set_major_formatter(lambda value, _: style.formatPercent(value, 0))
    ax.yaxis.set_major_formatter(lambda value, _: style.formatPercent(value, 0))
    ax.set_xlabel("Batailles par pli dans la partie")
    ax.set_ylabel("Part des parties")
    ax.set_title("Fréquence des batailles par pli", pad=24)
    style.addSubtitle(
        ax,
        f"{style.formatInt(len(rates))} parties terminées. Taux observé : total des batailles divisé par le total des plis.",
    )
    style.addSource(fig, f"Campagne « {metadata['name']} », seed {metadata['seed']}.")
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot battle statistics of a campaign.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    args = parser.parse_args()

    games, metadata = loadCampaign(args.name, results_dir=args.results_dir)
    finished = games[games["outcome"] == "win"]
    battles = finished["battles"].to_numpy()
    style.applyStyle()
    for figure, name in (
        (plotBattlesHistogram(battles, metadata), "battles_histogram"),
        (plotLongestChain(finished["max_battle_chain"].to_numpy(), metadata), "battle_chain"),
        (plotTieRate(battles, finished["tricks"].to_numpy(), metadata), "tie_rate"),
    ):
        print(f"Figure saved to {style.saveFigure(figure, name)}")


if __name__ == "__main__":
    main()
