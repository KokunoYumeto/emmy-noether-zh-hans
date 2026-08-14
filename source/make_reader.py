from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from pypdf import PdfReader, PdfWriter


ROOT = Path(r"C:\Users\Floris\Documents\interlanguage\03_projects\noether\10_zh")
REPO = ROOT / "repo"
SOURCE = REPO / "source"
EVIDENCE = REPO / "evidence"
READER = REPO / "reader"
WORK = ROOT / "work"
TMP = WORK / "tmp"
LIVE = Path(r"C:\Users\Floris\Documents\interlanguage\03_projects\language_management\cjk\03_working_translations\zh_r10b")
HANDOFF = Path(r"C:\Users\Floris\Documents\interlanguage\04_handoffs\zh_r10b")
OFL = Path(r"C:\Users\Floris\Documents\interlanguage\03_projects\language_management\south_asian\hindi_complete_open_math_20260812\01_authority\fonts\noto_serif_devanagari\OFL.txt")

BODY_TEX_SHA = "553446A494A59530946AB70EC2F672BED4D45A33B7FA554765A11B8C038DA6D4"
BODY_PDF_SHA = "0C457AB0C5F31BE1F6C8B5A4EC7ACB657ABE67979D5E9339BA493B599BC2D544"
BODY_TEX_BYTES = 1_874_083
BODY_PDF_BYTES = 3_129_044
BODY_PAGES = 424
SOURCE_DATE_EPOCH = "1786701600"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def copy_exact(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise SystemExit(f"missing source: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    if source.stat().st_size != destination.stat().st_size or sha(source) != sha(destination):
        raise SystemExit(f"copy mismatch: {destination}")


def clean_tmp() -> None:
    if TMP.exists():
        resolved = TMP.resolve()
        if resolved.parent != WORK.resolve() or resolved.name != "tmp":
            raise SystemExit("unsafe temporary path")
        shutil.rmtree(TMP)
    TMP.mkdir(parents=True)


def prepare_sources() -> None:
    body_tex = LIVE / "reader.tex"
    body_pdf = LIVE / "reader.pdf"
    if body_tex.stat().st_size != BODY_TEX_BYTES or sha(body_tex) != BODY_TEX_SHA:
        raise SystemExit("frozen body TeX identity mismatch")
    if body_pdf.stat().st_size != BODY_PDF_BYTES or sha(body_pdf) != BODY_PDF_SHA:
        raise SystemExit("frozen body PDF identity mismatch")
    copy_exact(body_tex, SOURCE / "reader.tex")
    for path in sorted((LIVE / "fonts").glob("*")):
        if path.is_file():
            copy_exact(path, SOURCE / "fonts" / path.name)
    copy_exact(OFL, SOURCE / "fonts" / "OFL.txt")
    for path in sorted((LIVE / "map").glob("*")):
        if path.is_file():
            copy_exact(path, SOURCE / "map" / path.name)
    for name in ("build.py", "fix.py", "scan.py", "render.py", "compare.py", "prep.py", "seal.py", "verify.py"):
        copy_exact(LIVE / name, SOURCE / "r10b" / name)
    copy_exact(Path(__file__), SOURCE / "make_reader.py")
    for name in ("v1.json", "v2.json", "freeze.json", "cleanup.json"):
        copy_exact(HANDOFF / name, EVIDENCE / "r10b" / name)


def run_cover_build() -> list[dict[str, object]]:
    env = os.environ.copy()
    env["SOURCE_DATE_EPOCH"] = SOURCE_DATE_EPOCH
    env["FORCE_SOURCE_DATE"] = "1"
    results = []
    for index in range(1, 4):
        command = [
            "xelatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={TMP}",
            str(SOURCE / "cover.tex"),
        ]
        run = subprocess.run(command, cwd=SOURCE, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        log_path = TMP / f"cover-pass{index}.stdout.txt"
        log_path.write_text(run.stdout + "\n--- STDERR ---\n" + run.stderr, encoding="utf-8", newline="\n")
        if run.returncode != 0:
            raise SystemExit(f"cover XeLaTeX pass {index} failed; see {log_path}")
        pdf = TMP / "cover.pdf"
        results.append({"pass": index, "pdf_bytes": pdf.stat().st_size, "pdf_sha256": sha(pdf)})
    if results[1]["pdf_sha256"] != results[2]["pdf_sha256"]:
        raise SystemExit("cover passes 2 and 3 are not byte-identical")
    return results


def merge(output: Path) -> None:
    cover = PdfReader(str(TMP / "cover.pdf"))
    # Clone the body as one document before inserting the external-link-only
    # cover. This preserves all 760 body annotations and 2,102 named
    # destinations; append() drops one inherited body annotation on page 242.
    writer = PdfWriter(clone_from=str(LIVE / "reader.pdf"))
    writer.insert_page(cover.pages[0], 0)
    writer.add_metadata(
        {
            "/Title": "埃米·诺特数学著作全集——完整简体中文版",
            "/Author": "Emmy Noether; Manuscript Typesetting Project; OpenAI Codex",
            "/Subject": "Complete PRC-oriented Simplified-Chinese corpus edition, version 1.0.0",
            "/Keywords": "Emmy Noether, Simplified Chinese, translation, mathematics, algebra",
        }
    )
    with output.open("wb") as stream:
        writer.write(stream)


def page_stream_hash(page) -> str:
    contents = page.get_contents()
    data = b"" if contents is None else contents.get_data()
    return hashlib.sha256(data).hexdigest().upper()


def box_tuple(page, key: str) -> tuple[float, float, float, float]:
    box = getattr(page, key)
    return tuple(round(float(value), 6) for value in (box.left, box.bottom, box.right, box.top))


def annotation_count(reader: PdfReader) -> int:
    total = 0
    for page in reader.pages:
        annotations = page.get("/Annots", [])
        if hasattr(annotations, "get_object"):
            annotations = annotations.get_object()
        total += len(annotations)
    return total


def page_annotation_counts(reader: PdfReader) -> list[int]:
    counts = []
    for page in reader.pages:
        annotations = page.get("/Annots", [])
        if hasattr(annotations, "get_object"):
            annotations = annotations.get_object()
        counts.append(len(annotations))
    return counts


def cover_uris(reader: PdfReader) -> list[str]:
    annotations = reader.pages[0].get("/Annots", [])
    if hasattr(annotations, "get_object"):
        annotations = annotations.get_object()
    values = []
    for reference in annotations:
        annotation = reference.get_object()
        action = annotation.get("/A")
        if action and action.get("/S") == "/URI":
            values.append(str(action.get("/URI")))
    return sorted(values)


def outline_count(items) -> int:
    count = 0
    for item in items:
        if isinstance(item, list):
            count += outline_count(item)
        else:
            count += 1
    return count


def extraction_gate(pdf: Path) -> dict[str, object]:
    poppler = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, check=True).stdout
    poppler_text = poppler.decode("utf-8", errors="replace")
    reader = PdfReader(str(pdf))
    pypdf_text = "\f".join(page.extract_text() or "" for page in reader.pages)

    def counts(text: str) -> dict[str, int]:
        return {
            "disallowed_c0": sum(1 for char in text if ord(char) < 32 and char not in "\n\r\t\f"),
            "replacement_characters": text.count("\ufffd"),
            "nul": text.count("\x00"),
        }

    result = {"poppler": counts(poppler_text), "pypdf": counts(pypdf_text)}
    if any(value for tool in result.values() for value in tool.values()):
        raise SystemExit(f"extraction gate failed: {result}")
    return result


def render_page(pdf: Path, page: int, stem: str) -> Path:
    out = EVIDENCE / "visual" / stem
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["pdftoppm", "-f", str(page), "-l", str(page), "-singlefile", "-png", "-r", "180", str(pdf), str(out)],
        check=True,
        capture_output=True,
    )
    return out.with_suffix(".png")


def validate(final: Path, cover_passes: list[dict[str, object]]) -> dict[str, object]:
    body = PdfReader(str(LIVE / "reader.pdf"))
    combined = PdfReader(str(final))
    if len(body.pages) != BODY_PAGES or len(combined.pages) != BODY_PAGES + 1:
        raise SystemExit("page count mismatch")

    stream_equal = 0
    geometry_equal = 0
    for index, body_page in enumerate(body.pages):
        out_page = combined.pages[index + 1]
        if page_stream_hash(body_page) == page_stream_hash(out_page):
            stream_equal += 1
        if all(box_tuple(body_page, key) == box_tuple(out_page, key) for key in ("mediabox", "cropbox")):
            geometry_equal += 1
    if stream_equal != BODY_PAGES or geometry_equal != BODY_PAGES:
        raise SystemExit("merged body changed")

    metadata = combined.metadata
    if metadata.title != "埃米·诺特数学著作全集——完整简体中文版":
        raise SystemExit("final PDF title mismatch")
    if not metadata.author or not metadata.author.startswith("Emmy Noether"):
        raise SystemExit("final PDF author mismatch")

    cover_reader = PdfReader(str(TMP / "cover.pdf"))
    cover_annotations = annotation_count(cover_reader)
    body_annotations = annotation_count(body)
    combined_annotations = annotation_count(combined)
    if combined_annotations != cover_annotations + body_annotations:
        raise SystemExit("annotation count mismatch after merge")
    body_annotation_counts = page_annotation_counts(body)
    merged_body_annotation_counts = page_annotation_counts(combined)[1:]
    if body_annotation_counts != merged_body_annotation_counts:
        raise SystemExit("pagewise body annotation counts changed after merge")
    expected_uris = sorted(
        [
            "https://doi.org/10.5281/zenodo.21933034",
            "https://doi.org/10.5281/zenodo.21933035",
            "https://doi.org/10.5281/zenodo.20412587",
            "https://github.com/KokunoYumeto/emmy-noether-zh-hans",
        ]
    )
    actual_uris = cover_uris(combined)
    if actual_uris != expected_uris:
        raise SystemExit(f"cover URI mismatch: {actual_uris}")

    body_destinations = body.named_destinations
    combined_destinations = combined.named_destinations
    if set(body_destinations) != set(combined_destinations):
        raise SystemExit("named destination set changed after merge")
    shifted_destinations = 0
    for name, destination in body_destinations.items():
        before = body.get_destination_page_number(destination)
        after = combined.get_destination_page_number(combined_destinations[name])
        if after == before + 1:
            shifted_destinations += 1
    if shifted_destinations != len(body_destinations):
        raise SystemExit("not all named destinations shifted by exactly one cover page")

    extraction = extraction_gate(final)
    renders = [
        render_page(final, 1, "cover"),
        render_page(final, 2, "body-first"),
        render_page(final, BODY_PAGES + 1, "body-last"),
    ]
    return {
        "schema": "zh-noether-publication-build/1",
        "source_date_epoch": int(SOURCE_DATE_EPOCH),
        "python": subprocess.run(["python", "--version"], capture_output=True, text=True, check=True).stdout.strip(),
        "pypdf": __import__("pypdf").__version__,
        "xelatex": subprocess.run(["xelatex", "--version"], capture_output=True, text=True, check=True).stdout.splitlines()[0],
        "cover_passes": cover_passes,
        "body": {"bytes": BODY_PDF_BYTES, "sha256": BODY_PDF_SHA, "pages": BODY_PAGES},
        "reader": {"path": final.relative_to(REPO).as_posix(), "bytes": final.stat().st_size, "sha256": sha(final), "pages": len(combined.pages)},
        "body_content_streams_equal": f"{stream_equal}/{BODY_PAGES}",
        "body_mediabox_cropbox_equal": f"{geometry_equal}/{BODY_PAGES}",
        "annotations": {"cover": cover_annotations, "body": body_annotations, "reader": combined_annotations},
        "body_annotation_page_counts_equal": f"{BODY_PAGES}/{BODY_PAGES}",
        "cover_uris": actual_uris,
        "named_destinations": {"body": len(body_destinations), "reader": len(combined_destinations), "shifted_by_one_page": shifted_destinations},
        "outlines": {"body": outline_count(body.outline), "reader": outline_count(combined.outline)},
        "metadata": {"title": metadata.title, "author": metadata.author, "subject": metadata.subject},
        "extraction": extraction,
        "rendered_pages": [
            {"page": page, "path": path.relative_to(REPO).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)}
            for page, path in zip((1, 2, BODY_PAGES + 1), renders)
        ],
    }


def main() -> None:
    clean_tmp()
    prepare_sources()
    cover_passes = run_cover_build()
    one = TMP / "reader-one.pdf"
    two = TMP / "reader-two.pdf"
    merge(one)
    merge(two)
    if one.read_bytes() != two.read_bytes():
        raise SystemExit("two publication-reader merges are not byte-identical")
    READER.mkdir(parents=True, exist_ok=True)
    final = READER / "00_NOETHER_zh-Hans_COMPLETE_READER.pdf"
    shutil.copyfile(one, final)
    receipt = validate(final, cover_passes)
    receipt["two_merge_runs_byte_identical"] = True
    receipt["merge_run_sha256"] = sha(one)
    path = EVIDENCE / "build.json"
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(receipt, ensure_ascii=True))


if __name__ == "__main__":
    main()
