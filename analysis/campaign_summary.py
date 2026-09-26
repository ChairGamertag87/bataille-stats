"""Statistiques descriptives d'une campagne, avec intervalles de confiance à 95 %.

Lit results/<nom>/ sans rien rejouer.

    python analysis/campaign_summary.py --name <nom>
"""

import argparse
import math
from pathlib import Path

import numpy as np

from bataille.storage import RESULTS_DIR, loadCampaign

Z_95 = 1.959964
# Seed du rééchantillonnage, distincte de celle de la campagne : l'intervalle de la
# médiane doit être reproductible sans dépendre des donnes.
BOOTSTRAP_SEED = 0
BOOTSTRAP_SAMPLES = 2000


def wilsonInterval(successes: int, n: int) -> tuple[float, float]:
    # Wilson plutôt que l'approximation normale : reste valable près de 0 ou 1,
    # utile pour la proportion de parties infinies.
    p = successes / n
    denominator = 1 + Z_95**2 / n
    center = (p + Z_95**2 / (2 * n)) / denominator
    half_width = Z_95 * math.sqrt(p * (1 - p) / n + Z_95**2 / (4 * n**2)) / denominator
    return max(0.0, center - half_width), min(1.0, center + half_width)


def meanInterval(values: np.ndarray) -> tuple[float, float, float]:
    mean = values.mean()
    half_width = Z_95 * values.std(ddof=1) / math.sqrt(len(values))
    return mean, mean - half_width, mean + half_width


def medianInterval(values: np.ndarray) -> tuple[float, float, float]:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    # Un rééchantillon à la fois : la matrice complète dépasserait le gigaoctet sur 100 000 parties.
    medians = np.array([np.median(rng.choice(values, size=len(values))) for _ in range(BOOTSTRAP_SAMPLES)])
    low, high = np.percentile(medians, [2.5, 97.5])
    return float(np.median(values)), float(low), float(high)


def tailDecadeLength(values: np.ndarray, low_quantile: float = 0.5, high_quantile: float = 0.999) -> float:
    """Nombre de plis nécessaires pour diviser par 10 la part des parties plus longues.

    Ajustement linéaire du log10 de la survie P(T >= x) entre deux quantiles : au-delà
    du haut quantile, trop peu de parties pour que la courbe soit stable.
    """
    sorted_values = np.sort(values)
    survival = 1 - np.arange(len(sorted_values)) / len(sorted_values)
    low, high = np.quantile(values, [low_quantile, high_quantile])
    mask = (sorted_values >= low) & (sorted_values <= high)
    slope = np.polyfit(sorted_values[mask], np.log10(survival[mask]), 1)[0]
    return -1 / slope


def printProportion(label: str, successes: int, n: int) -> None:
    low, high = wilsonInterval(successes, n)
    print(f"  {label:<24} {successes:>6} / {n}  = {successes / n:8.3%}  [95% CI {low:.4%} ; {high:.4%}]")


def printDistribution(label: str, values: np.ndarray) -> None:
    mean, mean_low, mean_high = meanInterval(values)
    median, median_low, median_high = medianInterval(values)
    q1, q3, p90, p99 = np.percentile(values, [25, 75, 90, 99])
    print(f"{label}")
    print(f"  mean    {mean:8.1f}  [95% CI {mean_low:.1f} ; {mean_high:.1f}]")
    print(f"  median  {median:8.1f}  [95% CI {median_low:.1f} ; {median_high:.1f}] (bootstrap)")
    print(f"  std     {values.std(ddof=1):8.1f}")
    print(f"  min {values.min():.0f} | Q1 {q1:.0f} | Q3 {q3:.0f} | P90 {p90:.0f} | P99 {p99:.0f} | max {values.max():.0f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Print descriptive statistics of a campaign.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    args = parser.parse_args()

    games, metadata = loadCampaign(args.name, results_dir=args.results_dir)
    n = len(games)
    print(f"Campaign {metadata['name']} | seed {metadata['seed']} | {n} games | rules {metadata['rules']}")
    print()

    print("Outcomes")
    for outcome in ("win", "infinite", "draw", "capped"):
        printProportion(outcome, int((games["outcome"] == outcome).sum()), n)
    finished = games[games["outcome"] == "win"]
    print("Winner among finished games")
    for player in (1, 2):
        printProportion(f"player {player}", int((finished["winner"] == player).sum()), len(finished))
    print()

    printDistribution("Tricks per finished game", finished["tricks"].to_numpy())
    print(f"  tail: survival divided by 10 every {tailDecadeLength(finished['tricks'].to_numpy()):.0f} tricks")
    print()
    printDistribution("Battles per finished game", finished["battles"].to_numpy())
    print()

    total_battles, total_tricks = int(finished["battles"].sum()), int(finished["tricks"].sum())
    print(f"Pooled battles per trick: {total_battles} / {total_tricks} = {total_battles / total_tricks:.3%} "
          f"(independent draw reference 3/51 = {3 / 51:.3%})")
    print()

    print("Longest battle chain per game")
    for chain, count in finished["max_battle_chain"].value_counts().sort_index().items():
        print(f"  {chain}: {count:>6}  ({count / len(finished):.3%})")


if __name__ == "__main__":
    main()
