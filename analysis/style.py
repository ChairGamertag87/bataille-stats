"""Charte graphique commune à toutes les figures du projet.

Tout script d'analyse appelle applyStyle() avant de tracer, puis saveFigure()
pour écrire dans figures/. Aucune couleur ni taille ne se choisit dans un script :
elles viennent d'ici, pour que les figures du README forment un ensemble.

Règles :
- Couleurs catégorielles attribuées dans l'ordre fixe de CATEGORICAL, jamais
  cyclées. Le joueur 1 est toujours le créneau 1 (bleu), le joueur 2 le
  créneau 2 (orange), sur toutes les figures. Au-delà de 3 séries superposées
  (nuage de points, petits multiples), regrouper en "Autres" ou facetter.
- Une grandeur continue : une seule teinte, du clair au foncé (SEQUENTIAL_BLUE).
- Un écart autour d'une référence : bleu et rouge avec un gris neutre au centre.
- Un seul axe des ordonnées par graphique, jamais de double axe.
- Traits de données à 2 px, grille et axes en filet de 1 px, discrets.
- Le texte (titres, étiquettes, légende) reste dans les encres de texte, jamais
  dans la couleur d'une série : l'identité est portée par la marque colorée.
- Une légende dès deux séries, complétée d'étiquettes directes en bout de courbe.
  Une série unique n'a pas de légende : le titre dit ce qui est tracé.
- Une série unique qui n'est pas un joueur prend SINGLE_SERIES (violet).
- Barres et histogrammes : barres séparées par un filet de la couleur de fond.
- Nombres à la française : espace fine pour les milliers, virgule décimale.

Palette validée pour la vision des couleurs atypique (écart OKLab >= 8 entre
créneaux adjacents) sur la surface claire ci-dessous.
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

FIGURES_DIR = Path("figures")

# Surfaces et encres
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"

# Ordre fixe : c'est l'ordre qui garantit la séparation des couleurs adjacentes.
CATEGORICAL = (
    "#2a78d6",  # bleu
    "#eb6834",  # orange
    "#1baf7a",  # aqua
    "#eda100",  # jaune
    "#e87ba4",  # magenta
    "#008300",  # vert
    "#4a3aa7",  # violet
    "#e34948",  # rouge
)
PLAYER_1 = CATEGORICAL[0]
PLAYER_2 = CATEGORICAL[1]
# Série unique qui ne représente pas un joueur (durées, batailles) : violet, pour ne
# jamais laisser croire qu'il s'agit du joueur 1. Validé avec les deux couleurs joueurs.
SINGLE_SERIES = CATEGORICAL[6]
# Issue sans joueur associé (infinie, nulle, plafond).
NEUTRAL_SERIES = INK_MUTED

SEQUENTIAL_BLUE = (
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
    "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b",
)
DIVERGING_NEUTRAL = "#f0efec"
DIVERGING_NEGATIVE = "#e34948"
DIVERGING_POSITIVE = "#2a78d6"

LINE_WIDTH = 2.0
HAIRLINE = 1.0
AREA_ALPHA = 0.10

FIGURE_SIZE = (10, 5.5)
DPI = 150

NBSP = "\u202f"

FONT_FAMILY = ["Segoe UI", "Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]


def applyStyle() -> None:
    mpl.rcParams.update({
        "figure.figsize": FIGURE_SIZE,
        "figure.dpi": DPI,
        "figure.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "savefig.dpi": DPI,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.25,

        "font.family": "sans-serif",
        "font.sans-serif": FONT_FAMILY,
        "font.size": 10,
        "text.color": INK_PRIMARY,

        "axes.facecolor": SURFACE,
        "axes.edgecolor": BASELINE,
        "axes.linewidth": HAIRLINE,
        "axes.labelcolor": INK_SECONDARY,
        "axes.labelsize": 10,
        "axes.titlesize": 13,
        "axes.titleweight": "semibold",
        "axes.titlecolor": INK_PRIMARY,
        "axes.titlelocation": "left",
        "axes.titlepad": 12,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "axes.axisbelow": True,
        "axes.prop_cycle": mpl.cycler(color=CATEGORICAL),

        "grid.color": GRIDLINE,
        "grid.linewidth": HAIRLINE,
        "grid.linestyle": "-",

        "xtick.color": INK_MUTED,
        "ytick.color": INK_MUTED,
        "xtick.labelcolor": INK_MUTED,
        "ytick.labelcolor": INK_MUTED,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "xtick.major.pad": 6,
        "ytick.major.pad": 6,

        "lines.linewidth": LINE_WIDTH,
        "lines.solid_capstyle": "round",
        "lines.solid_joinstyle": "round",
        "lines.markersize": 8,

        "legend.frameon": False,
        "legend.fontsize": 9,
        "legend.labelcolor": INK_SECONDARY,
    })


def addSubtitle(ax: plt.Axes, text: str) -> None:
    ax.text(0, 1.01, text, transform=ax.transAxes, color=INK_SECONDARY, fontsize=9, va="bottom")


def addSource(fig: plt.Figure, text: str) -> None:
    fig.text(0.01, -0.07, text, color=INK_MUTED, fontsize=8, ha="left", va="top")


def formatInt(value: float) -> str:
    # Séparateur de milliers à la française : espace fine insécable.
    return f"{round(value):,}".replace(",", "\u202f")


def formatPercent(value: float, decimals: int = 1) -> str:
    return f"{value * 100:.{decimals}f}".replace(".", ",") + "\u202f%"


def formatSmallPercent(value: float) -> str:
    # Garde deux chiffres significatifs pour les très petites parts, qu'un arrondi
    # à deux décimales ramènerait à zéro.
    if value == 0:
        return "0" + NBSP + "%"
    if value < 1e-4:
        return formatPercent(value, 4)
    if value < 1e-3:
        return formatPercent(value, 3)
    return formatPercent(value, 2)


def formatLogPercent(value: float) -> str:
    return f"{value * 100:g}".replace(".", ",") + NBSP + "%"


def formatDecimal(value: float, decimals: int = 1) -> str:
    return f"{value:,.{decimals}f}".replace(",", "\u202f").replace(".", ",")


def addReferenceLine(ax: plt.Axes, x: float, label: str, y_position: float = 0.97) -> None:
    ax.axvline(x, color=INK_SECONDARY, linewidth=HAIRLINE, zorder=4)
    ax.text(x, y_position, f" {label} ", transform=ax.get_xaxis_transform(), color=INK_SECONDARY,
            fontsize=9, ha="left", va="top", zorder=5,
            bbox={"facecolor": SURFACE, "edgecolor": "none", "pad": 1.5})


def saveFigure(fig: plt.Figure, name: str, figures_dir: Path = FIGURES_DIR) -> Path:
    figures_dir.mkdir(parents=True, exist_ok=True)
    path = figures_dir / f"{name}.png"
    fig.savefig(path)
    plt.close(fig)
    return path
