from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[4]
MANIFEST = ROOT / "manifest.csv"
REPARSE_POINT = 0x400
FORBIDDEN_DIRS = {"b", "img", "sheet", "chg", "r36", "f36", "r10_120", "r10b_120", "__pycache__"}
POLICY_PATH = WORKSPACE / "03_projects/language_management/cjk/00_lane_control/RELEASE_GATE_OVERRIDE_20260813.md"

LOCAL_PINS = {
    "base.tex": (1_874_053, "14240969926ED46CCD1D9F75BA7EA8A25652B28FF27F436030F46D74DCFBA00E"),
    "reader.tex": (1_874_083, "553446A494A59530946AB70EC2F672BED4D45A33B7FA554765A11B8C038DA6D4"),
    "raw.pdf": (2_549_851, "83940446386BA3A008F1D65C964E0923A4E60B511E165EAB651A5FB02433F1AD"),
    "reader.pdf": (3_129_044, "0C457AB0C5F31BE1F6C8B5A4EC7ACB657ABE67979D5E9339BA493B599BC2D544"),
    "reader.txt": (1_896_159, "9A50D8B3FDD0F410812ED295A29D5D9736E38A7BACC2A242E109941D0B444143"),
    "STATE.md": (2_368, "B0FC9A8DA681863FAE6F1AF01FACE4F7DB7EC5518AA468356C350640D929BCAC"),
    "delta.json": (3_942, "AD7C82F6EE4EAF73A8C77A920042D559C1EC11D76D3C5091300DFA6A9394D845"),
    "qa.json": (5_501, "3C5A23D05FB603CF72721BF6279E2D9417E6CCDBC9B56E68E8D7742FBAA2FE81"),
    "build.json": (3_508, "149913288328915FD491C9D2B99AEBC0ACC91E5C3E23DCAE0422BD3D6B710184"),
    "fix.json": (16_219, "E790AC17D21E98B9042360CE8606C7EA3FB72D16AEFF75F7B5F11FC51052A831"),
    "extract.json": (10_115, "8137C4489F41A80F8F67B43EDE64F407B98D8F6D2AC5940CF5E8C09B1B6D2068"),
    "render.json": (124_487, "1F3E3E8E11BDB5AA209063D74382D91CA60837F1DB16A7B024C25144D015EE42"),
    "compare.json": (338_293, "69013DEAB77E89347821AA3EC5B38976B2E90D0303426BC3C566605458A353DA"),
    "visual.json": (2_545, "AAD726DFC00399B1079DAC5ACD1F54DE0A4BC5FD2B2DDC62B45B13E4273F0F85"),
    "return.json": (4_853, "3BE177A771301A02EDD2CF05FDAEC190D55867B50EA963D6152570D49AC17BB6"),
    "handoff.md": (1_727, "D1029FB5902E12F18E422062026E4B2125085B2E3E1E31D6AE72F532DB7D07FB"),
    "agents.jsonl": (2_035, "17A9C1899EA0C58472F112E052934B1CEA7D68DA667FA4BE1044947AF933828A"),
    "events.jsonl": (4_552, "0CED422BB110C16A6A38617047B47909E4323AD3FCB90592B6B1B3C65AC52825"),
    "build.py": (5_394, "B97E177263897A417986B76A1336778673AF81E09F04171D7B152FD7D309E3B2"),
    "compare.py": (7_545, "8E5B0B84F5C57CD032997239C88FF6F9BF233B562F565B2B0712E30CB13487B8"),
    "fix.py": (15_103, "06476D0B8EA2670F7C3CC4D7C8EBC2163AF356916F5A71DAE6230342637EB518"),
    "fonts.txt": (3_389, "47019FAEB73FAA9819E8CEEB9BF738F1B9C21B4F3C42753353A73928396CCF31"),
    "fonts/NotoSansCJKsc-Bold.otf": (17_002_248, "B5F0D1A190A7F9B43C310A8850630AF12553DF32C4C050543F9059732D9B4C0A"),
    "fonts/NotoSansCJKsc-Regular.otf": (16_437_364, "2C76254F6FC379FDDFCE0A7E84FB5385BB135D3E399294F6EEB6680D0365B74B"),
    "fonts/NotoSansMono-Bold.ttf": (525_664, "BEB857BD799A114DE7D5D90CC75CC69F4B6EE8D401F4AB20697E6F9719A66DFC"),
    "fonts/NotoSansMono-Regular.ttf": (512_836, "D9E2B23D19F8230BE7146F409A52B1D23117E635E28F2E2892CF91B7382F325B"),
    "fonts/NotoSerifCJKsc-Bold.otf": (25_521_460, "8AF07D4B6C2E82BCC72A30E066EAF295F11B9424F4AAD2EAA9FE0E9C3B38FC73"),
    "fonts/NotoSerifCJKsc-Regular.otf": (24_543_080, "2A2EAE2628DF83556C54018C41E20FA532C1B862C5256AE8B3F23FEB918D12CA"),
    "log/p1.log": (55_449, "832D2B71BBA6E56B5E8BA169F18938C2A96802EA0FF3038F1A48C448570D73D2"),
    "log/p1.txt": (13_647, "D1CD5F0C6A13E5994EC63579FAD98F714830F329D08C493F1D1D3CA18ABB8FA7"),
    "log/p2.log": (52_510, "B8AA0F6FA9FE97A38FBE97EDF1DECB042C92F304A33EEFFC2A581673600CD342"),
    "log/p2.txt": (10_621, "0D9987C19657F37983ADA2B3240DE7415D1098D6F28CF23990C5A027E6FFA84A"),
    "log/p3.log": (52_510, "B8AA0F6FA9FE97A38FBE97EDF1DECB042C92F304A33EEFFC2A581673600CD342"),
    "log/p3.txt": (10_621, "0D9987C19657F37983ADA2B3240DE7415D1098D6F28CF23990C5A027E6FFA84A"),
    "map/oms.cmap": (2_370, "B0EA8E71B5D2E1DC86991867AF6B9547BE1BCC20EC7561D7C3BEDFA84204A999"),
    "map/omx.cmap": (3_001, "C07DF4892D287A36825A0611A1E2BE0C9F120260F632E00E17D4E8C5973331F8"),
    "map/umsb.cmap": (2_450, "22266C6FAA697A7266CF244EFF2A64037FF762F90B5AD123D8744054D2B02F82"),
    "prep.py": (8_632, "28C97E0AD8997256A127C8ED4687FDB1B6631B27B407673734573C868074ABB1"),
    "rawfonts.txt": (3_389, "A7E8823962E118A6EA1F051E8182645B56CB05965E4AF56324004108E9410D81"),
    "render.py": (3_592, "BD3C96101FA74B256798562F640142372E3EDFAC11B266ACF85764DC0B737622"),
    "scan.py": (5_792, "3687166CB003013B4836B7B45807A83F981AC345549411D8C066456B8328D38B"),
    "seal.py": (2_446, "739B1D174033942CF37D96630B8050A7F7EE7673B73EC8DC84B1C8BE088B8AF5"),
    "src/ext.csv": (1_091, "2F3738E2AABD7B585D474F8767F112E3D9D23AAECF2B8D66D85551F18FF00F31"),
    "src/ext.json": (3_144, "7EC290D5DA0054625EAB7F3CC0E9753A1674E782B6B78330DA4C262F528372AE"),
    "src/ext.md": (3_074, "6A48E98B660A308E164DDE821093AE640ED5F95AE466E9D39E8ED96472792887"),
    "src/cand.tex": (1_874_053, "0CF0CDB22E66E00D01282BDAA33E5FEB65EDDE7DE2FE5000A1628D61F116F497"),
    "src/state0.md": (2_405, "C92399F4A9F73627239176ABBB0BD49146595E64D7F3625F7A15C7A970EE8066"),
    "src/chk.json": (6_649, "4338E7695E92731F265CCDF523AD0A2B309EC7047922164072318C544E4E1323"),
    "src/chk.csv": (182, "174A07464A344A1240C654E3A393643E263DDE079DB335344A714E6CAED6185D"),
    "src/chkv1.json": (354, "05306EB89417404205688CC8A8B181137971C31A8C434304C4AC3D037C89271F"),
    "src/chkv2.json": (464, "CA53579988EC6C4B5A35B18C91FB8EA8C954DA574FF3AEED7F6EB3D79C432F36"),
    "src/find.csv": (797, "74B36CC24D722708C4C06134BA204813D36EBEBEAA8138504B4819AC719E78EF"),
    "src/r10.csv": (4_581, "F8647FE279273538F2E7702FB96CB633DDFA47CC59E856FBA6F272FC447EF371"),
    "src/r10ret.json": (4_424, "1DF6EA1DAD813C6C1AE42E96B0E557287AC562C405F0D30DA985B989690E060D"),
    "src/r10frz.json": (2_380, "7A0C7EEE76597CB04761336D4D69CFF75B37715FB78A454B35056CC1F4D3F3B5"),
    "src/ptr.json": (132_270, "0053EA0B7E44DDE7EA7DC285ABC115DFC43F4A74B34C54DE8F39DE4E445D5BEA"),
    "src/v051.json": (152_755, "2B36556DCF123F19281AB6BF36CE6E46BEE8ADDBF37DA682032372306564D0DE"),
}

EXTERNAL_PINS = {
    "frozen_r10_tex": (ROOT.parent / "zh_r10/reader.tex", 1_874_053, LOCAL_PINS["base.tex"][1]),
    "frozen_r10_pdf": (ROOT.parent / "zh_r10/reader.pdf", 3_129_035, "41FE49CAA081E5A22A4F8E3CEACFA046BD14E799EE806D9661AC8C4F9CE2E1CE"),
    "frozen_r10_manifest": (ROOT.parent / "zh_r10/manifest.csv", 4_581, LOCAL_PINS["src/r10.csv"][1]),
    "r10_checker_return": (WORKSPACE / "03_projects/language_management/cjk/05_independent_checking/noether_chinese/r10/ret/receipt.json", 6_649, LOCAL_PINS["src/chk.json"][1]),
    "release_override": (POLICY_PATH, 1_152, "8B07A31E2BE62859F3593488EB664743A02D5D7F218E371529CBE6CB0BB7C0A9"),
    "immutable_v047": (WORKSPACE / "03_projects/noether/07_german_canon_control/pointers/v047.json", 132_270, LOCAL_PINS["src/ptr.json"][1]),
    "immutable_v051": (WORKSPACE / "03_projects/noether/07_german_canon_control/pointers/v051.json", 152_755, LOCAL_PINS["src/v051.json"][1]),
    "ED0011": (WORKSPACE / "03_projects/noether/07_german_canon_control/candidates/ED0011/noether.tex", 2_153_594, "9E6BF2BC3155ECE3DF98CD8A408C23662BEFB047A1DDF200CA1DC8476A488BF3"),
}

LINE2 = b"% Static release: ZH-CUM-R10B; producer state MACHINE_VALIDATED_RELEASE_READY.\n"
LINE5 = b"% Historical R7 return ZHCHK-NOETHER-CUM-R7-RETURN-REQUIRED-001 and dated pending-review comments are provenance only; later human audit is optional and is not a publication gate.\n"
TITLE_NEW = b"\\hypersetup{unicode=true,hidelinks,pdfauthor={Emmy Noether},pdftitle={Noether Simplified Chinese cumulative rebase r10}}\n"


def digest(path: Path) -> tuple[int, str]:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            hasher.update(chunk)
    return path.stat().st_size, hasher.hexdigest().upper()


def is_reparse(path: Path) -> bool:
    stat = path.lstat()
    return path.is_symlink() or bool(getattr(stat, "st_file_attributes", 0) & REPARSE_POINT)


def safe_relative(text: str) -> bool:
    pure = PurePosixPath(text)
    return bool(text and "\\" not in text and ":" not in text and not pure.is_absolute() and all(part not in ("", ".", "..") for part in pure.parts))


def load(relative: str) -> object:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def identity(path: Path) -> dict[str, object]:
    size, sha256 = digest(path)
    return {"bytes": size, "sha256": sha256}


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only verifier for frozen Chinese Noether r10b")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    checks: list[dict[str, object]] = []

    def check(name: str, passed: bool, evidence: object = None) -> None:
        row: dict[str, object] = {"id": name, "pass": bool(passed)}
        if evidence is not None:
            row["evidence"] = evidence
        checks.append(row)

    rows: list[tuple[str, int, str]] = []
    check("manifest_exists", MANIFEST.is_file())
    if MANIFEST.is_file():
        with MANIFEST.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            check("manifest_header", next(reader, None) == ["path", "bytes", "sha256"])
            for row in reader:
                if len(row) == 3:
                    rows.append((row[0], int(row[1]), row[2].upper()))
    names = [row[0] for row in rows]
    check("manifest_nonempty", bool(rows))
    check("manifest_sorted", names == sorted(names))
    check("manifest_paths_safe", all(safe_relative(name) for name in names))
    check("manifest_unique", len(names) == len(set(names)) == len({name.casefold() for name in names}))
    check("manifest_excludes_self", "manifest.csv" not in names)
    check("manifest_hash_shapes", all(len(value) == 64 and all(char in "0123456789ABCDEF" for char in value) for _, _, value in rows))

    actual, reparse = [], []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT).as_posix()
        if is_reparse(path):
            reparse.append(relative)
        if path.is_file() and relative != "manifest.csv":
            actual.append(relative)
    actual.sort()
    check("member_set_exact", actual == names, {"actual": len(actual), "listed": len(names)})
    check("no_reparse", not reparse, reparse)
    check("no_forbidden_dirs", not [name for name in FORBIDDEN_DIRS if (ROOT / name).exists()])
    failures = [relative for relative, expected_bytes, expected_sha in rows if not (ROOT / PurePosixPath(relative)).is_file() or digest(ROOT / PurePosixPath(relative)) != (expected_bytes, expected_sha)]
    check("manifest_replay", not failures, failures)

    local_results = {}
    for relative, expected in LOCAL_PINS.items():
        observed = identity(ROOT / relative) if (ROOT / relative).is_file() else {"missing": True}
        local_results[relative] = observed
        check(f"local:{relative}", observed == {"bytes": expected[0], "sha256": expected[1]}, observed)
    external_results = {}
    for label, (path, expected_bytes, expected_sha) in EXTERNAL_PINS.items():
        observed = identity(path) if path.is_file() else {"missing": True}
        external_results[label] = {"path": str(path), **observed}
        check(f"external:{label}", observed == {"bytes": expected_bytes, "sha256": expected_sha}, external_results[label])

    parse_failures = []
    for path in sorted(ROOT.rglob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            parse_failures.append(f"{path.relative_to(ROOT)}: {exc}")
    jsonl_counts = {}
    for path in sorted(ROOT.rglob("*.jsonl")):
        count = 0
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                count += 1
                try:
                    json.loads(line)
                except Exception as exc:
                    parse_failures.append(f"{path.relative_to(ROOT)}:{number}: {exc}")
        jsonl_counts[path.name] = count
    check("json_jsonl_parse", not parse_failures, parse_failures)
    check("agent_event_counts", jsonl_counts == {"agents.jsonl": 3, "events.jsonl": 8}, jsonl_counts)

    base = (ROOT / "base.tex").read_bytes()
    target = (ROOT / "reader.tex").read_bytes()
    candidate = (ROOT / "src/cand.tex").read_bytes()
    base_lines = base.splitlines(keepends=True)
    target_lines = target.splitlines(keepends=True)
    check("tex_line_counts", len(base_lines) == len(target_lines) == 25_085)
    check("tex_lf_only", b"\r" not in base and b"\r" not in target)
    check("tex_tail_preserved", base.endswith(b"\n\n\n\n") and target.endswith(b"\n\n\n\n"))
    changed = [index for index, pair in enumerate(zip(base_lines, target_lines), 1) if pair[0] != pair[1]]
    check("exact_three_line_replay", changed == [2, 5, 25], changed)
    check("control_lines_exact", target_lines[1] == LINE2 and target_lines[4] == LINE5 and target_lines[24] == TITLE_NEW)
    reconstructed = list(base_lines)
    reconstructed[1], reconstructed[4], reconstructed[24] = LINE2, LINE5, TITLE_NEW
    check("exact_byte_reconstruction", b"".join(reconstructed) == target)
    check("checker_candidate_tail_disclosed", candidate.count(b"\n") == 25_084 and candidate.splitlines(keepends=True)[24] == TITLE_NEW and target.endswith(b"\n\n\n\n"))
    check("substantive_body_exact", b"".join(base_lines[25:]) == b"".join(target_lines[25:]))

    delta = load("delta.json")
    check("delta_id_state", delta.get("record_id") == "ZH-NOETHER-CUM-R10B-DELTA-002" and delta.get("state") == "MACHINE_VALIDATED_RELEASE_READY")
    check("delta_scope", delta.get("changed_line_count") == 3 and delta.get("unchanged_line_count") == 25_082 and delta.get("substantive_chinese_delta") is False and delta.get("mathematical_delta") is False and delta.get("german_mutated") is False)
    check("delta_policy", delta.get("release_policy", {}).get("human_review_required") is False and delta.get("release_policy", {}).get("independent_review_required") is False and delta.get("release_policy", {}).get("checker_acceptance_required") is False and delta.get("release_policy", {}).get("clean_day_gate_required") is False)
    qa = load("qa.json")
    check("qa_pass", qa.get("record_id") == "ZH-NOETHER-CUM-R10B-QA-002" and qa.get("phase") == "PASS_MACHINE_VALIDATED_RELEASE_READY" and qa.get("all_pass") is True and qa.get("check_count") == 32)
    check("qa_rows", len(qa.get("checks", [])) == 32 and all(row.get("pass") for row in qa.get("checks", [])))
    check("qa_delta_identity", qa.get("delta") == {"bytes": LOCAL_PINS["delta.json"][0], "path": "delta.json", "sha256": LOCAL_PINS["delta.json"][1]})

    build = load("build.json")
    passes = build.get("passes", [])
    check("build_serial_three", build.get("serial") is True and len(passes) == 3 and all(row.get("exit_code") == 0 for row in passes))
    check("build_stable", len(passes) == 3 and passes[1]["pdf"].get("bytes") == passes[2]["pdf"].get("bytes") and passes[1]["pdf"].get("sha256") == passes[2]["pdf"].get("sha256") and passes[1]["log"].get("bytes") == passes[2]["log"].get("bytes") and passes[1]["log"].get("sha256") == passes[2]["log"].get("sha256"))
    check("build_controls_stable", build.get("pass2_controls_equal_pass3") == {"aux": True, "out": True})
    check("build_signals_pages", all(value == 0 for value in build.get("final_log_signals", {}).values()) and build.get("raw_pdf", {}).get("pages") == 424)
    check("build_lineage", build.get("qa", {}).get("current_postbuild_sha256") == LOCAL_PINS["qa.json"][1])

    fix = load("fix.json")
    expected_fonts = {"CMEX10": 224, "CMEX7": 2, "CMEX8": 43, "CMSY10": 385, "CMSY8": 299, "MSBM10": 24}
    observed_fonts = {row["font"]: len(row.get("pages", [])) for row in fix.get("injected_fonts", [])}
    check("fix_fonts", observed_fonts == expected_fonts, observed_fonts)
    check("fix_invariants", fix.get("invariants", {}).get("all_pass") is True and fix.get("invariants", {}).get("page_count") == 424 and fix.get("invariants", {}).get("annotations") == 760 and fix.get("invariants", {}).get("named_destinations") == 2102 and fix.get("invariants", {}).get("outlines") == 6)
    check("fix_tounicode_determinism", fix.get("pdffonts", {}).get("fixed", {}).get("font_count") == 34 and fix.get("pdffonts", {}).get("fixed", {}).get("all_uni_yes") is True and fix.get("determinism", {}).get("byte_identical") is True)
    check("fix_scope_lineage", fix.get("target_text_mutated") is False and fix.get("german_mutated") is False and fix.get("build", {}).get("current_postbuild_sha256") == LOCAL_PINS["build.json"][1])

    extract = load("extract.json")
    check("extract_gate", extract.get("all_pass") is True and extract.get("build_gate") == "CLOSED_ZERO_DISALLOWED_C0")
    for engine in ("poppler", "pypdf"):
        row = extract.get("r10b", {}).get(engine, {})
        check(f"extract_{engine}", row.get("pages") == 424 and row.get("disallowed_internal_c0") == 0 and row.get("replacement_characters") == 0 and row.get("affected_pages") == 0)

    render = load("render.json")
    check("render_pass", render.get("record_id") == "ZH-NOETHER-CUM-R10B-RENDER-001" and render.get("all_pass") is True and render.get("pixel_identical_pages") == 424 and len(render.get("page_records", [])) == 424)
    compare = load("compare.json")
    check("compare_pass", compare.get("record_id") == "ZH-NOETHER-CUM-R10B-R10-EQUALITY-001" and compare.get("all_pass") is True and compare.get("state") == "PASS_MACHINE_VALIDATED_RELEASE_READY")
    check("compare_424", all(compare.get(key) == 424 for key in ("pages", "content_streams_equal", "extracted_text_equal", "geometry_equal", "fresh_120_dpi_rasters_equal")))
    check("compare_rows", all(row.get("content_equal") and row.get("text_equal") and row.get("geometry_equal") for row in compare.get("pdf_page_records", [])) and all(row.get("equal") for row in compare.get("raster_page_records", [])))
    check("compare_metadata", compare.get("metadata", {}).get("changed_keys") == ["/Title"] and compare.get("metadata", {}).get("successor", {}).get("/Title") == "Noether Simplified Chinese cumulative rebase r10" and compare.get("metadata", {}).get("successor", {}).get("/Author") == "Emmy Noether")
    visual = load("visual.json")
    check("visual_pass", visual.get("record_id") == "ZH-NOETHER-CUM-R10B-VISUAL-001" and visual.get("state") == "PASS_MACHINE_VALIDATED_RELEASE_READY" and visual.get("all_pass") is True and len(visual.get("contact_sheets", [])) == 8 and visual.get("inspection", {}).get("page_coverage_visible") == "424/424" and visual.get("inspection", {}).get("failures") == 0)

    ret = load("return.json")
    check("return_state", ret.get("return_id") == "ZH-NOETHER-CUM-R10B-PRODUCER-001" and ret.get("disposition") == "MACHINE_VALIDATED_RELEASE_READY" and ret.get("release_ready") is True and ret.get("publishable") is True)
    check("release_without_review_gate", ret.get("human_review_required") is False and ret.get("independent_review_required") is False and ret.get("checker_acceptance_required") is False and ret.get("clean_day_gate_required") is False)
    check("return_release_gate", ret.get("release_gate", {}).get("machine_validation") == "PASS" and ret.get("release_gate", {}).get("human_review") == "OPTIONAL_NONBLOCKING" and ret.get("release_gate", {}).get("independent_review") == "OPTIONAL_NONBLOCKING" and ret.get("release_gate", {}).get("checker_acceptance") == "NOT_REQUIRED")
    check("return_scope", ret.get("target", {}).get("language") == "Chinese" and ret.get("target", {}).get("Hant") == "NO_INTAKE" and ret.get("sga") == "held and untouched" and ret.get("publication") == "not_yet_published")

    current_surfaces = "\n".join([
        "".join(line.decode("utf-8") for line in target_lines[:6]),
        (ROOT / "STATE.md").read_text(encoding="utf-8"),
        (ROOT / "return.json").read_text(encoding="utf-8"),
        (ROOT / "handoff.md").read_text(encoding="utf-8"),
    ])
    check("current_surfaces_release_ready", "MACHINE_VALIDATED_RELEASE_READY" in current_surfaces and "publishable=true" in current_surfaces)
    check("no_current_blocking_gate", "FROZEN_PENDING_INDEPENDENT_RECHECK" not in current_surfaces and "nonpublishable" not in current_surfaces and "0/3" not in current_surfaces)
    check("claim_boundary", "No external" in current_surfaces and "not_yet_published" in current_surfaces)

    raw_reader = PdfReader(str(ROOT / "raw.pdf"), strict=True)
    final_reader = PdfReader(str(ROOT / "reader.pdf"), strict=True)
    final_metadata = final_reader.metadata or {}
    check("pdf_pages", len(raw_reader.pages) == len(final_reader.pages) == 424)
    check("pdf_metadata", str(final_metadata.get("/Title")) == "Noether Simplified Chinese cumulative rebase r10" and str(final_metadata.get("/Author")) == "Emmy Noether")

    manifest_identity = identity(MANIFEST) if MANIFEST.is_file() else {"missing": True}
    root_files = [path for path in ROOT.rglob("*") if path.is_file()]
    all_pass = all(row["pass"] for row in checks)
    result = {
        "verification_id": "ZH-NOETHER-CUM-R10B-VERIFY-002",
        "all_pass": all_pass,
        "checks_passed": sum(1 for row in checks if row["pass"]),
        "checks_total": len(checks),
        "checks": checks,
        "manifest": {**manifest_identity, "entries": len(rows), "member_bytes": sum(row[1] for row in rows)},
        "root_census": {"files_including_manifest": len(root_files), "bytes_including_manifest": sum(path.stat().st_size for path in root_files)},
        "local_pins": local_results,
        "external_pins": external_results,
        "disposition": "PASS_MACHINE_VALIDATED_RELEASE_READY" if all_pass else "FAIL",
        "scope": {"target": "complete PRC-oriented zh-Hans Noether reader", "Hant": "NO_INTAKE", "German_mutated": False, "SGA": "held and untouched", "publication": "not_yet_published"},
    }
    payload = (json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if args.out:
        out = args.out.resolve()
        try:
            out.relative_to(ROOT)
        except ValueError:
            pass
        else:
            raise SystemExit("--out must be outside frozen root")
        if out.exists() or not out.parent.is_dir():
            raise SystemExit("refusing invalid --out")
        out.write_bytes(payload)
    else:
        sys.stdout.buffer.write(payload)
    if not all_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
