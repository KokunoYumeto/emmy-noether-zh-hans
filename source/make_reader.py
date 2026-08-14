from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pypdf
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, IndirectObject, NameObject


ROOT = Path(__file__).resolve().parent
BODY_TEX = ROOT / "reader.tex"
COVER_TEX = ROOT / "cover.tex"
BUILD_DOC = ROOT / "BUILD.md"

BODY_TEX_PIN = (
    1_874_083,
    "553446A494A59530946AB70EC2F672BED4D45A33B7FA554765A11B8C038DA6D4",
)
COVER_TEX_PIN = (
    3_861,
    "AE1FF7B63EAC73D82F71A6B57D7588BF95AF542251BAB67472EACD7D9637EA77",
)
FONT_PINS = {
    "NotoSansCJKsc-Bold.otf": (17_002_248, "B5F0D1A190A7F9B43C310A8850630AF12553DF32C4C050543F9059732D9B4C0A"),
    "NotoSansCJKsc-Regular.otf": (16_437_364, "2C76254F6FC379FDDFCE0A7E84FB5385BB135D3E399294F6EEB6680D0365B74B"),
    "NotoSansMono-Bold.ttf": (525_664, "BEB857BD799A114DE7D5D90CC75CC69F4B6EE8D401F4AB20697E6F9719A66DFC"),
    "NotoSansMono-Regular.ttf": (512_836, "D9E2B23D19F8230BE7146F409A52B1D23117E635E28F2E2892CF91B7382F325B"),
    "NotoSerifCJKsc-Bold.otf": (25_521_460, "8AF07D4B6C2E82BCC72A30E066EAF295F11B9424F4AAD2EAA9FE0E9C3B38FC73"),
    "NotoSerifCJKsc-Regular.otf": (24_543_080, "2A2EAE2628DF83556C54018C41E20FA532C1B862C5256AE8B3F23FEB918D12CA"),
    "OFL.txt": (4_386, "A216F6F8D85C7228093E0EE5E258D9D377E6671F68ACB4DB1930B29583D0F331"),
}
CMAP_PINS = {
    "oms.cmap": (2_370, "B0EA8E71B5D2E1DC86991867AF6B9547BE1BCC20EC7561D7C3BEDFA84204A999"),
    "omx.cmap": (3_001, "C07DF4892D287A36825A0611A1E2BE0C9F120260F632E00E17D4E8C5973331F8"),
    "umsb.cmap": (2_450, "22266C6FAA697A7266CF244EFF2A64037FF762F90B5AD123D8744054D2B02F82"),
}
FONT_MAP = {
    "CMSY8": "oms.cmap",
    "CMSY10": "oms.cmap",
    "MSBM10": "umsb.cmap",
    "CMEX7": "omx.cmap",
    "CMEX8": "omx.cmap",
    "CMEX10": "omx.cmap",
}

BODY_PAGES = 424
FINAL_PAGES = 425
BODY_SOURCE_DATE_EPOCH = "1786053600"
COVER_SOURCE_DATE_EPOCH = "1786701600"
FINAL_NAME = "00_NOETHER_zh-Hans_COMPLETE_READER.pdf"
FINAL_TITLE = "埃米·诺特数学著作全集——完整简体中文版"
EXPECTED_URIS = sorted(
    [
        "https://doi.org/10.5281/zenodo.21933034",
        "https://doi.org/10.5281/zenodo.21933035",
        "https://doi.org/10.5281/zenodo.20412587",
        "https://github.com/KokunoYumeto/emmy-noether-zh-hans",
    ]
)

# reader.tex deliberately records the historical font-family declarations.
# The public build stages an otherwise byte-derived copy and replaces exactly
# these three declarations so all text fonts come from source/fonts.
PORTABLE_FONT_REWRITES = {
    r"\setmainfont{Noto Serif}": (
        r"\setmainfont[Path=fonts/,BoldFont=NotoSerifCJKsc-Bold.otf,"
        r"ItalicFont=NotoSerifCJKsc-Regular.otf,ItalicFeatures={FakeSlant=0.2},"
        r"BoldItalicFont=NotoSerifCJKsc-Bold.otf,BoldItalicFeatures={FakeSlant=0.2}]"
        r"{NotoSerifCJKsc-Regular.otf}"
    ),
    r"\setsansfont{Noto Sans}": (
        r"\setsansfont[Path=fonts/,BoldFont=NotoSansCJKsc-Bold.otf]"
        r"{NotoSansCJKsc-Regular.otf}"
    ),
    r"\setmonofont{Noto Sans Mono}": (
        r"\setmonofont[Path=fonts/,BoldFont=NotoSansMono-Bold.ttf]"
        r"{NotoSansMono-Regular.ttf}"
    ),
}


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            hasher.update(chunk)
    return hasher.hexdigest().upper()


def identity(path: Path) -> dict[str, object]:
    return {"bytes": path.stat().st_size, "sha256": sha(path)}


def require_pin(path: Path, expected: tuple[int, str]) -> None:
    if not path.is_file() or (path.stat().st_size, sha(path)) != expected:
        raise SystemExit(f"identity mismatch: {path}")


def require_tool(name: str) -> str:
    # On Windows, prefer the real executable over a same-name .cmd shim. A
    # bundled runtime may put a wrapper first on PATH even when its private
    # target is absent, while the installed Poppler/XeTeX executable is valid.
    path = shutil.which(f"{name}.exe") if os.name == "nt" else None
    path = path or shutil.which(name)
    if not path:
        raise SystemExit(f"required command not found on PATH: {name}")
    return path


def tool_version(command: str, *args: str) -> str:
    completed = subprocess.run(
        [command, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True
    )
    text = (completed.stdout or completed.stderr).strip()
    return text.splitlines()[0] if text else "unknown"


def deref(value: Any) -> Any:
    return value.get_object() if hasattr(value, "get_object") else value


def ref_id(value: Any) -> tuple[int | None, int | None]:
    ref = value if isinstance(value, IndirectObject) else getattr(value, "indirect_reference", None)
    return (getattr(ref, "idnum", None), getattr(ref, "generation", None))


def base_name(font: Any) -> str:
    return str(font.get("/BaseFont", "")).lstrip("/").rsplit("+", 1)[-1]


def page_stream_hash(page: Any) -> str:
    contents = page.get_contents()
    return digest_bytes(b"" if contents is None else contents.get_data())


def box_tuple(page: Any, key: str) -> tuple[float, float, float, float]:
    box = getattr(page, key)
    return tuple(round(float(item), 6) for item in (box.left, box.bottom, box.right, box.top))


def annotation_counts(reader: PdfReader) -> list[int]:
    rows = []
    for page in reader.pages:
        annotations = page.get("/Annots", [])
        annotations = deref(annotations)
        rows.append(len(annotations))
    return rows


def outline_count(items: list[Any]) -> int:
    total = 0
    for item in items:
        if isinstance(item, list):
            total += outline_count(item)
        else:
            total += 1
    return total


def cover_uris(reader: PdfReader) -> list[str]:
    annotations = deref(reader.pages[0].get("/Annots", []))
    values = []
    for reference in annotations:
        annotation = deref(reference)
        action = annotation.get("/A")
        if action and action.get("/S") == "/URI":
            values.append(str(action.get("/URI")))
    return sorted(values)


def font_program_signature(reader: PdfReader) -> list[tuple[str, str, str]]:
    records: set[tuple[str, str, str]] = set()
    seen: set[tuple[int | None, int | None]] = set()
    for page in reader.pages:
        resources = deref(page.get("/Resources"))
        fonts = deref(resources.get("/Font")) if resources else None
        if not fonts:
            continue
        for value in fonts.values():
            key = ref_id(value)
            if key in seen:
                continue
            seen.add(key)
            font = deref(value)
            descriptor = deref(font.get("/FontDescriptor"))
            if not descriptor:
                continue
            for label in ("/FontFile", "/FontFile2", "/FontFile3"):
                if label in descriptor:
                    program = deref(descriptor[label]).get_data()
                    records.add((base_name(font), label, digest_bytes(program)))
    return sorted(records)


def missing_tounicode(reader: PdfReader) -> dict[tuple[int | None, int | None], str]:
    result: dict[tuple[int | None, int | None], str] = {}
    for page in reader.pages:
        resources = deref(page.get("/Resources"))
        fonts = deref(resources.get("/Font")) if resources else None
        if not fonts:
            continue
        for value in fonts.values():
            font = deref(value)
            if "/ToUnicode" not in font:
                result[ref_id(value)] = base_name(font)
    return result


def stage_body_tex(destination: Path) -> list[dict[str, str]]:
    text = BODY_TEX.read_text(encoding="utf-8")
    records = []
    for before, after in PORTABLE_FONT_REWRITES.items():
        if text.count(before) != 1:
            raise SystemExit(f"portable-font rewrite preimage mismatch: {before}")
        text = text.replace(before, after)
        records.append({"from": before, "to": after})
    destination.write_text(text, encoding="utf-8", newline="\n")
    return records


def run_xelatex(
    xelatex: str,
    tex: Path,
    output_dir: Path,
    jobname: str,
    source_date_epoch: str,
) -> list[dict[str, object]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["SOURCE_DATE_EPOCH"] = source_date_epoch
    env["FORCE_SOURCE_DATE"] = "1"
    command = [
        xelatex,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        "-no-shell-escape",
        f"-jobname={jobname}",
        f"-output-directory={output_dir}",
        str(tex),
    ]
    passes = []
    pass_pdfs: dict[int, bytes] = {}
    for number in (1, 2, 3):
        completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
        log = output_dir / f"{jobname}.log"
        pdf = output_dir / f"{jobname}.pdf"
        log_text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
        record = {
            "pass": number,
            "exit_code": completed.returncode,
            "stdout_sha256": digest_bytes(completed.stdout + completed.stderr),
            "log_sha256": sha(log) if log.is_file() else None,
            "pdf": identity(pdf) if pdf.is_file() else None,
            "signals": {
                "fatal": log_text.count("Fatal error") + log_text.count("Emergency stop"),
                "overfull": log_text.count("Overfull \\hbox") + log_text.count("Overfull \\vbox"),
                "missing_character": log_text.count("Missing character:"),
            },
        }
        passes.append(record)
        if completed.returncode != 0 or not pdf.is_file():
            stdout = output_dir / f"{jobname}-pass{number}.stdout.txt"
            stdout.write_bytes(completed.stdout + completed.stderr)
            raise SystemExit(f"XeLaTeX failed for {jobname} pass {number}; see {stdout}")
        if any(record["signals"].values()):
            raise SystemExit(f"XeLaTeX quality gate failed for {jobname} pass {number}: {record['signals']}")
        pass_pdfs[number] = pdf.read_bytes()
    if pass_pdfs[2] != pass_pdfs[3]:
        raise SystemExit(f"XeLaTeX passes 2 and 3 are not byte-identical: {jobname}")
    return passes


def inject_tounicode(raw: Path, destination: Path, cmap_data: dict[str, bytes]) -> list[dict[str, object]]:
    reader = PdfReader(str(raw), strict=True)
    writer = PdfWriter(clone_from=reader)
    map_refs = {}
    for name in sorted(cmap_data):
        stream = DecodedStreamObject()
        stream.set_data(cmap_data[name])
        map_refs[name] = writer._add_object(stream)
    injected: dict[tuple[int | None, int | None], dict[str, object]] = {}
    for page_number, page in enumerate(writer.pages, 1):
        resources = deref(page.get("/Resources"))
        fonts = deref(resources.get("/Font")) if resources else None
        if not fonts:
            continue
        for value in fonts.values():
            font = deref(value)
            key = ref_id(value)
            name = base_name(font)
            if key in injected:
                injected[key]["pages"].append(page_number)
                continue
            if "/ToUnicode" in font:
                continue
            if name not in FONT_MAP:
                raise SystemExit(f"unrecognized missing-ToUnicode font: {name}")
            cmap = FONT_MAP[name]
            font[NameObject("/ToUnicode")] = map_refs[cmap]
            injected[key] = {"font": name, "cmap": cmap, "pages": [page_number]}
    names = {record["font"] for record in injected.values()}
    if names != set(FONT_MAP) or len(injected) != len(FONT_MAP):
        raise SystemExit(f"missing-ToUnicode allowlist mismatch: {sorted(names)}")
    with destination.open("wb") as stream:
        writer.write(stream)
    return sorted(injected.values(), key=lambda record: str(record["font"]))


def compare_body_invariants(before_path: Path, after_path: Path) -> dict[str, object]:
    before = PdfReader(str(before_path), strict=True)
    after = PdfReader(str(after_path), strict=True)
    if len(before.pages) != BODY_PAGES or len(after.pages) != BODY_PAGES:
        raise SystemExit("body page-count invariant failed")
    streams = 0
    geometry = 0
    for left, right in zip(before.pages, after.pages):
        streams += page_stream_hash(left) == page_stream_hash(right)
        geometry += all(box_tuple(left, key) == box_tuple(right, key) for key in ("mediabox", "cropbox"))
    if streams != BODY_PAGES or geometry != BODY_PAGES:
        raise SystemExit("ToUnicode injection changed body content streams or geometry")
    if annotation_counts(before) != annotation_counts(after):
        raise SystemExit("ToUnicode injection changed annotations")
    before_destinations = before.named_destinations
    after_destinations = after.named_destinations
    if set(before_destinations) != set(after_destinations):
        raise SystemExit("ToUnicode injection changed destination names")
    destination_pages = sum(
        before.get_destination_page_number(value)
        == after.get_destination_page_number(after_destinations[name])
        for name, value in before_destinations.items()
    )
    if destination_pages != len(before_destinations):
        raise SystemExit("ToUnicode injection changed destination pages")
    if outline_count(before.outline) != outline_count(after.outline):
        raise SystemExit("ToUnicode injection changed outlines")
    if font_program_signature(before) != font_program_signature(after):
        raise SystemExit("ToUnicode injection changed embedded font programs")
    return {
        "content_streams_equal": f"{streams}/{BODY_PAGES}",
        "geometry_equal": f"{geometry}/{BODY_PAGES}",
        "annotations": sum(annotation_counts(after)),
        "named_destinations": len(after_destinations),
        "destination_pages_equal": destination_pages,
        "outlines": outline_count(after.outline),
        "font_programs_equal": True,
    }


def pdffonts_gate(pdffonts: str, pdf: Path) -> dict[str, object]:
    completed = subprocess.run(
        [pdffonts, str(pdf)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True
    )
    rows = [line.split() for line in completed.stdout.splitlines()[2:] if line.strip()]
    malformed = [row for row in rows if len(row) < 8]
    missing = [row[0] for row in rows if len(row) >= 8 and row[-3].lower() != "yes"]
    if not rows or malformed or missing:
        raise SystemExit(f"pdffonts ToUnicode gate failed: missing={missing}, malformed={len(malformed)}")
    return {"font_rows": len(rows), "all_uni_yes": True, "stdout_sha256": digest_bytes(completed.stdout.encode("utf-8"))}


def text_counts(text: str) -> dict[str, int]:
    return {
        "disallowed_c0": sum(1 for char in text if ord(char) < 32 and char not in "\n\r\t\f"),
        "replacement_characters": text.count("\ufffd"),
        "nul": text.count("\x00"),
    }


def extraction_gate(pdftotext: str, pdf: Path) -> dict[str, object]:
    poppler_bytes = subprocess.run([pdftotext, "-layout", str(pdf), "-"], capture_output=True, check=True).stdout
    poppler_text = poppler_bytes.decode("utf-8", errors="replace")
    reader = PdfReader(str(pdf), strict=True)
    pypdf_text = "\f".join(page.extract_text() or "" for page in reader.pages)
    result = {
        "poppler": {**text_counts(poppler_text), "text_sha256": digest_bytes(poppler_bytes)},
        "pypdf": {**text_counts(pypdf_text), "text_sha256": digest_bytes(pypdf_text.encode("utf-8"))},
    }
    if any(value for tool in result.values() for key, value in tool.items() if key != "text_sha256"):
        raise SystemExit(f"dual-extractor gate failed: {result}")
    return result


def merge(cover_path: Path, body_path: Path, destination: Path) -> None:
    cover = PdfReader(str(cover_path), strict=True)
    if len(cover.pages) != 1:
        raise SystemExit("cover is not exactly one page")
    writer = PdfWriter(clone_from=str(body_path))
    writer.insert_page(cover.pages[0], 0)
    writer.add_metadata(
        {
            "/Title": FINAL_TITLE,
            "/Author": "Emmy Noether; Manuscript Typesetting Project; OpenAI Codex",
            "/Subject": "Complete PRC-oriented Simplified-Chinese corpus edition, version 1.0.0",
            "/Keywords": "Emmy Noether, Simplified Chinese, translation, mathematics, algebra",
        }
    )
    with destination.open("wb") as stream:
        writer.write(stream)


def validate_merge(body_path: Path, final_path: Path) -> dict[str, object]:
    body = PdfReader(str(body_path), strict=True)
    final = PdfReader(str(final_path), strict=True)
    if len(body.pages) != BODY_PAGES or len(final.pages) != FINAL_PAGES:
        raise SystemExit("final page-count gate failed")
    streams = 0
    geometry = 0
    for number, body_page in enumerate(body.pages):
        final_page = final.pages[number + 1]
        streams += page_stream_hash(body_page) == page_stream_hash(final_page)
        geometry += all(box_tuple(body_page, key) == box_tuple(final_page, key) for key in ("mediabox", "cropbox"))
    if streams != BODY_PAGES or geometry != BODY_PAGES:
        raise SystemExit("cover merge changed body content streams or geometry")
    body_annotations = annotation_counts(body)
    final_annotations = annotation_counts(final)
    if body_annotations != final_annotations[1:]:
        raise SystemExit("cover merge changed body annotations")
    if cover_uris(final) != EXPECTED_URIS:
        raise SystemExit("cover URI gate failed")
    body_destinations = body.named_destinations
    final_destinations = final.named_destinations
    if set(body_destinations) != set(final_destinations):
        raise SystemExit("cover merge changed destination names")
    shifted = sum(
        final.get_destination_page_number(final_destinations[name])
        == body.get_destination_page_number(destination) + 1
        for name, destination in body_destinations.items()
    )
    if shifted != len(body_destinations):
        raise SystemExit("cover merge did not shift every destination by one page")
    metadata = final.metadata or {}
    if str(metadata.get("/Title")) != FINAL_TITLE:
        raise SystemExit("final title metadata mismatch")
    if outline_count(body.outline) != outline_count(final.outline):
        raise SystemExit("cover merge changed outline count")
    return {
        "pages": len(final.pages),
        "body_content_streams_equal": f"{streams}/{BODY_PAGES}",
        "body_geometry_equal": f"{geometry}/{BODY_PAGES}",
        "body_annotation_page_counts_equal": f"{BODY_PAGES}/{BODY_PAGES}",
        "annotations": {"body": sum(body_annotations), "cover": final_annotations[0], "reader": sum(final_annotations)},
        "named_destinations": {"body": len(body_destinations), "reader": len(final_destinations), "shifted_by_one": shifted},
        "outlines": {"body": outline_count(body.outline), "reader": outline_count(final.outline)},
        "cover_uris": cover_uris(final),
    }


def render_qa(pdftoppm: str, pdf: Path, qa_dir: Path, force: bool) -> list[dict[str, object]]:
    expected = {"cover.png", "body-first.png", "body-last.png"}
    if qa_dir.exists():
        members = {path.name for path in qa_dir.iterdir()}
        if members and (not force or not members <= expected):
            raise SystemExit(f"QA directory contains files that cannot be replaced safely: {qa_dir}")
        for name in sorted(members):
            path = qa_dir / name
            if not path.is_file():
                raise SystemExit(f"QA directory contains a non-file member: {path}")
            path.unlink()
    qa_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for page, name in ((1, "cover"), (2, "body-first"), (FINAL_PAGES, "body-last")):
        stem = qa_dir / name
        subprocess.run(
            [pdftoppm, "-f", str(page), "-l", str(page), "-singlefile", "-png", "-r", "180", str(pdf), str(stem)],
            capture_output=True,
            check=True,
        )
        image = stem.with_suffix(".png")
        if not image.is_file():
            raise SystemExit(f"representative render missing: {image}")
        rows.append({"page": page, "path": str(image), **identity(image)})
    return rows


def user_path(value: Path | None, default: Path) -> Path:
    if value is None:
        return default.resolve()
    return (value if value.is_absolute() else Path.cwd() / value).resolve()


@contextmanager
def managed_work_dir(output_parent: Path):
    """Use one validated, output-local path so XeLaTeX sees a stable input path."""
    parent = output_parent.resolve()
    parent.mkdir(parents=True, exist_ok=True)
    work = (parent / ".noether-zh-work").resolve()
    if work.parent != parent or work.name != ".noether-zh-work":
        raise SystemExit("unsafe work-directory resolution")
    if work.exists():
        raise SystemExit(f"work directory already exists; remove it after checking its contents: {work}")
    work.mkdir()
    marker = work / ".owner"
    marker.write_text("noether-zh-hans-portable-build/1\n", encoding="ascii", newline="\n")
    succeeded = False
    try:
        yield work
        succeeded = True
    finally:
        if succeeded and (
            work.is_dir()
            and marker.is_file()
            and marker.read_text(encoding="ascii") == "noether-zh-hans-portable-build/1\n"
            and work.parent == parent
            and work.name == ".noether-zh-work"
        ):
            shutil.rmtree(work)
        elif succeeded and work.exists():
            raise RuntimeError(f"refusing unsafe work-directory cleanup: {work}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the portable 425-page Simplified-Chinese Noether reader")
    parser.add_argument("--output", type=Path, help=f"output PDF (default: source/out/{FINAL_NAME})")
    parser.add_argument("--receipt", type=Path, help="JSON build receipt (default: next to output PDF)")
    parser.add_argument("--qa-dir", type=Path, help="optional directory for three representative 180-dpi PNG renders")
    parser.add_argument("--force", action="store_true", help="replace an existing output PDF/receipt")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = user_path(args.output, ROOT / "out" / FINAL_NAME)
    receipt_path = user_path(args.receipt, output.with_suffix(".build.json"))
    qa_dir = user_path(args.qa_dir, Path()) if args.qa_dir is not None else None
    if output == receipt_path or output in (BODY_TEX.resolve(), COVER_TEX.resolve()):
        raise SystemExit("unsafe output path")
    for path in (output, receipt_path):
        if path.exists() and not args.force:
            raise SystemExit(f"refusing to overwrite without --force: {path}")

    require_pin(BODY_TEX, BODY_TEX_PIN)
    require_pin(COVER_TEX, COVER_TEX_PIN)
    if not BUILD_DOC.is_file():
        raise SystemExit(f"missing build documentation: {BUILD_DOC}")
    for name, expected in FONT_PINS.items():
        require_pin(ROOT / "fonts" / name, expected)
    for name, expected in CMAP_PINS.items():
        require_pin(ROOT / "map" / name, expected)

    xelatex = require_tool("xelatex")
    pdffonts = require_tool("pdffonts")
    pdftotext = require_tool("pdftotext")
    pdftoppm = require_tool("pdftoppm") if qa_dir is not None else None

    with managed_work_dir(output.parent) as work:
        staged_tex = work / "reader-portable.tex"
        rewrites = stage_body_tex(staged_tex)
        body_dir = work / "body"
        cover_dir = work / "cover"
        body_passes = run_xelatex(xelatex, staged_tex, body_dir, "body", BODY_SOURCE_DATE_EPOCH)
        raw_body = body_dir / "body.pdf"
        if len(PdfReader(str(raw_body), strict=True).pages) != BODY_PAGES:
            raise SystemExit("portable body did not compile to 424 pages")

        raw_missing = missing_tounicode(PdfReader(str(raw_body), strict=True))
        if set(raw_missing.values()) != set(FONT_MAP) or len(raw_missing) != len(FONT_MAP):
            raise SystemExit(f"raw missing-ToUnicode gate mismatch: {sorted(raw_missing.values())}")
        cmap_data = {name: (ROOT / "map" / name).read_bytes() for name in CMAP_PINS}
        fixed_one = work / "body-fixed-one.pdf"
        fixed_two = work / "body-fixed-two.pdf"
        injected_one = inject_tounicode(raw_body, fixed_one, cmap_data)
        injected_two = inject_tounicode(raw_body, fixed_two, cmap_data)
        if injected_one != injected_two or fixed_one.read_bytes() != fixed_two.read_bytes():
            raise SystemExit("ToUnicode injection is not byte-deterministic")
        if missing_tounicode(PdfReader(str(fixed_one), strict=True)):
            raise SystemExit("fixed body still contains a font without ToUnicode")
        body_invariants = compare_body_invariants(raw_body, fixed_one)
        font_gate = pdffonts_gate(pdffonts, fixed_one)
        body_extraction = extraction_gate(pdftotext, fixed_one)

        cover_passes = run_xelatex(xelatex, COVER_TEX, cover_dir, "cover", COVER_SOURCE_DATE_EPOCH)
        cover = cover_dir / "cover.pdf"
        merged_one = work / "reader-one.pdf"
        merged_two = work / "reader-two.pdf"
        merge(cover, fixed_one, merged_one)
        merge(cover, fixed_one, merged_two)
        if merged_one.read_bytes() != merged_two.read_bytes():
            raise SystemExit("cover merge is not byte-deterministic")
        merge_gate = validate_merge(fixed_one, merged_one)
        final_extraction = extraction_gate(pdftotext, merged_one)

        renders = (
            render_qa(pdftoppm, merged_one, qa_dir, args.force)
            if qa_dir is not None and pdftoppm is not None
            else []
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(merged_one, output)
        receipt = {
            "schema": "noether-zh-hans-portable-build/1",
            "state": "PASS_MACHINE_VALIDATED",
            "source_root": str(ROOT),
            "source": {
                "reader.tex": identity(BODY_TEX),
                "cover.tex": identity(COVER_TEX),
                "make_reader.py": identity(Path(__file__).resolve()),
                "BUILD.md": identity(BUILD_DOC),
            },
            "portable_font_rewrites": rewrites,
            "bundled_fonts": {name: {"bytes": size, "sha256": value} for name, (size, value) in FONT_PINS.items()},
            "bundled_cmaps": {name: {"bytes": size, "sha256": value} for name, (size, value) in CMAP_PINS.items()},
            "tools": {
                "python": sys.version.splitlines()[0],
                "python_executable": str(Path(sys.executable).resolve()),
                "pypdf": pypdf.__version__,
                "xelatex": tool_version(xelatex, "--version"),
                "pdffonts": tool_version(pdffonts, "-v"),
                "pdftotext": tool_version(pdftotext, "-v"),
                "pdftoppm": tool_version(pdftoppm, "-v") if pdftoppm is not None else None,
            },
            "body": {
                "pages": BODY_PAGES,
                "raw": identity(raw_body),
                "fixed": identity(fixed_one),
                "xelatex_passes": body_passes,
                "injected_fonts": injected_one,
                "invariants": body_invariants,
                "pdffonts": font_gate,
                "extraction": body_extraction,
            },
            "cover": {"pages": 1, "pdf": identity(cover), "xelatex_passes": cover_passes},
            "reader": {"path": str(output), "pages": FINAL_PAGES, **identity(output)},
            "merge": {**merge_gate, "two_runs_byte_identical": True},
            "extraction": final_extraction,
            "representative_renders": renders,
            "claims": {
                "language": "zh-Hans-CN / PRC-oriented Simplified Chinese",
                "hant": "not included",
                "zh_Hans_SG": "not included",
                "external_or_human_certification": False,
            },
        }

    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    receipt_path.write_text(payload, encoding="utf-8", newline="\n")
    print(json.dumps({"reader": receipt["reader"], "receipt": {"path": str(receipt_path), **identity(receipt_path)}}, ensure_ascii=True))


if __name__ == "__main__":
    main()
