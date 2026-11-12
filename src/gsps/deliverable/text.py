"""Page text for token checks."""

from __future__ import annotations

from pathlib import Path

_DASHES = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2212"), "-")


def normalize_page(text: str) -> str:
    """Unify dash variants so a hyphen on the page matches a hyphen in the approved wording."""
    return text.translate(_DASHES)


def docx_text(path: str | Path) -> str:
    """Paragraphs and table cells of a .docx. Requires the ``docx`` extra."""
    try:
        import docx  # type: ignore[import-not-found,unused-ignore]
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise RuntimeError("install the 'docx' extra: pip install 'gsps[docx]'") from exc
    d = docx.Document(str(path))
    parts = [p.text for p in d.paragraphs]
    parts += [c.text for t in d.tables for r in t.rows for c in r.cells]
    return "\n".join(parts)
