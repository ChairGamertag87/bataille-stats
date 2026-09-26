"""Écriture et lecture des résultats bruts.

Une campagne occupe un dossier results/<nom>/ :
- games.csv : une ligne par partie ;
- metadata.json : seed, nombre de parties, règles et versions, de quoi rejouer
  la campagne à l'identique ;
- trace_game_<indice>.csv et .json : le déroulé d'une partie rejouée ;
- snapshots.csv et .json : l'écart de cartes des parties encore en cours à
  certains plis de contrôle.
"""

import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from bataille.rules import RulesConfig

RESULTS_DIR = Path("results")

TRACE_COLUMNS = ["trick", "hand_1", "hand_2", "battles"]


def campaignDir(name: str, results_dir: Path = RESULTS_DIR) -> Path:
    return Path(results_dir) / name


def saveCampaign(
    name: str, rows: list[dict], seed: int, rules: RulesConfig, results_dir: Path = RESULTS_DIR
) -> Path:
    directory = campaignDir(name, results_dir)
    directory.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(directory / "games.csv", index=False)
    metadata = {
        "name": name,
        "seed": seed,
        "n_games": len(rows),
        "rules": rules.toDict(),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
    }
    _writeJson(directory / "metadata.json", metadata)
    return directory


def loadCampaign(name: str, results_dir: Path = RESULTS_DIR) -> tuple[pd.DataFrame, dict]:
    directory = campaignDir(name, results_dir)
    games = pd.read_csv(directory / "games.csv")
    metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    return games, metadata


def saveGameTrace(
    name: str,
    game_index: int,
    hand_sizes: list[tuple[int, int, int, int]],
    details: dict,
    results_dir: Path = RESULTS_DIR,
) -> Path:
    directory = campaignDir(name, results_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"trace_game_{game_index}.csv"
    pd.DataFrame(hand_sizes, columns=TRACE_COLUMNS).to_csv(path, index=False)
    _writeJson(directory / f"trace_game_{game_index}.json", details)
    return path


def loadGameTrace(name: str, game_index: int, results_dir: Path = RESULTS_DIR) -> tuple[pd.DataFrame, dict]:
    directory = campaignDir(name, results_dir)
    trace = pd.read_csv(directory / f"trace_game_{game_index}.csv")
    details = json.loads((directory / f"trace_game_{game_index}.json").read_text(encoding="utf-8"))
    return trace, details


def findGameTraces(name: str, results_dir: Path = RESULTS_DIR) -> list[int]:
    directory = campaignDir(name, results_dir)
    return sorted(int(path.stem.removeprefix("trace_game_")) for path in directory.glob("trace_game_*.csv"))


def saveSnapshots(
    name: str, rows: list[tuple[int, int, int]], checkpoints: tuple[int, ...], results_dir: Path = RESULTS_DIR
) -> Path:
    directory = campaignDir(name, results_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "snapshots.csv"
    pd.DataFrame(rows, columns=["game_index", "trick", "card_delta"]).to_csv(path, index=False)
    _writeJson(directory / "snapshots.json", {"checkpoints": list(checkpoints)})
    return path


def loadSnapshots(name: str, results_dir: Path = RESULTS_DIR) -> tuple[pd.DataFrame, list[int]]:
    directory = campaignDir(name, results_dir)
    snapshots = pd.read_csv(directory / "snapshots.csv")
    checkpoints = json.loads((directory / "snapshots.json").read_text(encoding="utf-8"))["checkpoints"]
    return snapshots, checkpoints


def _writeJson(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
