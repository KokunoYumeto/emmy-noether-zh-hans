from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parent
R7 = ROOT.parents[1] / "05_independent_checking/noether_chinese/cum_r7"
OUT = ROOT / "extract.json"
PDFTOTEXT = Path(r"C:\Users\Floris\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdftotext.exe")


def ident(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest().upper()}


def internal_controls(text: str, *, poppler_page_text: bool) -> Counter[int]:
    allowed = {9, 10, 13}
    if poppler_page_text:
        # Poppler's form feeds delimit pages and are removed before this function.
        allowed.add(12)
    return Counter(ord(char) for char in text if ord(char) < 32 and ord(char) not in allowed)


def poppler_record(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    pages = text.split("\f")
    if pages and pages[-1] == "":
        pages.pop()
    page_counts: list[int] = []
    codes: Counter[int] = Counter()
    for page in pages:
        found = internal_controls(page, poppler_page_text=True)
        page_counts.append(sum(found.values()))
        codes.update(found)
    return {
        "identity": ident(path),
        "method": "pdftotext -layout -enc UTF-8; split at page-separator FF; disallowed internal C0 excludes TAB/LF/CR and the removed page separators",
        "pages": len(pages),
        "disallowed_internal_c0": sum(codes.values()),
        "affected_pages": sum(value > 0 for value in page_counts),
        "affected_page_numbers": [index for index, value in enumerate(page_counts, 1) if value],
        "code_counts": {f"U+{code:04X}": count for code, count in sorted(codes.items())},
        "replacement_characters": text.count("\ufffd"),
    }


def pypdf_record(path: Path) -> dict[str, object]:
    reader = PdfReader(str(path))
    page_counts: list[int] = []
    codes: Counter[int] = Counter()
    replacement = 0
    for page in reader.pages:
        text = page.extract_text() or ""
        found = internal_controls(text, poppler_page_text=False)
        page_counts.append(sum(found.values()))
        codes.update(found)
        replacement += text.count("\ufffd")
    return {
        "identity": ident(path),
        "method": "pypdf page.extract_text; disallowed internal C0 excludes TAB/LF/CR and includes any extracted FF",
        "pages": len(reader.pages),
        "disallowed_internal_c0": sum(codes.values()),
        "affected_pages": sum(value > 0 for value in page_counts),
        "affected_page_numbers": [index for index, value in enumerate(page_counts, 1) if value],
        "code_counts": {f"U+{code:04X}": count for code, count in sorted(codes.items())},
        "replacement_characters": replacement,
    }


def main() -> None:
    final_pdf = ROOT / "reader.pdf"
    final_txt = ROOT / "reader.txt"
    if OUT.exists() or final_txt.exists():
        raise SystemExit("refusing to overwrite extract.json or reader.txt")
    if not PDFTOTEXT.is_file():
        raise SystemExit("pdftotext unavailable")
    completed = subprocess.run(
        [str(PDFTOTEXT), "-layout", "-enc", "UTF-8", str(final_pdf), str(final_txt)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0 or not final_txt.is_file():
        raise SystemExit("pdftotext failed")
    r7_pdf = R7 / "reader.pdf"
    r7_txt = R7 / "reader.txt"
    if ident(r7_pdf)["sha256"] != "CCA7A94C795027378FB370D7E78977DEFA252CFA5115AD915B164013055369D4":
        raise SystemExit("r7 PDF identity mismatch")
    baseline_poppler = poppler_record(r7_txt)
    baseline_pypdf = pypdf_record(r7_pdf)
    if (
        baseline_poppler["disallowed_internal_c0"] != 559
        or baseline_poppler["affected_pages"] != 100
        or baseline_pypdf["disallowed_internal_c0"] != 11_488
        or baseline_pypdf["affected_pages"] != 388
    ):
        raise SystemExit("CJK-NOETH-EXT-SYS-001 baseline replay mismatch")

    final_poppler = poppler_record(final_txt)
    final_pypdf = pypdf_record(final_pdf)
    gate_closed = bool(
        final_poppler["disallowed_internal_c0"] == 0
        and final_pypdf["disallowed_internal_c0"] == 0
        and final_poppler["replacement_characters"] == 0
        and final_pypdf["replacement_characters"] == 0
    )
    result = {
        "record_id": "ZH-NOETHER-CUM-R10B-EXTRACT-001",
        "finding_id": "CJK-NOETH-EXT-SYS-001",
        "receipt": {
            "csv": {"path": "src/ext.csv", "bytes": 1_091, "sha256": "2F3738E2AABD7B585D474F8767F112E3D9D23AAECF2B8D66D85551F18FF00F31"},
            "md": {"path": "src/ext.md", "bytes": 3_074, "sha256": "6A48E98B660A308E164DDE821093AE640ED5F95AE466E9D39E8ED96472792887"},
        },
        "baseline_r7": {"poppler": baseline_poppler, "pypdf": baseline_pypdf, "replay_exact": True},
        "r10b": {"poppler": final_poppler, "pypdf": final_pypdf},
        "poppler_command": ["pdftotext", "-layout", "-enc", "UTF-8", "reader.pdf", "reader.txt"],
        "build_gate": "CLOSED_ZERO_DISALLOWED_C0" if gate_closed else "OPEN_CJK-NOETH-EXT-SYS-001",
        "unconditional_extraction_clean_claim": gate_closed,
        "all_pass": gate_closed,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"r10b_poppler": final_poppler["disallowed_internal_c0"], "r10b_pypdf": final_pypdf["disallowed_internal_c0"], "gate": result["build_gate"]}))
    if not gate_closed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
