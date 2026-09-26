"""Configuration des règles.

Les hypothèses H1 à H5 de CLAUDE.md ne sont pas encore tranchées : chacune est
un paramètre explicite, et la configuration complète doit être enregistrée avec
les résultats de chaque campagne.
"""

from dataclasses import asdict, dataclass
from enum import Enum


class BattlePickupOrder(Enum):
    """H2 : ordre de ramassage à l'issue d'une bataille.

    Un pli sans bataille suit toujours la règle figée : carte du gagnant, puis
    carte du perdant.
    """

    WINNER_THEN_LOSER = "winner_then_loser"
    LOSER_THEN_WINNER = "loser_then_winner"


class ShortInBattle(Enum):
    """H3 : joueur qui n'a pas assez de cartes pour terminer une bataille."""

    # Il perd immédiatement la partie.
    LOSES = "loses"
    # Il joue sa dernière carte face visible, et ne perd que s'il n'en a plus aucune.
    PLAYS_LAST_CARD = "plays_last_card"


@dataclass(frozen=True)
class RulesConfig:
    # H1 : nombre de cartes posées face cachée avant la carte visible.
    hidden_cards_per_battle: int = 1
    # H2
    battle_pickup_order: BattlePickupOrder = BattlePickupOrder.WINNER_THEN_LOSER
    # H3
    short_in_battle: ShortInBattle = ShortInBattle.LOSES
    # H4 : un retour à un état déjà vu classe la partie comme infinie.
    detect_cycles: bool = True
    # H5 : garde-fou, None pour aucun plafond. Valeur provisoire, à fixer une fois
    # la distribution des durées observée.
    max_tricks: int | None = 100_000

    def __post_init__(self) -> None:
        if self.hidden_cards_per_battle < 0:
            raise ValueError("hidden_cards_per_battle must be >= 0")
        if self.max_tricks is not None and self.max_tricks <= 0:
            raise ValueError("max_tricks must be > 0 or None")

    def toDict(self) -> dict:
        data = asdict(self)
        data["battle_pickup_order"] = self.battle_pickup_order.value
        data["short_in_battle"] = self.short_in_battle.value
        return data


DEFAULT_RULES = RulesConfig()
