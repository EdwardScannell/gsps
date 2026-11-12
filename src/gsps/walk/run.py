"""Walk runs: one folder per review, frozen once written.

``runs/WR-###_<docversion>_<YYYYMMDD>/``. The next run number is the highest used plus one.
Files are added with exclusive create. :meth:`WalkRun.freeze` writes a manifest of every
file's sha256; after that the run accepts no new files, and :meth:`WalkRun.verify`
proves nothing changed.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path

from gsps.store.fingerprint import sha256_file
from gsps.store.versioned import write_new

MANIFEST = "MANIFEST.json"
_RUN = re.compile(r"^WR-(\d{3,})_")


class RunFrozenError(RuntimeError):
    pass


@dataclass(frozen=True)
class WalkRun:
    path: Path

    @property
    def run_id(self) -> str:
        return self.path.name.split("_", 1)[0]

    @classmethod
    def create(cls, runs_dir: str | Path, doc_version: str, on: dt.date | None = None) -> WalkRun:
        root = Path(runs_dir)
        root.mkdir(parents=True, exist_ok=True)
        used = [0] + [int(m[1]) for p in root.iterdir() if (m := _RUN.match(p.name))]
        day = (on or dt.date.today()).strftime("%Y%m%d")
        safe = re.sub(r"[^A-Za-z0-9.-]+", "-", doc_version).strip("-") or "doc"
        path = root / f"WR-{max(used) + 1:03d}_{safe}_{day}"
        path.mkdir()
        return cls(path)

    @property
    def frozen(self) -> bool:
        return (self.path / MANIFEST).exists()

    def add_file(self, name: str, text: str) -> Path:
        if self.frozen:
            raise RunFrozenError(f"{self.run_id} is frozen; start a new run")
        return write_new(self.path / name, text)

    def freeze(self, note: str = "") -> Path:
        if self.frozen:
            raise RunFrozenError(f"{self.run_id} is already frozen")
        files = {
            p.relative_to(self.path).as_posix(): sha256_file(p)
            for p in sorted(self.path.rglob("*"))
            if p.is_file()
        }
        manifest = {
            "run_id": self.run_id,
            "frozen_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
            "note": note,
            "files": files,
        }
        return write_new(self.path / MANIFEST, json.dumps(manifest, indent=2) + "\n")

    def verify(self) -> list[str]:
        """Differences between the folder and its manifest. Empty means intact."""
        if not self.frozen:
            return ["not frozen"]
        manifest = json.loads((self.path / MANIFEST).read_text(encoding="utf-8"))
        listed: dict[str, str] = manifest["files"]
        present = {
            p.relative_to(self.path).as_posix(): p
            for p in self.path.rglob("*")
            if p.is_file() and p.name != MANIFEST
        }
        problems = [f"missing: {n}" for n in sorted(set(listed) - set(present))]
        problems += [f"added after freeze: {n}" for n in sorted(set(present) - set(listed))]
        problems += [
            f"changed: {n}"
            for n in sorted(set(listed) & set(present))
            if sha256_file(present[n]) != listed[n]
        ]
        return problems
