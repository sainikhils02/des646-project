"""Automated experiment runner for ICoRD'27 paper evaluation.

Runs three experiments:
  1. Agentic vs Static audit comparison
  2. Remediation quality evaluation
  3. DFS component ablation study

Usage:
    python scripts/experiment_runner.py --output-dir experiments/
    python scripts/experiment_runner.py --urls urls.txt --output-dir experiments/
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from design_assistant.pipeline import DesignAssistant, InputMode, PipelineResult
from design_assistant.fusion import DesignFairnessScore


# Default benchmark URLs — mix of accessible, dark-pattern-heavy, and average sites
DEFAULT_URLS = [
    "https://www.w3.org/WAI/demos/bad/before/home.html",    # Intentionally bad accessibility
    "https://www.w3.org/WAI/demos/bad/after/home.html",      # Fixed version
    "https://example.com",                                     # Minimal baseline
    "https://www.wikipedia.org",                               # Generally accessible
    "https://www.gov.uk",                                      # Accessibility-focused
    "https://www.amazon.com",                                  # E-commerce (dark patterns)
    "https://www.booking.com",                                 # Travel (urgency patterns)
    "https://www.nytimes.com",                                 # News site
    "https://github.com",                                      # Developer platform
    "https://www.apple.com",                                   # Polished commercial
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--urls", type=Path, help="Text file with one URL per line")
    parser.add_argument("--output-dir", type=Path, default=Path("experiments"), help="Output directory")
    parser.add_argument("--experiment", choices=["all", "agentic", "remediation", "ablation"], default="all")
    parser.add_argument("--max-urls", type=int, default=10, help="Max URLs to process")
    return parser.parse_args()


def load_urls(path: Optional[Path], max_urls: int) -> List[str]:
    if path and path.exists():
        with open(path) as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    else:
        urls = DEFAULT_URLS.copy()
    return urls[:max_urls]


# ---------------------------------------------------------------------------
# Experiment 1: Agentic vs Static comparison
# ---------------------------------------------------------------------------

def experiment_agentic_vs_static(urls: List[str], output_dir: Path) -> None:
    """Compare issues found by static-only audit vs agentic audit."""
    print("\n" + "=" * 60)
    print("EXPERIMENT 1: Agentic vs Static Audit Comparison")
    print("=" * 60)

    results_dir = output_dir / "exp1_agentic_vs_static"
    results_dir.mkdir(parents=True, exist_ok=True)

    rows = []

    for url in urls:
        print(f"\n  Auditing: {url}")
        row = {"url": url, "timestamp": datetime.now().isoformat()}

        try:
            # Static-only audit
            print("    Running static audit...")
            static_assistant = DesignAssistant(
                enable_agentic=False,
                enable_remediation=False,
                alpha=0.4, beta=0.3,
            )
            t0 = time.time()
            static_result = static_assistant.run(InputMode.URL, url, output_dir=results_dir / "static" / _safe_name(url))
            static_time = time.time() - t0

            row["static_dfs"] = round(static_result.fairness.value, 4)
            row["static_accessibility_score"] = round(static_result.accessibility.score, 4) if static_result.accessibility else None
            row["static_contrast_violations"] = len(static_result.contrast.violations)
            row["static_dark_pattern_flags"] = len(static_result.dark_patterns.flags)
            row["static_total_issues"] = row["static_contrast_violations"] + row["static_dark_pattern_flags"]
            row["static_time_s"] = round(static_time, 2)

            # Full audit (with agentic)
            print("    Running full agentic audit...")
            full_assistant = DesignAssistant(
                enable_agentic=True,
                enable_remediation=False,
                alpha=0.4, beta=0.3,
            )
            t0 = time.time()
            full_result = full_assistant.run(InputMode.URL, url, output_dir=results_dir / "full" / _safe_name(url))
            full_time = time.time() - t0

            row["full_dfs"] = round(full_result.fairness.value, 4)
            row["full_keyboard_score"] = round(full_result.agentic.keyboard_score, 4) if full_result.agentic else None
            row["full_sr_score"] = round(full_result.agentic.screen_reader_score, 4) if full_result.agentic else None
            row["full_keyboard_issues"] = len(full_result.agentic.keyboard_issues) if full_result.agentic else 0
            row["full_sr_issues"] = len(full_result.agentic.screen_reader_issues) if full_result.agentic else 0
            row["full_functional_issues"] = len(full_result.agentic.functional_issues) if full_result.agentic else 0
            row["full_agentic_only_issues"] = row["full_keyboard_issues"] + row["full_sr_issues"] + row["full_functional_issues"]
            row["full_total_issues"] = row["static_total_issues"] + row["full_agentic_only_issues"]
            row["full_time_s"] = round(full_time, 2)

            row["dfs_delta"] = round(row["full_dfs"] - row["static_dfs"], 4)
            row["agentic_issue_pct"] = round(
                row["full_agentic_only_issues"] / max(row["full_total_issues"], 1) * 100, 1
            )

            print(f"    Static DFS: {row['static_dfs']:.3f} | Full DFS: {row['full_dfs']:.3f} | "
                  f"Agentic-only issues: {row['full_agentic_only_issues']}")

        except Exception as exc:
            print(f"    ERROR: {exc}")
            row["error"] = str(exc)

        rows.append(row)

    # Save CSV
    csv_path = results_dir / "results.csv"
    _write_csv(rows, csv_path)
    print(f"\n  Results saved to: {csv_path}")


# ---------------------------------------------------------------------------
# Experiment 2: Remediation quality
# ---------------------------------------------------------------------------

def experiment_remediation(urls: List[str], output_dir: Path) -> None:
    """Evaluate remediation quality: count suggestions, predicted DFS delta."""
    print("\n" + "=" * 60)
    print("EXPERIMENT 2: Remediation Quality Evaluation")
    print("=" * 60)

    results_dir = output_dir / "exp2_remediation"
    results_dir.mkdir(parents=True, exist_ok=True)

    rows = []

    for url in urls:
        print(f"\n  Auditing: {url}")
        row = {"url": url, "timestamp": datetime.now().isoformat()}

        try:
            assistant = DesignAssistant(
                enable_agentic=True,
                enable_remediation=True,
                alpha=0.4, beta=0.3,
            )
            result = assistant.run(InputMode.URL, url, output_dir=results_dir / _safe_name(url))

            row["dfs_before"] = round(result.fairness.value, 4)
            row["total_issues"] = (
                len(result.contrast.violations) +
                len(result.dark_patterns.flags) +
                (result.agentic.total_issues if result.agentic else 0)
            )

            if result.remediation:
                row["remediation_count"] = len(result.remediation.suggestions)
                row["predicted_dfs_delta"] = round(result.remediation.total_predicted_dfs_delta, 4)
                row["high_priority"] = sum(1 for s in result.remediation.suggestions if s.priority == "high")
                row["medium_priority"] = sum(1 for s in result.remediation.suggestions if s.priority == "medium")
                row["low_priority"] = sum(1 for s in result.remediation.suggestions if s.priority == "low")

                # Save individual remediation report
                rem_path = results_dir / _safe_name(url) / "remediation.json"
                rem_path.parent.mkdir(parents=True, exist_ok=True)
                with open(rem_path, "w") as f:
                    json.dump(result.remediation.to_dict(), f, indent=2)
            else:
                row["remediation_count"] = 0
                row["predicted_dfs_delta"] = 0.0

            print(f"    Issues: {row['total_issues']} | Remediations: {row['remediation_count']} | "
                  f"Predicted delta: {row.get('predicted_dfs_delta', 0):.3f}")

        except Exception as exc:
            print(f"    ERROR: {exc}")
            row["error"] = str(exc)

        rows.append(row)

    csv_path = results_dir / "results.csv"
    _write_csv(rows, csv_path)
    print(f"\n  Results saved to: {csv_path}")


# ---------------------------------------------------------------------------
# Experiment 3: DFS ablation
# ---------------------------------------------------------------------------

def experiment_ablation(urls: List[str], output_dir: Path) -> None:
    """Ablation study: disable each DFS tier and measure score change."""
    print("\n" + "=" * 60)
    print("EXPERIMENT 3: DFS Component Ablation Study")
    print("=" * 60)

    results_dir = output_dir / "exp3_ablation"
    results_dir.mkdir(parents=True, exist_ok=True)

    rows = []

    for url in urls:
        print(f"\n  Auditing: {url}")
        row = {"url": url, "timestamp": datetime.now().isoformat()}

        try:
            assistant = DesignAssistant(
                enable_agentic=True,
                enable_remediation=False,
                alpha=0.4, beta=0.3,
            )
            result = assistant.run(InputMode.URL, url, output_dir=results_dir / _safe_name(url))

            # Full DFS
            row["full_dfs"] = round(result.fairness.value, 4)
            row["technical_score"] = round(result.fairness.technical.value, 4)
            row["perceptual_score"] = round(result.fairness.perceptual.value, 4)
            row["ethical_score"] = round(result.fairness.ethical.value, 4)

            # Ablation: remove technical
            dfs_no_tech = DesignFairnessScore.from_components(
                accessibility_score=None,
                ethical_score=result.dark_patterns.score,
                contrast_score=getattr(result.contrast, 'contrast_score', None),
                keyboard_score=None,
                screen_reader_score=None,
                alpha=0.0, beta=0.5,
            )
            row["dfs_no_technical"] = round(dfs_no_tech.value, 4)

            # Ablation: remove perceptual
            dfs_no_perc = DesignFairnessScore.from_components(
                accessibility_score=result.accessibility.score if result.accessibility else None,
                ethical_score=result.dark_patterns.score,
                contrast_score=None,
                keyboard_score=result.agentic.keyboard_score if result.agentic else None,
                screen_reader_score=result.agentic.screen_reader_score if result.agentic else None,
                alpha=0.6, beta=0.4,
            )
            row["dfs_no_perceptual"] = round(dfs_no_perc.value, 4)

            # Ablation: remove ethical
            dfs_no_eth = DesignFairnessScore.from_components(
                accessibility_score=result.accessibility.score if result.accessibility else None,
                ethical_score=0.0,
                contrast_score=getattr(result.contrast, 'contrast_score', None),
                keyboard_score=result.agentic.keyboard_score if result.agentic else None,
                screen_reader_score=result.agentic.screen_reader_score if result.agentic else None,
                alpha=0.6, beta=0.0,
            )
            row["dfs_no_ethical"] = round(dfs_no_eth.value, 4)

            row["delta_no_technical"] = round(row["dfs_no_technical"] - row["full_dfs"], 4)
            row["delta_no_perceptual"] = round(row["dfs_no_perceptual"] - row["full_dfs"], 4)
            row["delta_no_ethical"] = round(row["dfs_no_ethical"] - row["full_dfs"], 4)

            print(f"    Full: {row['full_dfs']:.3f} | "
                  f"−Tech: {row['dfs_no_technical']:.3f} | "
                  f"−Perc: {row['dfs_no_perceptual']:.3f} | "
                  f"−Eth: {row['dfs_no_ethical']:.3f}")

        except Exception as exc:
            print(f"    ERROR: {exc}")
            row["error"] = str(exc)

        rows.append(row)

    csv_path = results_dir / "results.csv"
    _write_csv(rows, csv_path)
    print(f"\n  Results saved to: {csv_path}")


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _safe_name(url: str) -> str:
    """Convert a URL to a filesystem-safe directory name."""
    import re
    name = url.replace("https://", "").replace("http://", "").replace("www.", "")
    return re.sub(r"[^a-zA-Z0-9-]", "_", name)[:50]


def _write_csv(rows: List[Dict], path: Path) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(rows[0].keys())
    for r in rows[1:]:
        for k in r:
            if k not in keys:
                keys.append(k)

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    urls = load_urls(args.urls, args.max_urls)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Experiment runner — {len(urls)} URLs — output: {args.output_dir}")

    if args.experiment in ("all", "agentic"):
        experiment_agentic_vs_static(urls, args.output_dir)
    if args.experiment in ("all", "remediation"):
        experiment_remediation(urls, args.output_dir)
    if args.experiment in ("all", "ablation"):
        experiment_ablation(urls, args.output_dir)

    print("\n" + "=" * 60)
    print("All experiments complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
