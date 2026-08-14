from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
WORK = ROOT.parent / "zh_r10b_w"
RAW = ROOT / "raw.pdf"
FINAL = ROOT / "reader.pdf"
OUT = ROOT / "render.json"
PDFTOPPM = Path(r"C:\Users\Floris\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdftoppm.exe")
PAGE_COUNT = 424


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def ident(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(data), "sha256": digest(data)}


def render(source: Path, directory: Path) -> list[Path]:
    if directory.exists():
        raise RuntimeError(f"refusing to overwrite {directory}")
    directory.mkdir(parents=True)
    completed = subprocess.run(
        [str(PDFTOPPM), "-png", "-r", "36", str(source), str(directory / "p")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise RuntimeError(f"pdftoppm failed for {source.name}")
    pages = sorted(directory.glob("p-*.png"))
    if len(pages) != PAGE_COUNT:
        raise RuntimeError(f"page count mismatch for {source.name}: {len(pages)}")
    return pages


def pixels(path: Path) -> tuple[list[int], str]:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        return [rgb.width, rgb.height], digest(rgb.tobytes())


def main() -> None:
    if OUT.exists() or not PDFTOPPM.is_file():
        raise SystemExit("render output exists or pdftoppm unavailable")
    fix = json.loads((ROOT / "fix.json").read_text(encoding="utf-8"))
    if fix.get("record_id") != "ZH-NOETHER-CUM-R10B-CMAP-FIX-001" or not fix.get("invariants", {}).get("all_pass"):
        raise SystemExit("r10b fix receipt state mismatch")
    if ident(RAW) != fix["raw_pdf"] or ident(FINAL) != fix["fixed_pdf"]:
        raise SystemExit("raw/final identity mismatch against fix receipt")
    raw_pages = render(RAW, WORK / "r36")
    final_pages = render(FINAL, WORK / "f36")
    records = []
    for page, (raw_page, final_page) in enumerate(zip(raw_pages, final_pages), 1):
        raw_size, raw_sha = pixels(raw_page)
        final_size, final_sha = pixels(final_page)
        records.append({
            "page": page,
            "size": raw_size,
            "raw_pixel_sha256": raw_sha,
            "fixed_pixel_sha256": final_sha,
            "equal": raw_size == final_size and raw_sha == final_sha,
        })
    if not all(row["equal"] for row in records):
        raise SystemExit("raw/final visual-layout mutation detected")
    result = {
        "record_id": "ZH-NOETHER-CUM-R10B-RENDER-001",
        "state": "PASS_RAW_FIXED_424_OF_424_PIXEL_IDENTICAL",
        "method": "Poppler pdftoppm 36 DPI; RGB pixel SHA-256",
        "inputs": {"raw": ident(RAW), "fixed": ident(FINAL)},
        "pages": PAGE_COUNT,
        "pixel_identical_pages": PAGE_COUNT,
        "all_pass": True,
        "page_records": records,
        "scratch": "../zh_r10b_w/r36 and ../zh_r10b_w/f36; excluded from static successor",
        "scope": "computational CMap-layout invariance only; not an independent linguistic or every-page visual verdict",
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"pages": PAGE_COUNT, "pixel_identical": PAGE_COUNT, "all_pass": True}))


if __name__ == "__main__":
    main()
