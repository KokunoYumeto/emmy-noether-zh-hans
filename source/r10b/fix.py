from __future__ import annotations

import hashlib
import json
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

import pypdf
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, IndirectObject, NameObject


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw.pdf"
FINAL = ROOT / "reader.pdf"
TMP1 = ROOT / "_f1.pdf"
TMP2 = ROOT / "_f2.pdf"
OUT = ROOT / "fix.json"
MAP_DIR = ROOT / "map"
PDFFONTS = Path(r"C:\Users\Floris\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdffonts.exe")
MAP_PINS = {
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


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def ident(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(data), "sha256": digest(data)}


def deref(value: Any) -> Any:
    return value.get_object() if hasattr(value, "get_object") else value


def ref_id(value: Any) -> tuple[int | None, int | None]:
    ref = value if isinstance(value, IndirectObject) else getattr(value, "indirect_reference", None)
    return (getattr(ref, "idnum", None), getattr(ref, "generation", None))


def base_name(font: DictionaryObject) -> str:
    value = str(font.get("/BaseFont", "")).lstrip("/")
    return value.rsplit("+", 1)[-1]


def stream_identity(value: Any) -> dict[str, object] | None:
    if value is None:
        return None
    obj = deref(value)
    encoded = bytes(getattr(obj, "_data", b""))
    decoded = obj.get_data()
    return {
        "ref": list(ref_id(value)),
        "encoded_bytes": len(encoded),
        "encoded_sha256": digest(encoded),
        "decoded_bytes": len(decoded),
        "decoded_sha256": digest(decoded),
    }


def font_inventory(reader: PdfReader) -> dict[str, dict[str, object]]:
    found: dict[tuple[int | None, int | None], tuple[Any, DictionaryObject]] = {}
    pages: dict[tuple[int | None, int | None], list[int]] = defaultdict(list)
    for page_number, page in enumerate(reader.pages, 1):
        resources = deref(page.get("/Resources"))
        fonts = deref(resources.get("/Font")) if resources else None
        if not fonts:
            continue
        for value in fonts.values():
            font = deref(value)
            key = ref_id(value)
            found[key] = (value, font)
            pages[key].append(page_number)
    result: dict[str, dict[str, object]] = {}
    for key, (value, font) in sorted(found.items(), key=lambda row: (row[0][0] or -1, row[0][1] or -1)):
        name = base_name(font)
        descriptor = deref(font.get("/FontDescriptor"))
        programs = {}
        if descriptor:
            for label in ("/FontFile", "/FontFile2", "/FontFile3"):
                if label in descriptor:
                    programs[label] = stream_identity(descriptor[label])
        result[name] = {
            "ref": list(key),
            "base_font": str(font.get("/BaseFont", "")),
            "subtype": str(font.get("/Subtype", "")),
            "encoding": str(font.get("/Encoding", "")),
            "pages": pages[key],
            "font_programs": programs,
            "to_unicode": stream_identity(font.get("/ToUnicode")),
        }
    return result


def content_signature(page: Any) -> list[dict[str, object]]:
    value = page.get("/Contents")
    if value is None:
        return []
    value = deref(value)
    items = list(value) if isinstance(value, ArrayObject) else [page.get("/Contents")]
    return [stream_identity(item) for item in items]


def simple(value: Any, depth: int = 0) -> Any:
    if depth > 8:
        return "<depth>"
    if isinstance(value, IndirectObject):
        return {"ref": [value.idnum, value.generation]}
    value = deref(value)
    if isinstance(value, DictionaryObject):
        return {str(key): simple(item, depth + 1) for key, item in sorted(value.items(), key=lambda row: str(row[0])) if str(key) != "/P"}
    if isinstance(value, dict):
        return {str(key): simple(item, depth + 1) for key, item in sorted(value.items(), key=lambda row: str(row[0]))}
    if isinstance(value, (ArrayObject, list, tuple)):
        return [simple(item, depth + 1) for item in value]
    if isinstance(value, bytes):
        return {"bytes_hex": value.hex()}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def without_refs(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: without_refs(item) for key, item in value.items() if key != "ref"}
    if isinstance(value, list):
        return [without_refs(item) for item in value]
    return value


def annotation_signature(page: Any) -> list[dict[str, object]]:
    value = page.get("/Annots")
    if value is None:
        return []
    return [{"ref": list(ref_id(item)), "object": simple(deref(item))} for item in deref(value)]


def destination_signature(reader: PdfReader) -> list[dict[str, object]]:
    rows = []
    for name, destination in sorted(reader.named_destinations.items()):
        rows.append(
            {
                "name": name,
                "page": reader.get_destination_page_number(destination),
                "typ": str(getattr(destination, "typ", "")),
                "left": str(getattr(destination, "left", None)),
                "top": str(getattr(destination, "top", None)),
                "zoom": str(getattr(destination, "zoom", None)),
            }
        )
    return rows


def outline_signature(reader: PdfReader) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    def visit(items: list[Any], level: int) -> None:
        for item in items:
            if isinstance(item, list):
                visit(item, level + 1)
                continue
            rows.append(
                {
                    "level": level,
                    "title": str(getattr(item, "title", item)),
                    "page": reader.get_destination_page_number(item) if hasattr(item, "page") else None,
                }
            )

    visit(reader.outline, 0)
    return rows


def document_signature(reader: PdfReader) -> dict[str, object]:
    pages = []
    for page in reader.pages:
        pages.append(
            {
                "contents": content_signature(page),
                "boxes": {
                    "media": [str(item) for item in page.mediabox],
                    "crop": [str(item) for item in page.cropbox],
                    "bleed": [str(item) for item in page.bleedbox],
                    "trim": [str(item) for item in page.trimbox],
                    "art": [str(item) for item in page.artbox],
                    "rotation": int(page.rotation),
                },
                "annotations": annotation_signature(page),
            }
        )
    return {
        "header": reader.pdf_header,
        "trailer_id": simple(reader.trailer.get("/ID")),
        "metadata": simple(dict(reader.metadata or {})),
        "pages": pages,
        "named_destinations": destination_signature(reader),
        "outlines": outline_signature(reader),
        "fonts": font_inventory(reader),
    }


def build_fixed(destination: Path, cmap_data: dict[str, bytes]) -> list[dict[str, object]]:
    reader = PdfReader(str(RAW), strict=True)
    writer = PdfWriter(clone_from=reader)
    writer.pdf_header = reader.pdf_header
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
                raise RuntimeError(f"unrecognized missing ToUnicode font: {name}")
            cmap_name = FONT_MAP[name]
            font[NameObject("/ToUnicode")] = map_refs[cmap_name]
            injected[key] = {"font": name, "font_ref": list(key), "cmap": cmap_name, "pages": [page_number]}
    names = {row["font"] for row in injected.values()}
    if names != set(FONT_MAP) or len(injected) != 6:
        raise RuntimeError(f"missing-font allowlist mismatch: {sorted(names)}")
    with destination.open("wb") as handle:
        writer.write(handle)
    return sorted(injected.values(), key=lambda row: row["font"])


def pdffonts(path: Path, evidence: Path, expected_no: set[str]) -> dict[str, object]:
    completed = subprocess.run([str(PDFFONTS), str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    evidence.write_text(completed.stdout + completed.stderr, encoding="utf-8", newline="\n")
    if completed.returncode != 0:
        raise RuntimeError("pdffonts failed")
    rows = [line.split() for line in completed.stdout.splitlines()[2:] if line.strip()]
    missing = {row[0].rsplit("+", 1)[-1] for row in rows if len(row) >= 8 and row[-3] == "no"}
    if len(rows) != 34 or any(len(row) < 8 for row in rows) or missing != expected_no:
        raise RuntimeError("pdffonts ToUnicode gate failed")
    return {"identity": ident(evidence), "font_count": len(rows), "missing_tounicode": sorted(missing), "all_uni_yes": not missing}


def main() -> None:
    if pypdf.__version__ != "6.12.2":
        raise SystemExit(f"unexpected pypdf version: {pypdf.__version__}")
    build_path = ROOT / "build.json"
    build = json.loads(build_path.read_text(encoding="utf-8"))
    if build.get("record_id") != "ZH-NOETHER-CUM-R10B-RAW-BUILD-001" or build.get("state") != "PASS_RAW_PDF_PENDING_CMAP_FIX_AND_VISUAL_QA":
        raise SystemExit("r10b build receipt identity/state mismatch")
    raw_pin = build.get("raw_pdf", {})
    if RAW.stat().st_size != raw_pin.get("bytes") or digest(RAW.read_bytes()) != raw_pin.get("sha256"):
        raise SystemExit("raw PDF identity mismatch against build receipt")
    if any(path.exists() for path in (FINAL, TMP1, TMP2, OUT)):
        raise SystemExit("refusing to overwrite fixed output/control")
    cmap_data = {}
    cmap_records = {}
    for name, (expected_bytes, expected_sha) in MAP_PINS.items():
        path = MAP_DIR / name
        data = path.read_bytes()
        if len(data) != expected_bytes or digest(data) != expected_sha:
            raise SystemExit(f"CMap identity mismatch: {name}")
        cmap_data[name] = data
        cmap_records[name] = ident(path)

    raw_reader = PdfReader(str(RAW), strict=True)
    raw_fonts = font_inventory(raw_reader)
    missing = sorted(name for name, record in raw_fonts.items() if record["to_unicode"] is None)
    if missing != sorted(FONT_MAP) or len(raw_fonts) != 34:
        raise SystemExit(f"raw missing-font gate mismatch: {missing}")
    raw_signature = document_signature(raw_reader)
    injected1 = build_fixed(TMP1, cmap_data)
    injected2 = build_fixed(TMP2, cmap_data)
    if injected1 != injected2 or TMP1.read_bytes() != TMP2.read_bytes():
        raise SystemExit("fixed PDF is not byte-deterministic")

    fixed_reader = PdfReader(str(TMP1), strict=True)
    fixed_signature = document_signature(fixed_reader)
    raw_core = dict(raw_signature)
    fixed_core = dict(fixed_signature)
    raw_font_sig = raw_core.pop("fonts")
    fixed_font_sig = fixed_core.pop("fonts")
    if without_refs(raw_core) != without_refs(fixed_core):
        raise SystemExit("non-font PDF structure changed")
    if set(raw_font_sig) != set(fixed_font_sig):
        raise SystemExit("font set changed")
    for name in sorted(raw_font_sig):
        raw_font = dict(raw_font_sig[name])
        fixed_font = dict(fixed_font_sig[name])
        raw_font.pop("ref")
        fixed_font.pop("ref")
        raw_map = raw_font.pop("to_unicode")
        fixed_map = fixed_font.pop("to_unicode")
        if without_refs(raw_font) != without_refs(fixed_font):
            raise SystemExit(f"font program/structure changed: {name}")
        if name in FONT_MAP:
            if raw_map is not None or fixed_map is None or fixed_map["decoded_sha256"] != MAP_PINS[FONT_MAP[name]][1]:
                raise SystemExit(f"new ToUnicode mismatch: {name}")
        elif without_refs(raw_map) != without_refs(fixed_map):
            raise SystemExit(f"existing ToUnicode changed: {name}")

    first_identity = ident(TMP1)
    second_identity = ident(TMP2)
    TMP1.replace(FINAL)
    TMP2.unlink()
    raw_fonts_record = pdffonts(RAW, ROOT / "rawfonts.txt", set(FONT_MAP))
    final_fonts_record = pdffonts(FINAL, ROOT / "fonts.txt", set())
    result = {
        "record_id": "ZH-NOETHER-CUM-R10B-CMAP-FIX-001",
        "state": "PASS_PENDING_DUAL_EXTRACTION_AND_VISUAL_QA",
        "method": "pypdf 6.12.2 missing-only deterministic ToUnicode CMap injection",
        "receipt": {"path": "src/ext.json", "bytes": 3_144, "sha256": "7EC290D5DA0054625EAB7F3CC0E9753A1674E782B6B78330DA4C262F528372AE"},
        "build": ident(build_path),
        "raw_pdf": ident(RAW),
        "fixed_pdf": ident(FINAL),
        "determinism": {"first": first_identity, "second": second_identity, "byte_identical": True},
        "cmaps": cmap_records,
        "injected_fonts": injected1,
        "invariants": {
            "page_count": len(raw_reader.pages),
            "page_content_streams": "exact",
            "font_programs": "exact",
            "page_boxes_and_rotation": "exact",
            "annotations": sum(len(row["annotations"]) for row in raw_signature["pages"]),
            "named_destinations": len(raw_signature["named_destinations"]),
            "outlines": len(raw_signature["outlines"]),
            "metadata": "exact",
            "trailer_id": "exact",
            "pdf_header": raw_reader.pdf_header,
            "all_pass": True,
        },
        "pdffonts": {"raw": raw_fonts_record, "fixed": final_fonts_record},
        "german_mutated": False,
        "target_text_mutated": False,
        "sga": "held and untouched",
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"fixed": ident(FINAL), "fonts": 34, "injected": 6, "invariants": True}))


if __name__ == "__main__":
    main()
