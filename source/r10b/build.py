from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parent
TEX = ROOT / "reader.tex"
QA = ROOT / "qa.json"
WORK = ROOT.parent / "zh_r10b_w"
BUILD = WORK / "b"
LOG = ROOT / "log"
RAW = ROOT / "raw.pdf"
OUT = ROOT / "build.json"
XELATEX = Path(r"C:\Users\Floris\AppData\Local\Programs\MiKTeX\miktex\bin\x64\xelatex.exe")
TEX_SHA = "553446A494A59530946AB70EC2F672BED4D45A33B7FA554765A11B8C038DA6D4"
SOURCE_DATE_EPOCH = "1786053600"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def ident(path: Path, shown: str | None = None) -> dict[str, object]:
    return {"path": shown or path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)}


def main() -> None:
    if TEX.stat().st_size != 1_874_083 or sha(TEX) != TEX_SHA:
        raise SystemExit("reader.tex identity mismatch")
    qa = json.loads(QA.read_text(encoding="utf-8"))
    if not qa.get("all_pass") or qa.get("record_id") != "ZH-NOETHER-CUM-R10B-QA-002" or qa.get("target", {}).get("sha256") != TEX_SHA:
        raise SystemExit("qa.json identity/state mismatch")
    if not XELATEX.is_file():
        raise SystemExit("xelatex not found")
    if WORK.exists() or LOG.exists() or RAW.exists() or OUT.exists():
        raise SystemExit("refusing to overwrite scratch, log, raw PDF, or build receipt")
    BUILD.mkdir(parents=True)
    LOG.mkdir()

    env = dict(os.environ)
    env["SOURCE_DATE_EPOCH"] = SOURCE_DATE_EPOCH
    env["FORCE_SOURCE_DATE"] = "1"
    command = [
        str(XELATEX),
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        "-no-shell-escape",
        "-jobname=r10b",
        f"-output-directory={BUILD}",
        str(TEX),
    ]
    passes: list[dict[str, object]] = []
    for number in (1, 2, 3):
        completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=False)
        stdout_path = LOG / f"p{number}.txt"
        stdout_path.write_bytes(completed.stdout + completed.stderr)
        live_log = BUILD / "r10b.log"
        pass_log = LOG / f"p{number}.log"
        if live_log.exists():
            shutil.copyfile(live_log, pass_log)
        log_text = pass_log.read_text(encoding="utf-8", errors="replace") if pass_log.exists() else ""
        pdf = BUILD / "r10b.pdf"
        record = {
            "pass": number,
            "exit_code": completed.returncode,
            "stdout": ident(stdout_path),
            "log": ident(pass_log) if pass_log.exists() else None,
            "pdf": ident(pdf, f"scratch/b/r10b-pass{number}.pdf") if pdf.exists() else None,
            "signals": {
                "fatal": log_text.count("Fatal error") + log_text.count("Emergency stop"),
                "overfull": log_text.count("Overfull \\hbox") + log_text.count("Overfull \\vbox"),
                "underfull": log_text.count("Underfull \\hbox") + log_text.count("Underfull \\vbox"),
                "missing_character": log_text.count("Missing character:"),
            },
        }
        passes.append(record)
        if completed.returncode != 0 or not pdf.is_file():
            raise SystemExit(f"XeLaTeX pass {number} failed")
        if number == 2:
            shutil.copyfile(pdf, BUILD / "p2.pdf")
            for suffix in ("aux", "out", "toc"):
                live = BUILD / f"r10b.{suffix}"
                if live.exists():
                    shutil.copyfile(live, BUILD / f"p2.{suffix}")
    shutil.copyfile(BUILD / "r10b.pdf", RAW)

    pass2_controls_equal = {}
    for suffix in ("aux", "out", "toc"):
        second = BUILD / f"p2.{suffix}"
        third = BUILD / f"r10b.{suffix}"
        if second.exists() or third.exists():
            pass2_controls_equal[suffix] = second.exists() and third.exists() and second.read_bytes() == third.read_bytes()
    if not all(pass2_controls_equal.values()):
        raise SystemExit("pass-2/pass-3 control files did not stabilize")
    final_log = (LOG / "p3.log").read_text(encoding="utf-8", errors="replace")
    if "Fatal error" in final_log or "Emergency stop" in final_log or "Missing character:" in final_log:
        raise SystemExit("fatal or missing-character signal in final log")
    page_count = len(PdfReader(str(RAW), strict=True).pages)
    result = {
        "record_id": "ZH-NOETHER-CUM-R10B-RAW-BUILD-001",
        "state": "PASS_RAW_PDF_PENDING_CMAP_FIX_AND_VISUAL_QA",
        "source_date_epoch": int(SOURCE_DATE_EPOCH),
        "command": [item.replace(str(BUILD), "<SCRATCH>/b").replace(str(ROOT), "<ROOT>") for item in command],
        "scratch": "../zh_r10b_w/b; excluded from static successor",
        "serial": True,
        "passes": passes,
        "pass2_controls_equal_pass3": pass2_controls_equal,
        "input": ident(TEX),
        "qa": ident(QA),
        "raw_pdf": {**ident(RAW), "pages": page_count},
        "final_log_signals": passes[-1]["signals"],
        "german_mutated": False,
        "sga": "held and untouched",
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"pages": page_count, "raw_bytes": RAW.stat().st_size, "raw_sha256": sha(RAW), "passes": 3}))


if __name__ == "__main__":
    main()
