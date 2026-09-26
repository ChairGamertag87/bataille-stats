"""Situation des parties encore en cours après k plis : se stabilise-t-elle ?

Si la probabilité de terminaison devient constante parce que les parties survivantes
atteignent une distribution quasi stationnaire, alors :
- la répartition de l'écart de cartes parmi les parties en cours ne dépend plus de k ;
- la probabilité de finir dans les W plis suivants dépend de l'écart, pas de k.

Lit les instantanés produits par `bataille.simulate snapshots`, sans rien rejouer.

    python analysis/quasi_stationary.py --name <nom> [--window 100]
"""

import argparse
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator
from scipy.stats import chi2_contingency

import style
from bataille.cards import DECK_SIZE
from bataille.storage import RESULTS_DIR, loadCampaign, loadSnapshots
from campaign_summary import BOOTSTRAP_SAMPLES, BOOTSTRAP_SEED, meanInterval, wilsonInterval

# Plis de contrôle à partir desquels la probabilité de terminaison est stable (section 6).
SETTLED_FROM = 100
REFERENCE_TRICK = 300
# Seed du partage en deux moitiés disjointes, distincte de celle du bootstrap.
SPLIT_SEED = 1
# Classes d'écart absolu pour les comparaisons et la probabilité par écart : assez
# larges pour que chaque case compte au moins quelques dizaines de parties.
DELTA_BINS = (0, 8, 16, 24, 32, 40, DECK_SIZE + 1)
# Pas d'ordre de la rampe séquentielle : aucun plus clair que le pas 250, qui reste lisible sur le fond.
RAMP_STEPS = (3, 4, 5, 7, 8, 9, 10, 12)


def binLabels() -> list[str]:
    return [f"{low}-{high - 2}" if high <= DECK_SIZE else f"{low}+" for low, high in zip(DELTA_BINS, DELTA_BINS[1:])]


def binCounts(abs_delta: np.ndarray) -> np.ndarray:
    return np.histogram(abs_delta, bins=DELTA_BINS)[0]


def checkpointColors(checkpoints: list[int]) -> dict[int, str]:
    steps = RAMP_STEPS[-len(checkpoints):] if len(checkpoints) <= len(RAMP_STEPS) else RAMP_STEPS
    return {k: style.SEQUENTIAL_BLUE[step] for k, step in zip(checkpoints, steps)}


def plotDeltaDistribution(snapshots, checkpoints: list[int], metadata: dict) -> plt.Figure:
    colors = checkpointColors(checkpoints)
    # Chaque pli fait passer un nombre impair de cartes d'un joueur à l'autre : après
    # un nombre pair de plis l'écart est multiple de 4, sinon il vaut 2 modulo 4.
    # Des classes de 4 cartes neutralisent cette parité.
    starts = np.arange(0, DECK_SIZE, 4)
    values = starts + 1

    fig, ax = plt.subplots()
    for k in checkpoints:
        abs_delta = snapshots.loc[snapshots["trick"] == k, "card_delta"].abs().to_numpy()
        shares = np.histogram(abs_delta, bins=np.append(starts, DECK_SIZE + 1))[0] / len(abs_delta)
        dashed = k < SETTLED_FROM
        ax.plot(values, shares, color=colors[k], linestyle=(0, (4, 2)) if dashed else "-",
                label=f"après {k} plis ({style.formatInt(len(abs_delta))} parties)", zorder=3)

    ax.set_xlim(0, DECK_SIZE)
    ax.set_xticks(range(0, DECK_SIZE + 1, 8))
    ax.set_ylim(0, None)
    ax.yaxis.set_major_formatter(lambda value, _: style.formatPercent(value, 0))
    ax.set_xlabel("Écart de cartes entre les joueurs, en valeur absolue (classes de 4 cartes)")
    ax.set_ylabel("Part des parties encore en cours")
    ax.set_title("Écart de cartes des parties encore en cours après k plis", pad=24)
    style.addSubtitle(
        ax,
        f"Pointillés : avant {SETTLED_FROM} plis. Traits pleins : à partir de {SETTLED_FROM} plis.",
    )
    ax.legend(loc="upper right", ncol=2)
    style.addSource(fig, f"Campagne « {metadata['name']} », seed {metadata['seed']}. "
                         f"Classes de 4 cartes : un pli déplace toujours un nombre impair de cartes, "
                         f"ce qui alterne la parité de l'écart d'un pli à l'autre.")
    return fig


def plotMeanDelta(snapshots, checkpoints: list[int], metadata: dict) -> plt.Figure:
    rows = []
    for k in checkpoints:
        abs_delta = snapshots.loc[snapshots["trick"] == k, "card_delta"].abs().to_numpy().astype(float)
        rows.append((k, *meanInterval(abs_delta)))
    rows = np.array(rows)

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.errorbar(rows[:, 0], rows[:, 1], yerr=[rows[:, 1] - rows[:, 2], rows[:, 3] - rows[:, 1]],
                color=style.SINGLE_SERIES, ecolor=style.INK_SECONDARY, elinewidth=style.HAIRLINE,
                capsize=4, marker="o", markersize=8, markeredgecolor=style.SURFACE, markeredgewidth=2, zorder=3)
    for k, mean, _, _ in rows:
        ax.annotate(style.formatDecimal(mean), xy=(k, mean), xytext=(0, 10), textcoords="offset points",
                    ha="center", color=style.INK_SECONDARY, fontsize=9)

    ax.set_xscale("log")
    ax.set_xticks(checkpoints, [str(k) for k in checkpoints])
    ax.minorticks_off()
    ax.set_ylim(0, rows[:, 3].max() * 1.25)
    ax.set_xlabel("Plis déjà joués (k, échelle log)")
    ax.set_ylabel("Écart absolu moyen (cartes)")
    ax.set_title("Écart de cartes moyen des parties encore en cours", pad=24)
    style.addSubtitle(ax, "Barres : IC 95 % de la moyenne, valables point par point. Les comparaisons entre k sont faites par bootstrap des parties.")
    style.addSource(fig, f"Campagne « {metadata['name']} », seed {metadata['seed']}.")
    return fig


def terminationByDelta(snapshots, tricks_by_game: np.ndarray, k: int, window: int) -> list[tuple[int, int]]:
    at_k = snapshots[snapshots["trick"] == k]
    abs_delta = at_k["card_delta"].abs().to_numpy()
    ends_soon = tricks_by_game[at_k["game_index"].to_numpy()] <= k + window
    bins = np.digitize(abs_delta, DELTA_BINS[1:-1])
    return [(int(ends_soon[bins == b].sum()), int((bins == b).sum())) for b in range(len(DELTA_BINS) - 1)]


def plotTerminationByDelta(snapshots, tricks_by_game: np.ndarray, checkpoints: list[int], window: int,
                           metadata: dict) -> plt.Figure:
    settled = [k for k in checkpoints if k >= SETTLED_FROM]
    colors = checkpointColors(checkpoints)
    labels = binLabels()
    positions = np.arange(len(labels))

    fig, ax = plt.subplots()
    offsets = np.linspace(-0.12, 0.12, len(settled))
    for offset, k in zip(offsets, settled):
        counts = terminationByDelta(snapshots, tricks_by_game, k, window)
        keep = [n >= 30 for _, n in counts]
        probability = np.array([e / n if n else np.nan for e, n in counts])
        bounds = np.array([wilsonInterval(e, n) if n else (np.nan, np.nan) for e, n in counts])
        x = positions[keep] + offset
        ax.errorbar(x, probability[keep], yerr=[probability[keep] - bounds[keep, 0], bounds[keep, 1] - probability[keep]],
                    color=colors[k], ecolor=colors[k], elinewidth=style.HAIRLINE, capsize=3, marker="o",
                    markersize=6, linestyle="-", label=f"après {k} plis", zorder=3)

    ax.set_xticks(positions, labels)
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(lambda value, _: style.formatPercent(value, 0))
    ax.set_xlabel("Écart de cartes absolu après k plis")
    ax.set_ylabel(f"Probabilité de finir dans les {window} plis suivants")
    ax.set_title(f"Probabilité de finir dans les {window} plis suivants, selon l'écart de cartes", pad=24)
    style.addSubtitle(ax, "Barres : IC 95 % de Wilson, valables point par point. "
                          "Les comparaisons entre k sont faites par bootstrap des parties.")
    ax.legend(loc="upper left")
    style.addSource(fig, f"Campagne « {metadata['name']} », seed {metadata['seed']}. "
                         f"Points omis quand moins de 30 parties sont dans la classe.")
    return fig


class SnapshotPanel:
    """Relevés rangés par partie : une ligne par partie, une colonne par pli de contrôle.

    Toutes les statistiques sont des sommes pondérées sur les parties. Le bootstrap
    tire des parties, pas des relevés : une partie tirée apporte tous ses relevés, ce
    qui respecte la dépendance entre plis de contrôle (une partie en cours à 600 plis
    l'est aussi à 100, 200 et 300).
    """

    def __init__(self, snapshots, checkpoints: list[int], tricks_by_game: np.ndarray, window: int) -> None:
        self.checkpoints = list(checkpoints)
        n_games, n_checkpoints, n_classes = len(tricks_by_game), len(checkpoints), len(DELTA_BINS) - 1
        column = {k: index for index, k in enumerate(checkpoints)}
        abs_delta = np.full((n_games, n_checkpoints), -1, dtype=np.int64)
        abs_delta[snapshots["game_index"].to_numpy(), snapshots["trick"].map(column).to_numpy()] = (
            snapshots["card_delta"].abs().to_numpy()
        )
        alive = abs_delta >= 0
        classes = np.digitize(abs_delta, DELTA_BINS[1:-1])
        in_class = (classes[:, :, None] == np.arange(n_classes)) & alive[:, :, None]
        ends_soon = tricks_by_game[:, None] <= np.array(checkpoints) + window
        self.shape = (n_checkpoints, n_classes)
        self.features = np.hstack([
            alive,
            np.where(alive, abs_delta, 0),
            in_class.reshape(n_games, -1),
            (in_class & ends_soon[:, :, None]).reshape(n_games, -1),
        ]).astype(np.float32)
        self.in_class = in_class

    def statistics(self, weights: np.ndarray) -> dict[str, np.ndarray]:
        n_checkpoints, n_classes = self.shape
        totals = (weights.astype(np.float32) @ self.features).astype(np.float64)
        alive = totals[:n_checkpoints]
        class_counts = totals[2 * n_checkpoints:2 * n_checkpoints + n_checkpoints * n_classes].reshape(self.shape)
        ended = totals[2 * n_checkpoints + n_checkpoints * n_classes:].reshape(self.shape)
        with np.errstate(invalid="ignore", divide="ignore"):
            return {
                "mean": totals[n_checkpoints:2 * n_checkpoints] / alive,
                "shares": class_counts / alive[:, None],
                "termination": ended / class_counts,
            }


def bootstrapDifferences(panel: SnapshotPanel) -> tuple[dict, dict, dict]:
    """Différences avec le pli de référence : estimation, borne basse et borne haute à 95 %."""
    reference = panel.checkpoints.index(REFERENCE_TRICK)
    n_games = panel.features.shape[0]

    def differences(stats: dict) -> dict:
        return {key: value - value[reference] for key, value in stats.items()}

    point = differences(panel.statistics(np.ones(n_games)))
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    samples = {key: [] for key in point}
    for _ in range(BOOTSTRAP_SAMPLES):
        weights = np.bincount(rng.integers(0, n_games, n_games), minlength=n_games)
        for key, value in differences(panel.statistics(weights)).items():
            samples[key].append(value)
    with warnings.catch_warnings():
        # Aux tout premiers plis, les classes d'écart élevé sont vides : leur intervalle reste indéfini.
        warnings.simplefilter("ignore", RuntimeWarning)
        low = {key: np.nanpercentile(np.array(values), 2.5, axis=0) for key, values in samples.items()}
        high = {key: np.nanpercentile(np.array(values), 97.5, axis=0) for key, values in samples.items()}
    return point, low, high


def splitHalfChiSquare(panel: SnapshotPanel) -> dict[int, tuple[float, float, int, int]]:
    """Khi-deux d'homogénéité sur deux moitiés disjointes des parties, tirées au hasard.

    Le pli k est lu sur une moitié, la référence sur l'autre : les échantillons sont
    indépendants. Moins puissant que sur toutes les parties, mais valide.
    """
    reference = panel.checkpoints.index(REFERENCE_TRICK)
    n_games = panel.features.shape[0]
    in_first_half = np.random.default_rng(SPLIT_SEED).permutation(n_games) < n_games // 2
    counts_first = panel.in_class[in_first_half].sum(axis=0)
    counts_second = panel.in_class[~in_first_half].sum(axis=0)
    results = {}
    for index, k in enumerate(panel.checkpoints):
        if index == reference:
            continue
        table = np.vstack([counts_first[index], counts_second[reference]])
        statistic, p_value, _, _ = chi2_contingency(table)
        results[k] = (statistic, p_value, int(table[0].sum()), int(table[1].sum()))
    return results


def formatPoints(value: float) -> str:
    return (f"{value:+.0f}" if round(value) else "0") + "\u202fpt"


def plotDifferences(panel: SnapshotPanel, differences: tuple[dict, dict, dict], key: str, title: str,
                    ylabel: str, subtitle: str, metadata: dict) -> plt.Figure:
    point, low, high = differences
    shown = [k for k in panel.checkpoints if k >= SETTLED_FROM and k != REFERENCE_TRICK]
    colors = checkpointColors(panel.checkpoints)
    labels = binLabels()
    positions = np.arange(len(labels))

    fig, ax = plt.subplots()
    ax.axhline(0, color=style.INK_SECONDARY, linewidth=style.HAIRLINE, zorder=2)
    for offset, k in zip(np.linspace(-0.15, 0.15, len(shown)), shown):
        index = panel.checkpoints.index(k)
        value, lower, upper = point[key][index] * 100, low[key][index] * 100, high[key][index] * 100
        ax.errorbar(positions + offset, value, yerr=[value - lower, upper - value], color=colors[k],
                    ecolor=colors[k], elinewidth=style.HAIRLINE * 1.5, capsize=3, marker="o", markersize=6,
                    linestyle="none", label=f"après {k} plis", zorder=3)

    ax.set_xticks(positions, labels)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.yaxis.set_major_formatter(lambda value, _: formatPoints(value))
    ax.set_xlabel("Écart de cartes absolu (classes)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, pad=24)
    style.addSubtitle(ax, subtitle)
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.11), ncol=len(shown))
    style.addSource(fig, f"Campagne « {metadata['name']} », seed {metadata['seed']}. Bootstrap de "
                         f"{style.formatInt(BOOTSTRAP_SAMPLES)} rééchantillonnages des parties, seed {BOOTSTRAP_SEED}.")
    return fig


def printSummary(panel: SnapshotPanel, differences: tuple[dict, dict, dict], split: dict, window: int) -> None:
    point, low, high = differences
    stats = panel.statistics(np.ones(panel.features.shape[0]))
    alive = panel.features[:, :len(panel.checkpoints)].sum(axis=0).astype(int)
    labels = binLabels()

    print("Absolute card difference among ongoing games (descriptive)")
    for index, k in enumerate(panel.checkpoints):
        shares = " ".join(f"{label}:{share:6.2%}" for label, share in zip(labels, stats["shares"][index]))
        print(f"  k = {k:5d} | n {alive[index]:6d} | mean {stats['mean'][index]:5.2f} | {shares}")
    print()

    print(f"Game-level bootstrap, differences against k = {REFERENCE_TRICK} ({BOOTSTRAP_SAMPLES} resamples)")
    for index, k in enumerate(panel.checkpoints):
        if k == REFERENCE_TRICK:
            continue
        mean = f"{point['mean'][index]:+.2f} [{low['mean'][index]:+.2f} ; {high['mean'][index]:+.2f}]"
        largest = np.max(np.maximum(np.abs(low["shares"][index]), np.abs(high["shares"][index])))
        excluded = int(np.sum((low["shares"][index] > 0) | (high["shares"][index] < 0)))
        print(f"  k = {k:5d} | mean diff {mean} cards | classes whose CI excludes 0: {excluded}/{len(labels)} "
              f"| largest CI bound on a class share: {largest:.2%}")
        cells = " ".join(
            f"{label}:{point['shares'][index][c]:+.2%}[{low['shares'][index][c]:+.2%};{high['shares'][index][c]:+.2%}]"
            for c, label in enumerate(labels)
        )
        print(f"           share diffs {cells}")
    print()

    print(f"Split-half chi-square against k = {REFERENCE_TRICK} (independent halves, split seed {SPLIT_SEED})")
    for k, (statistic, p_value, n_k, n_reference) in split.items():
        print(f"  k = {k:5d} | n {n_k:6d} vs {n_reference:6d} | chi2 {statistic:9.1f} | p-value {p_value:.3g}")
    print()

    print(f"P(end within {window} tricks | class at k): differences against k = {REFERENCE_TRICK}")
    for index, k in enumerate(panel.checkpoints):
        if k < SETTLED_FROM or k == REFERENCE_TRICK:
            continue
        excluded = int(np.nansum((low["termination"][index] > 0) | (high["termination"][index] < 0)))
        cells = " ".join(
            f"{label}:{point['termination'][index][c]:+.2%}[{low['termination'][index][c]:+.2%};{high['termination'][index][c]:+.2%}]"
            for c, label in enumerate(labels)
        )
        print(f"  k = {k:5d} | classes whose CI excludes 0: {excluded}/{len(labels)} | {cells}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check whether ongoing games reach a stable card-difference distribution.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--window", type=int, default=100)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    args = parser.parse_args()

    games, metadata = loadCampaign(args.name, results_dir=args.results_dir)
    snapshots, checkpoints = loadSnapshots(args.name, results_dir=args.results_dir)
    tricks_by_game = games.sort_values("game_index")["tricks"].to_numpy()

    panel = SnapshotPanel(snapshots, checkpoints, tricks_by_game, args.window)
    differences = bootstrapDifferences(panel)
    printSummary(panel, differences, splitHalfChiSquare(panel), args.window)
    style.applyStyle()
    for figure, name in (
        (plotDifferences(
            panel, differences, "shares",
            f"Répartition de l'écart de cartes : différence avec les parties en cours à {REFERENCE_TRICK} plis",
            "Différence de part (points de pourcentage)",
            f"Part de chaque classe à k plis moins part à {REFERENCE_TRICK} plis. Barres : IC 95 % par bootstrap des parties.",
            metadata), "ongoing_delta_differences"),
        (plotDifferences(
            panel, differences, "termination",
            f"Probabilité de finir dans les {args.window} plis : différence avec {REFERENCE_TRICK} plis, à écart égal",
            "Différence de probabilité (points)",
            f"Probabilité à k plis moins probabilité à {REFERENCE_TRICK} plis, par classe d'écart. "
            f"Barres : IC 95 % par bootstrap des parties.",
            metadata), f"termination_by_delta_differences_{args.window}"),
        (plotDeltaDistribution(snapshots, checkpoints, metadata), "ongoing_delta_distribution"),
        (plotMeanDelta(snapshots, checkpoints, metadata), "ongoing_delta_mean"),
        (plotTerminationByDelta(snapshots, tricks_by_game, checkpoints, args.window, metadata),
         f"termination_by_delta_{args.window}"),
    ):
        print(f"Figure saved to {style.saveFigure(figure, name)}")


if __name__ == "__main__":
    main()
