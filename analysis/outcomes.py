"""Issue des parties : victoires de chaque joueur, parties infinies, nulles ou plafonnées.

    python analysis/outcomes.py --name <nom>
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt

import style
from bataille.storage import RESULTS_DIR, loadCampaign
from campaign_summary import wilsonInterval


def plotOutcomes(games, metadata: dict) -> plt.Figure:
    n = len(games)
    categories = [
        ("Victoire du joueur 1", (games["outcome"] == "win") & (games["winner"] == 1), style.PLAYER_1),
        ("Victoire du joueur 2", (games["outcome"] == "win") & (games["winner"] == 2), style.PLAYER_2),
        ("Partie infinie", games["outcome"] == "infinite", style.NEUTRAL_SERIES),
        ("Partie nulle", games["outcome"] == "draw", style.NEUTRAL_SERIES),
        ("Plafond de plis atteint", games["outcome"] == "capped", style.NEUTRAL_SERIES),
    ]

    fig, ax = plt.subplots(figsize=(10, 3.8))
    labels = []
    for position, (label, mask, color) in enumerate(categories):
        count = int(mask.sum())
        share = count / n
        low, high = wilsonInterval(count, n)
        ax.barh(position, share, height=0.5, color=color, zorder=3)
        ax.errorbar(share, position, xerr=[[share - low], [high - share]], fmt="none",
                    ecolor=style.INK_PRIMARY, elinewidth=style.HAIRLINE, capsize=4, zorder=4)
        ax.text(high + 0.01, position,
                f"{style.formatPercent(share)}  ({style.formatInt(count)}), "
                f"IC 95 % [{style.formatSmallPercent(low)} ; {style.formatSmallPercent(high)}]",
                va="center", color=style.INK_SECONDARY, fontsize=9)
        labels.append(label)

    ax.set_yticks(range(len(labels)), labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(lambda value, _: style.formatPercent(value, 0))
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.tick_params(axis="y", labelcolor=style.INK_SECONDARY)
    ax.set_xlabel("Part des parties")
    ax.set_title("Issue des parties", pad=24)
    style.addSubtitle(ax, f"{style.formatInt(n)} donnes aléatoires. Barres d'erreur : intervalle de Wilson à 95 %.")
    style.addSource(fig, f"Campagne « {metadata['name']} », seed {metadata['seed']}.")
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot game outcomes of a campaign.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    args = parser.parse_args()

    games, metadata = loadCampaign(args.name, results_dir=args.results_dir)
    style.applyStyle()
    path = style.saveFigure(plotOutcomes(games, metadata), "outcomes")
    print(f"Figure saved to {path}")


if __name__ == "__main__":
    main()
