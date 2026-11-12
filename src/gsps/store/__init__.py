"""Storage discipline: dated versions, never edit in place, CSV through a parser only."""

from gsps.store.csv_io import load_records, read_rows, write_rows
from gsps.store.fingerprint import sha256_bytes, sha256_file
from gsps.store.versioned import (
    VersionedName,
    latest,
    mark_to_delete,
    next_version_path,
    parse_versioned,
    write_new,
)

__all__ = [
    "VersionedName",
    "latest",
    "load_records",
    "mark_to_delete",
    "next_version_path",
    "parse_versioned",
    "read_rows",
    "sha256_bytes",
    "sha256_file",
    "write_new",
    "write_rows",
]
