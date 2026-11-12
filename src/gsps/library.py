"""A library on disk: the current version of every table, resolved by the naming rules.

Expected layout (all files dated per :mod:`gsps.store.versioned`)::

    <root>/
      ANCHORS_<date>[_vN].csv
      FINDINGS_<date>[_vN].csv
      DELIVERABLES_<date>[_vN].csv
      TENSIONS_<date>[_vN].csv
      CITATION_MAP/CITATION_MAP_<date>[_vN].csv
      STATE_FLAGS.md            (optional; the default registry is used when absent)
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from gsps.model.records import Anchor, Citation, Deliverable, Finding, Tension
from gsps.store.csv_io import load_records
from gsps.store.versioned import latest
from gsps.vocab.registry import Registry


@dataclass
class Library:
    root: Path
    anchors: list[Anchor] = field(default_factory=list)
    findings: dict[str, Finding] = field(default_factory=dict)
    citations: list[Citation] = field(default_factory=list)
    deliverables: list[Deliverable] = field(default_factory=list)
    tensions: list[Tension] = field(default_factory=list)
    registry: Registry = field(default_factory=Registry.default)
    sources: dict[str, Path | None] = field(default_factory=dict)

    @property
    def anchors_by_id(self) -> dict[str, Anchor]:
        return {a.anchor_id: a for a in self.anchors}

    @classmethod
    def load(
        cls,
        root: str | Path,
        *,
        rename: Mapping[str, Mapping[str, str]] | None = None,
        registry_file: str = "STATE_FLAGS.md",
    ) -> Library:
        """Load the current version of each table.

        ``rename`` maps a table name (``"tensions"``, ``"findings"``, ...) to a column
        rename, for libraries whose column names differ from the field names.
        """
        r = Path(root)
        ren = {k: dict(v) for k, v in (rename or {}).items()}
        paths = {
            "anchors": latest(r, "ANCHORS"),
            "findings": latest(r, "FINDINGS"),
            "citations": latest(r / "CITATION_MAP", "CITATION_MAP"),
            "deliverables": latest(r, "DELIVERABLES"),
            "tensions": latest(r, "TENSIONS"),
        }
        reg_path = r / registry_file
        registry = Registry.from_markdown(reg_path) if reg_path.exists() else Registry.default()
        return cls(
            root=r,
            anchors=load_records(paths["anchors"], Anchor, rename=ren.get("anchors")),
            findings={
                f.anchor_id: f
                for f in load_records(paths["findings"], Finding, rename=ren.get("findings"))
            },
            citations=load_records(paths["citations"], Citation, rename=ren.get("citations")),
            deliverables=load_records(
                paths["deliverables"], Deliverable, rename=ren.get("deliverables")
            ),
            tensions=load_records(paths["tensions"], Tension, rename=ren.get("tensions")),
            registry=registry,
            sources=paths,
        )
