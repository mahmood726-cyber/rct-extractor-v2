from __future__ import annotations

from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]


def first_existing(candidates: Iterable[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def find_pairwise70_dir() -> Path:
    candidates = [
        REPO_ROOT / "Pairwise70" / "data",
        REPO_ROOT / "data" / "Pairwise70",
        Path("D:/Pairwise70/data"),
        Path("C:/Pairwise70/data"),
        Path.home() / "OneDrive - NHS" / "Documents" / "Pairwise70" / "data",
        Path.home() / "Documents" / "Pairwise70" / "data",
    ]
    resolved = first_existing(candidates)
    if resolved is None:
        tried = ", ".join(str(path) for path in candidates)
        raise FileNotFoundError(f"Could not find Pairwise70 data directory. Tried: {tried}")
    return resolved


def default_corpus_dir(name: str) -> Path:
    candidates = [
        REPO_ROOT / name,
        Path(f"D:/{name}"),
        Path(f"C:/{name}"),
        Path.home() / name,
    ]
    resolved = first_existing(candidates)
    if resolved is not None:
        return resolved
    return REPO_ROOT / name
