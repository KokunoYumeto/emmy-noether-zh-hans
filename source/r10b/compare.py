from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parent
WORK = ROOT.parent / "zh_r10b_w"
CURRENT = ROOT / "reader.pdf"
PREV = ROOT.parent / "zh_r10/reader.pdf"
OUT = ROOT / "compare.json"
PDFTOPPM = Path(r"C:\Users\Floris\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdftoppm.exe")
PREV_PIN = (3_129_035, "41FE49CAA081E5A22A4F8E3CEACFA046BD14E799EE806D9661AC8C4F9CE2E1CE")
PAGES = 424
EXPECTED_TITLE = "Noether Simplified Chinese cumulative rebase r10"
EXPECTED_AUTHOR = "Emmy Noether"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def ident(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": sha(data)}


def page_bytes(page: object) -> bytes:
    contents = page.get_contents()
    return b"" if contents is None else contents.get_data()


def render(pdf: Path, directory: Path) -> list[Path]:
    if directory.exists():
        raise RuntimeError(f"refusing to overwrite {directory}")
    directory.mkdir(parents=True)
    completed = subprocess.run(
        [str(PDFTOPPM), "-png", "-r", "120", str(pdf), str(directory / "p")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise RuntimeError(f"pdftoppm failed for {pdf}")
    pages = sorted(directory.glob("p-*.png"), key=lambda path: int(path.stem.rsplit("-", 1)[1]))
    if len(pages) != PAGES:
        raise RuntimeError(f"page count mismatch for {pdf}: {len(pages)}")
    return pages


def pixels(path: Path) -> tuple[list[int], str]:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        return [rgb.width, rgb.height], sha(rgb.tobytes())


def make_sheets(pages: list[Path], directory: Path) -> list[dict[str, object]]:
    directory.mkdir(parents=True, exist_ok=False)
    records = []
    per_sheet, columns, rows, thumb_w, thumb_h, label_h = 56, 7, 8, 180, 255, 20
    for sheet_index, start in enumerate(range(0, len(pages), per_sheet), 1):
        selected = pages[start : start + per_sheet]
        canvas = Image.new("RGB", (columns * thumb_w, rows * (thumb_h + label_h)), "white")
        draw = ImageDraw.Draw(canvas)
        for offset, page_path in enumerate(selected):
            with Image.open(page_path) as source:
                image = source.convert("RGB")
                image.thumbnail((thumb_w - 8, thumb_h - 8), Image.Resampling.LANCZOS)
                col, row = offset % columns, offset // columns
                x = col * thumb_w + (thumb_w - image.width) // 2
                y = row * (thumb_h + label_h) + label_h + (thumb_h - image.height) // 2
                canvas.paste(image, (x, y))
                draw.text((col * thumb_w + 4, row * (thumb_h + label_h) + 2), f"p{start + offset + 1}", fill="black")
        path = directory / f"s{sheet_index:02d}.png"
        canvas.save(path, format="PNG", optimize=True)
        records.append({"path": str(path), "bytes": path.stat().st_size, "sha256": sha(path.read_bytes()), "first_page": start + 1, "last_page": start + len(selected)})
    return records


def metadata(reader: PdfReader) -> dict[str, object]:
    value = reader.metadata or {}
    return {str(key): str(item) for key, item in sorted(value.items(), key=lambda row: str(row[0]))}


def main() -> None:
    if OUT.exists() or not PDFTOPPM.is_file():
        raise SystemExit("compare output exists or pdftoppm unavailable")
    if (PREV.stat().st_size, sha(PREV.read_bytes())) != PREV_PIN:
        raise SystemExit("frozen r10 PDF identity mismatch")
    old = PdfReader(str(PREV), strict=True)
    new = PdfReader(str(CURRENT), strict=True)
    if len(old.pages) != PAGES or len(new.pages) != PAGES:
        raise SystemExit("PDF page count mismatch")
    old_meta, new_meta = metadata(old), metadata(new)
    if new_meta.get("/Title") != EXPECTED_TITLE or new_meta.get("/Author") != EXPECTED_AUTHOR:
        raise SystemExit(f"new PDF metadata mismatch: {new_meta}")
    changed_meta = {key for key in set(old_meta) | set(new_meta) if old_meta.get(key) != new_meta.get(key)}
    if changed_meta != {"/Title"} or old_meta.get("/Title") != "Noether Simplified Chinese cumulative rebase r9":
        raise SystemExit(f"predecessor/successor metadata delta mismatch: {changed_meta}")

    pdf_rows = []
    for number, (old_page, new_page) in enumerate(zip(old.pages, new.pages), 1):
        old_content, new_content = page_bytes(old_page), page_bytes(new_page)
        old_text, new_text = old_page.extract_text() or "", new_page.extract_text() or ""
        old_geometry = [str(value) for value in old_page.mediabox] + [str(old_page.rotation)]
        new_geometry = [str(value) for value in new_page.mediabox] + [str(new_page.rotation)]
        pdf_rows.append({
            "page": number,
            "content_sha256_r10": sha(old_content),
            "content_sha256_r10b": sha(new_content),
            "content_equal": old_content == new_content,
            "text_sha256_r10": sha(old_text.encode("utf-8")),
            "text_sha256_r10b": sha(new_text.encode("utf-8")),
            "text_equal": old_text == new_text,
            "geometry_equal": old_geometry == new_geometry,
        })
    if not all(row["content_equal"] and row["text_equal"] and row["geometry_equal"] for row in pdf_rows):
        raise SystemExit("r10/r10b PDF content, text, or geometry delta")

    old_images = render(PREV, WORK / "r10_120")
    new_images = render(CURRENT, WORK / "r10b_120")
    raster_rows = []
    for number, (old_path, new_path) in enumerate(zip(old_images, new_images), 1):
        old_size, old_sha = pixels(old_path)
        new_size, new_sha = pixels(new_path)
        raster_rows.append({"page": number, "size": new_size, "r10_pixel_sha256": old_sha, "r10b_pixel_sha256": new_sha, "equal": old_size == new_size and old_sha == new_sha})
    if not all(row["equal"] for row in raster_rows):
        raise SystemExit("r10/r10b 120-DPI raster delta")
    sheets = make_sheets(new_images, WORK / "sheet")
    result = {
        "record_id": "ZH-NOETHER-CUM-R10B-R10-EQUALITY-001",
        "state": "PASS_MACHINE_VALIDATED_RELEASE_READY",
        "inputs": {"independently_inspected_frozen_r10": ident(PREV), "rebuilt_r10b": ident(CURRENT)},
        "metadata": {"predecessor": old_meta, "successor": new_meta, "changed_keys": sorted(changed_meta), "exact_title_author_pass": True},
        "pages": PAGES,
        "content_streams_equal": PAGES,
        "extracted_text_equal": PAGES,
        "geometry_equal": PAGES,
        "fresh_120_dpi_rasters_equal": PAGES,
        "pdf_page_records": pdf_rows,
        "raster_page_records": raster_rows,
        "contact_sheets": sheets,
        "checker_basis": "ZHCHK-NOETHER-R10-RETURN-001 found no substantive, mathematical, extraction, layout, or visual defect; all 424 r10 pages were inspected",
        "scope": "one PDF metadata title correction; no rendered body or substantive Chinese delta",
        "all_pass": True,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"pages": PAGES, "content": PAGES, "text": PAGES, "raster_120": PAGES, "sheets": len(sheets), "metadata_title": new_meta.get("/Title"), "all_pass": True}))


if __name__ == "__main__":
    main()
