#!/usr/bin/env python3
"""
diag_test.py — Pipeline differentiation diagnostic tool.

Runs Stage 2 scoring on one or more photos, saves raw JSON results,
prints a side-by-side comparison table and flags suspicious similarity.

Usage:
    python diag_test.py                              # all images in test_images/
    python diag_test.py uploads/a.jpg uploads/b.jpg  # specific files
    python diag_test.py --lang en                    # English analysis
    python diag_test.py --save-dir my_run/           # custom output dir
    python diag_test.py --model gpt-4o-mini          # cheaper model for quick tests
    python diag_test.py --stage1                     # also run Stage 1 validation first

Output files (written to --save-dir, default: test_results/):
    <image_stem>_<HHMMSS>.json   — raw Stage 2 JSON for each photo
    report_<YYYYMMDD_HHMMSS>.json — full comparison report
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime
from statistics import mean, stdev

# ── Setup env before any local imports ────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(override=True)


# ── Constants ──────────────────────────────────────────────────────────────────

SCORE_FIELDS = [
    "overall_face", "upper_face", "eye_area", "mid_face", "lower_face",
    "neck", "skin_quality", "skin_tension", "face_oval", "symmetry",
    "wrinkles", "pigmentation", "vessels", "freshness", "hairline", "hair_thinning",
]

# Fields that can legitimately default to 5 (not visible in photo)
OPTIONAL_FIELDS = {"neck", "hairline", "hair_thinning", "symmetry"}

# Thresholds for differentiation checks
SIMILAR_PAIR_THRESHOLD  = 1.5   # mean absolute score diff below this → pair is suspicious
LOW_VARIANCE_THRESHOLD  = 0.8   # per-field stdev below this (across all photos) → field never varies
TREATMENT_OVERLAP_LIMIT = 4     # shared treatments between 2 photos → flag overlap


# ── Core ───────────────────────────────────────────────────────────────────────

def run_stage2(image_path: str, client, model: str, lang: str) -> dict:
    from pipeline.stage2_score import run
    return run(
        image_path=image_path,
        openai_client=client,
        model=model,
        lang=lang,
        validation_metadata=None,
    )


def run_stage1_then_stage2(image_path: str, client, model: str, lang: str) -> dict:
    from pipeline.stage1_validate import run as s1_run
    from pipeline.stage2_score import run as s2_run

    print("  [Stage 1] validating photo...", flush=True)
    val = s1_run(image_path, client, model)
    if not val["accepted"]:
        reason = val.get("reject_reason", "unknown")
        raise ValueError(f"Stage 1 rejected photo: {reason}")
    print(f"  [Stage 1] accepted, warnings={len(val['warnings'])}", flush=True)

    return s2_run(
        image_path=image_path,
        openai_client=client,
        model=model,
        lang=lang,
        validation_metadata=val.get("metadata", {}),
    )


# ── Report helpers ─────────────────────────────────────────────────────────────

def scores_of(result: dict) -> dict[str, int]:
    return result.get("scores", {})


def fmt_score(v: int) -> str:
    bar = "#" * v + "." * (10 - v)
    return f"{v:2d}/10  {bar}"


def print_header(title: str) -> None:
    print(f"\n{'=' * 72}")
    print(f"  {title}")
    print(f"{'=' * 72}")


def print_scores_table(records: list[dict]) -> None:
    names = [r["name"] for r in records]
    cols  = len(names)

    print_header("SCORE TABLE — side by side")

    # Column headers
    col_w = 22
    header = f"{'Field':<18}" + "".join(f"{n[:col_w - 2]:<{col_w}}" for n in names)
    print(header)
    print("-" * (18 + cols * col_w))

    for field in SCORE_FIELDS:
        scores = [scores_of(r["result"]).get(field, "-") for r in records]
        row    = f"{field:<18}"
        for s in scores:
            cell = fmt_score(s) if isinstance(s, int) else f"{'N/A':<22}"
            row += f"{cell:<{col_w}}"

        # Flag if all same
        int_scores = [s for s in scores if isinstance(s, int)]
        if len(int_scores) > 1 and max(int_scores) - min(int_scores) == 0:
            row += "  << same"
        print(row)


def print_differentiation_report(records: list[dict]) -> list[str]:
    """Print per-field variance report. Returns list of warning strings."""
    warnings: list[str] = []

    print_header("DIFFERENTIATION REPORT — field variance across photos")

    field_scores: dict[str, list[int]] = {f: [] for f in SCORE_FIELDS}
    for r in records:
        for field in SCORE_FIELDS:
            v = scores_of(r["result"]).get(field)
            if isinstance(v, int):
                field_scores[field].append(v)

    print(f"{'Field':<18}  {'Min':>4} {'Max':>4} {'Mean':>6} {'Stdev':>6}  Status")
    print("-" * 62)

    frozen_fields: list[str] = []
    for field in SCORE_FIELDS:
        vals = field_scores[field]
        if len(vals) < 2:
            print(f"{field:<18}  (only {len(vals)} data point — skipping)")
            continue
        mn   = min(vals)
        mx   = max(vals)
        avg  = mean(vals)
        sd   = stdev(vals)
        flag = ""
        if field in OPTIONAL_FIELDS and avg == 5.0:
            flag = "  (optional, not visible in photos)"
        elif sd < LOW_VARIANCE_THRESHOLD:
            flag = "  ← LOW VARIANCE — always similar"
            frozen_fields.append(field)
        print(f"{field:<18}  {mn:>4} {mx:>4} {avg:>6.1f} {sd:>6.2f}{flag}")

    if frozen_fields:
        msg = f"Fields with suspiciously low variance (stdev < {LOW_VARIANCE_THRESHOLD}): {frozen_fields}"
        warnings.append(msg)
        print(f"\n  WARNING: {msg}")

    return warnings


def print_pairwise_similarity(records: list[dict]) -> list[str]:
    """Compare every pair of photos. Returns list of warning strings."""
    warnings: list[str] = []

    if len(records) < 2:
        return warnings

    print_header("PAIRWISE SIMILARITY — score distance between photos")

    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            a, b = records[i], records[j]
            sa, sb = scores_of(a["result"]), scores_of(b["result"])

            shared_fields = [f for f in SCORE_FIELDS
                             if isinstance(sa.get(f), int) and isinstance(sb.get(f), int)]
            if not shared_fields:
                continue

            diffs    = [abs(sa[f] - sb[f]) for f in shared_fields]
            mean_d   = mean(diffs)
            identical = [f for f, d in zip(shared_fields, diffs) if d == 0]

            ta = set(a["result"].get("treatments", []))
            tb = set(b["result"].get("treatments", []))
            shared_t = ta & tb

            print(f"\n  {a['name']}  vs  {b['name']}")
            print(f"    Mean field difference:   {mean_d:.2f}/10")
            print(f"    Identical score fields:  {len(identical)}/{len(shared_fields)}")
            print(f"    Shared treatments:       {len(shared_t)} — {sorted(shared_t) or '(none)'}")

            if mean_d < SIMILAR_PAIR_THRESHOLD:
                msg = (f"SUSPICIOUS: {a['name']} and {b['name']} are very similar "
                       f"(mean diff {mean_d:.2f}, threshold {SIMILAR_PAIR_THRESHOLD})")
                warnings.append(msg)
                print(f"    *** {msg}")

            if len(shared_t) >= TREATMENT_OVERLAP_LIMIT:
                msg = (f"TREATMENT OVERLAP: {a['name']} and {b['name']} share "
                       f"{len(shared_t)} treatments: {sorted(shared_t)}")
                warnings.append(msg)
                print(f"    *** {msg}")

    return warnings


def print_strengths_concerns(records: list[dict]) -> None:
    print_header("STRENGTHS & CONCERNS — do they differ across photos?")
    for r in records:
        res = r["result"]
        print(f"\n  {r['name']}")
        print(f"    Strengths:    {res.get('strengths', [])}")
        print(f"    Improvements: {res.get('improvements', [])}")
        print(f"    Treatments:   {res.get('suggested_treatments', [])}")
        print(f"    health_note:  {str(res.get('health_note', ''))[:80]}")


def print_summary(records: list[dict], all_warnings: list[str], elapsed_total: float) -> None:
    ok      = [r for r in records if r["error"] is None]
    failed  = [r for r in records if r["error"] is not None]

    print_header("SUMMARY")
    print(f"  Photos processed:  {len(ok)}/{len(records)}")
    print(f"  Total time:        {elapsed_total:.1f}s")

    if failed:
        print(f"\n  FAILED ({len(failed)}):")
        for r in failed:
            print(f"    {r['name']}: {r['error']}")

    if all_warnings:
        print(f"\n  DIFFERENTIATION WARNINGS ({len(all_warnings)}):")
        for w in all_warnings:
            print(f"    *** {w}")
    else:
        print("\n  No differentiation issues detected.")


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pipeline differentiation diagnostic",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("images",    nargs="*", help="Image file paths (default: test_images/*)")
    parser.add_argument("--lang",    default="pl", choices=["pl", "en"])
    parser.add_argument("--model",   default="gpt-4o")
    parser.add_argument("--save-dir", default="test_results", dest="save_dir")
    parser.add_argument("--stage1",  action="store_true", help="Also run Stage 1 photo validation")
    args = parser.parse_args()

    # ── Find images ────────────────────────────────────────────────────────────
    if args.images:
        image_paths = [Path(p) for p in args.images]
    else:
        test_dir = Path("test_images")
        if not test_dir.exists():
            print("[ERROR] test_images/ directory not found. Create it and add .jpg/.png photos.")
            sys.exit(1)
        image_paths = sorted(
            list(test_dir.glob("*.jpg")) +
            list(test_dir.glob("*.jpeg")) +
            list(test_dir.glob("*.png")) +
            list(test_dir.glob("*.webp"))
        )

    if not image_paths:
        print("[ERROR] No images found. Add photos to test_images/ or pass paths as arguments.")
        sys.exit(1)

    # ── Setup OpenAI ───────────────────────────────────────────────────────────
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or "sk-" not in api_key:
        print("[ERROR] OPENAI_API_KEY not set or invalid. Add it to .env file.")
        sys.exit(1)
    client = OpenAI(api_key=api_key, timeout=120.0)

    # ── Output dir ─────────────────────────────────────────────────────────────
    save_dir = Path(args.save_dir)
    save_dir.mkdir(exist_ok=True)
    run_id   = datetime.now().strftime("%Y%m%d_%H%M%S")

    runner = run_stage1_then_stage2 if args.stage1 else run_stage2

    print(f"\nDiagnostic run: {run_id}")
    print(f"Model: {args.model} | Lang: {args.lang} | Stage1: {args.stage1}")
    print(f"Photos: {[p.name for p in image_paths]}")
    print(f"Output: {save_dir}/")

    # ── Process each image ─────────────────────────────────────────────────────
    records: list[dict] = []
    t_start = time.time()

    for img_path in image_paths:
        print(f"\n{'-' * 60}")
        print(f"  Processing: {img_path.name}")
        t0 = time.time()
        try:
            result  = runner(str(img_path), client, args.model, args.lang)
            elapsed = time.time() - t0

            # Save individual JSON result
            out_name = f"{img_path.stem}_{datetime.now().strftime('%H%M%S')}.json"
            out_path = save_dir / out_name
            payload  = {
                "run_id":    run_id,
                "image":     str(img_path),
                "model":     args.model,
                "lang":      args.lang,
                "elapsed_s": round(elapsed, 2),
                "timestamp": datetime.now().isoformat(),
                "result":    result,
            }
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)

            records.append({
                "name":    img_path.name,
                "path":    str(img_path),
                "result":  result,
                "elapsed": elapsed,
                "error":   None,
                "saved":   str(out_path),
            })
            print(f"  [OK] {elapsed:.1f}s  → {out_path}")

        except Exception as e:
            elapsed = time.time() - t0
            records.append({
                "name":    img_path.name,
                "path":    str(img_path),
                "result":  None,
                "elapsed": elapsed,
                "error":   str(e),
                "saved":   None,
            })
            print(f"  [FAIL] {elapsed:.1f}s  {e}")

    elapsed_total = time.time() - t_start

    # ── Reports ────────────────────────────────────────────────────────────────
    ok_records = [r for r in records if r["result"] is not None]

    all_warnings: list[str] = []

    if ok_records:
        print_scores_table(ok_records)
        all_warnings += print_differentiation_report(ok_records)
        all_warnings += print_pairwise_similarity(ok_records)
        print_strengths_concerns(ok_records)

    print_summary(records, all_warnings, elapsed_total)

    # ── Save full report ───────────────────────────────────────────────────────
    report_path = save_dir / f"report_{run_id}.json"
    report_data = {
        "run_id":    run_id,
        "model":     args.model,
        "lang":      args.lang,
        "timestamp": datetime.now().isoformat(),
        "warnings":  all_warnings,
        "photos":    [
            {
                "name":    r["name"],
                "elapsed": round(r["elapsed"], 2),
                "error":   r["error"],
                "saved":   r["saved"],
                "scores":  scores_of(r["result"]) if r["result"] else None,
                "strengths":    r["result"].get("strengths")    if r["result"] else None,
                "improvements": r["result"].get("improvements") if r["result"] else None,
                "treatments":   r["result"].get("suggested_treatments") if r["result"] else None,
            }
            for r in records
        ],
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    print(f"\n  Full report: {report_path}")


if __name__ == "__main__":
    main()
