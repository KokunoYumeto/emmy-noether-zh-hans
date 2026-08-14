from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BASE = ROOT / "base.tex"
TARGET = ROOT / "reader.tex"
STATE = ROOT / "STATE.md"
CAND = ROOT / "src/cand.tex"
CHECKER = ROOT / "src/chk.json"
DELTA = ROOT / "delta.json"
QA = ROOT / "qa.json"

PINS = {
    "base.tex": (1_874_053, "14240969926ED46CCD1D9F75BA7EA8A25652B28FF27F436030F46D74DCFBA00E"),
    "reader.tex": (1_874_083, "553446A494A59530946AB70EC2F672BED4D45A33B7FA554765A11B8C038DA6D4"),
    "src/cand.tex": (1_874_053, "0CF0CDB22E66E00D01282BDAA33E5FEB65EDDE7DE2FE5000A1628D61F116F497"),
    "src/chk.json": (6_649, "4338E7695E92731F265CCDF523AD0A2B309EC7047922164072318C544E4E1323"),
    "src/r10.csv": (4_581, "F8647FE279273538F2E7702FB96CB633DDFA47CC59E856FBA6F272FC447EF371"),
    "src/r10ret.json": (4_424, "1DF6EA1DAD813C6C1AE42E96B0E557287AC562C405F0D30DA985B989690E060D"),
    "src/r10frz.json": (2_380, "7A0C7EEE76597CB04761336D4D69CFF75B37715FB78A454B35056CC1F4D3F3B5"),
}

CHANGES = {
    2: (
        "% Static successor: ZH-CUM-R9; producer state FROZEN_PENDING_INDEPENDENT_REVIEW.",
        "% Static release: ZH-CUM-R10B; producer state MACHINE_VALIDATED_RELEASE_READY.",
        "release_policy_comment",
        "DIRECT-FLORIS-RELEASE-GATE-OVERRIDE-20260813",
    ),
    5: (
        "% Rejected predecessor: ZHCHK-NOETHER-CUM-R7-RETURN-REQUIRED-001; independent disposition RETURN_REQUIRED. Clean-day count: 0/3; publishable: false.",
        "% Historical R7 return ZHCHK-NOETHER-CUM-R7-RETURN-REQUIRED-001 and dated pending-review comments are provenance only; later human audit is optional and is not a publication gate.",
        "release_policy_comment",
        "DIRECT-FLORIS-RELEASE-GATE-OVERRIDE-20260813",
    ),
    25: (
        r"\hypersetup{unicode=true,hidelinks,pdfauthor={Emmy Noether},pdftitle={Noether Simplified Chinese cumulative rebase r9}}",
        r"\hypersetup{unicode=true,hidelinks,pdfauthor={Emmy Noether},pdftitle={Noether Simplified Chinese cumulative rebase r10}}",
        "pdf_metadata_title_only",
        "ZHCHK-R10-PDFMETA-001",
    ),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def ident(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(data), "sha256": sha(data)}


def main() -> None:
    if DELTA.exists() or QA.exists():
        raise SystemExit("refusing to overwrite delta.json or qa.json")
    checks: list[dict[str, object]] = []

    def check(check_id: str, passed: bool, evidence: object = None) -> None:
        row: dict[str, object] = {"id": check_id, "pass": bool(passed)}
        if evidence is not None:
            row["evidence"] = evidence
        checks.append(row)

    for rel, pin in PINS.items():
        path = ROOT / rel
        observed = (path.stat().st_size, sha(path.read_bytes())) if path.is_file() else None
        check(f"pin:{rel}", observed == pin, {"expected": pin, "observed": observed})

    base, target, candidate = BASE.read_bytes(), TARGET.read_bytes(), CAND.read_bytes()
    base_lines, target_lines = base.splitlines(keepends=True), target.splitlines(keepends=True)
    check("tex_lf_only", b"\r" not in base and b"\r" not in target)
    check("line_counts_preserved", len(base_lines) == len(target_lines) == 25_085)
    check("terminal_lfs_preserved", base.endswith(b"\n\n\n\n") and target.endswith(b"\n\n\n\n"))
    changed = [i for i, pair in enumerate(zip(base_lines, target_lines), 1) if pair[0] != pair[1]]
    check("exact_changed_lines", changed == sorted(CHANGES), changed)
    reconstructed = list(base_lines)
    records = []
    for number, (old, new, classification, authority) in CHANGES.items():
        before, after = (old + "\n").encode("utf-8"), (new + "\n").encode("utf-8")
        check(f"line_{number}_preimage", base_lines[number - 1] == before)
        check(f"line_{number}_successor", target_lines[number - 1] == after)
        reconstructed[number - 1] = after
        records.append({
            "line": number,
            "classification": classification,
            "authority": authority,
            "before": {"bytes_lf": len(before), "sha256_lf": sha(before), "text": old},
            "after": {"bytes_lf": len(after), "sha256_lf": sha(after), "text": new},
        })
    check("exact_byte_reconstruction", b"".join(reconstructed) == target)
    check("substantive_body_exact", b"".join(base_lines[25:]) == b"".join(target_lines[25:]))
    check("checker_candidate_is_line25_witness", target_lines[24] == candidate.splitlines(keepends=True)[24])
    check("checker_candidate_tail_adverse", candidate.count(b"\n") == 25_084 and target.count(b"\n") == 25_085)
    check("release_policy_present", b"MACHINE_VALIDATED_RELEASE_READY" in target_lines[1] and b"not a publication gate" in target_lines[4])

    state_text = STATE.read_text(encoding="utf-8")
    check("state_release_ready", "`MACHINE_VALIDATED_RELEASE_READY`; publishable" in state_text)
    check("state_no_human_gate", "not publication prerequisites" in state_text and "Later audit is optional" in state_text)
    check("state_claim_boundary", "not claimed to have external, community, or human certification" in state_text)

    checker = json.loads(CHECKER.read_text(encoding="utf-8"))
    finding_ids = [row.get("id") for row in checker.get("open_findings", [])]
    check("checker_return", checker.get("return_id") == "ZHCHK-NOETHER-R10-RETURN-001")
    check("checker_findings", finding_ids == ["ZHCHK-R10-PDFMETA-001", "ZHCHK-R10-STATE-001"], finding_ids)
    check("checker_no_substantive_defect", checker.get("integration", {}).get("substantive_chinese_or_math_defects") == 0)
    check("german_unchanged", checker.get("authority", {}).get("german_mutated") is False)
    check("hant_no_intake", checker.get("Hant") == "NO_INTAKE")
    check("sga_held", checker.get("SGA") == "held_untouched")

    delta = {
        "record_id": "ZH-NOETHER-CUM-R10B-DELTA-002",
        "state": "MACHINE_VALIDATED_RELEASE_READY_PENDING_REBUILD",
        "base": {**ident(BASE), "role": "frozen r10 reader.tex"},
        "output": ident(TARGET),
        "state_output": ident(STATE),
        "checker_return": {**ident(CHECKER), "id": "ZHCHK-NOETHER-R10-RETURN-001", "role": "historical correction evidence; not release authority"},
        "changed_lines": records,
        "changed_line_count": 3,
        "unchanged_line_count": 25_082,
        "candidate_tail_adverse_evidence": {
            "checker_candidate": ident(CAND),
            "fact": "checker cand.tex removes one terminal LF while adding one byte in the title",
            "resolution": "use candidate as line-25 witness only; preserve all frozen terminal LFs",
        },
        "release_policy": {
            "authority": "direct Floris instruction, 2026-08-13",
            "machine_validation_required": True,
            "human_review_required": False,
            "independent_review_required": False,
            "checker_acceptance_required": False,
            "clean_day_gate_required": False,
            "later_audit": "optional additive evidence",
        },
        "substantive_chinese_delta": False,
        "mathematical_delta": False,
        "german_mutated": False,
        "Hant": "NO_INTAKE",
        "sga": "held and untouched",
        "publication": "not yet performed",
    }
    DELTA.write_text(json.dumps(delta, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    check("delta_written", DELTA.is_file())
    result = {
        "record_id": "ZH-NOETHER-CUM-R10B-QA-002",
        "phase": "PASS_MACHINE_VALIDATED_RELEASE_READY_PENDING_REBUILD",
        "all_pass": all(row["pass"] for row in checks),
        "check_count": len(checks),
        "checks": checks,
        "base": ident(BASE),
        "target": ident(TARGET),
        "state_file": ident(STATE),
        "delta": ident(DELTA),
        "changed_line_count": 3,
        "unchanged_line_count": 25_082,
        "substantive_chinese_delta": False,
        "german_mutated": False,
        "release_policy": delta["release_policy"],
        "Hant": "NO_INTAKE",
        "sga": "held and untouched",
    }
    QA.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"checks": len(checks), "all_pass": result["all_pass"], "target": ident(TARGET), "state": ident(STATE), "delta": ident(DELTA)}))
    if not result["all_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
