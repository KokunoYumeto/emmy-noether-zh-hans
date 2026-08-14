from __future__ import annotations

import csv
import hashlib
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "manifest.csv"
REPARSE_POINT = 0x400
FORBIDDEN_DIRS = {"b", "img", "sheet", "chg", "r36", "f36", "__pycache__"}


def digest(path: Path) -> tuple[int, str]:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            sha.update(chunk)
    return path.stat().st_size, sha.hexdigest().upper()


def is_reparse(path: Path) -> bool:
    stat = path.lstat()
    return path.is_symlink() or bool(getattr(stat, "st_file_attributes", 0) & REPARSE_POINT)


def safe(path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix()
    pure = PurePosixPath(relative)
    if not relative or "\\" in relative or ":" in relative or pure.is_absolute() or any(part in ("", ".", "..") for part in pure.parts):
        raise RuntimeError(f"unsafe package path: {relative!r}")
    return relative


def main() -> None:
    if MANIFEST.exists():
        raise SystemExit("refusing to overwrite manifest.csv")
    for name in FORBIDDEN_DIRS:
        if (ROOT / name).exists():
            raise SystemExit(f"forbidden mutable directory in static root: {name}")
    rows: list[tuple[str, int, str]] = []
    for path in ROOT.rglob("*"):
        relative = safe(path)
        if is_reparse(path):
            raise SystemExit(f"reparse point forbidden: {relative}")
        if path.is_file() and relative != "manifest.csv":
            size, sha256 = digest(path)
            rows.append((relative, size, sha256))
    rows.sort()
    names = [row[0] for row in rows]
    if len(names) != len(set(names)) or len(names) != len({name.casefold() for name in names}):
        raise SystemExit("duplicate or casefold-colliding path")
    required = {"return.json", "handoff.md", "verify.py", "seal.py", "reader.tex", "reader.pdf", "raw.pdf"}
    if not required.issubset(names):
        raise SystemExit(f"required payload member missing: {sorted(required - set(names))}")
    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["path", "bytes", "sha256"])
        writer.writerows(rows)
    print({"entries": len(rows), "member_bytes": sum(row[1] for row in rows), "manifest": digest(MANIFEST)})


if __name__ == "__main__":
    main()
