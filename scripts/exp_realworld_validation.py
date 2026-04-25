#!/usr/bin/env python3
"""Experiment: Real-world validation on 5+ production websites.

Runs the full DFS pipeline (all 4 auditors + remediation) on real production
websites to demonstrate that the framework generalises beyond controlled
benchmark pages.

Usage:
    set GOOGLE_API_KEY=your-key
    python scripts/exp_realworld_validation.py

Output:
    experiments/exp_realworld/results.csv
    experiments/exp_realworld/<site>_report.json  (per-site)
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

OUTPUT_DIR = PROJECT_ROOT / "experiments" / "exp_realworld"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Sites to audit — chosen for diversity
SITES = [
    ("example.com",     "https://example.com"),
    ("wikipedia.org",   "https://en.wikipedia.org/wiki/Main_Page"),
    ("w3.org_wai",      "https://www.w3.org/WAI/"),
    ("iitk.ac.in",      "https://www.iitk.ac.in/"),
    ("python.org",      "https://www.python.org/"),
]


def create_driver():
    """Create a headless Chrome driver."""
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    return webdriver.Chrome(options=opts)


def audit_site(driver, url: str, name: str) -> dict:
    """Run the full audit pipeline on a single site."""
    import cv2
    import numpy as np

    from design_assistant.audits.contrast import ContrastAuditor
    from design_assistant.audits.dark_patterns import DarkPatternAuditor
    from design_assistant.audits.agentic import AgenticAuditor
    from design_assistant.fusion import DesignFairnessScore
    from design_assistant.remediation import RemediationEngine

    result = {
        "site": name,
        "url": url,
        "timestamp": datetime.now().isoformat(),
    }

    print(f"\n{'='*60}")
    print(f"  Auditing: {name} ({url})")
    print(f"{'='*60}")

    try:
        # 1. Navigate and collect
        print(f"  [1/6] Loading page...")
        driver.get(url)
        time.sleep(3)  # Wait for full load

        # Get page source and screenshot
        html = driver.page_source
        screenshot_path = str(OUTPUT_DIR / f"{name}_screenshot.png")
        driver.save_screenshot(screenshot_path)
        print(f"  [1/6] Page loaded, screenshot saved.")

        # 2. Accessibility audit (axe-core)
        print(f"  [2/6] Running accessibility audit (axe-core)...")
        try:
            from axe_selenium_python import Axe
            axe = Axe(driver)
            axe.inject()
            axe_results = axe.run()
            violations = axe_results.get("violations", [])
            acc_violation_count = sum(len(v.get("nodes", [])) for v in violations)
            # Simple score: 1 - (violations / max_expected)
            acc_score = max(0.0, 1.0 - acc_violation_count / 50.0)
            result["accessibility_violations"] = acc_violation_count
            result["accessibility_score"] = round(acc_score, 4)
            print(f"        {acc_violation_count} violations, score={acc_score:.3f}")
        except Exception as e:
            print(f"        axe-core failed: {e}")
            result["accessibility_violations"] = 0
            result["accessibility_score"] = None
            acc_score = None

        # 3. Contrast audit
        print(f"  [3/6] Running contrast audit (KMeans-CIELAB)...")
        img = cv2.imread(screenshot_path)
        contrast_auditor = ContrastAuditor(method="kmeans_cielab", n_clusters=3)
        contrast_report = contrast_auditor.audit(img)
        result["contrast_violations"] = len(contrast_report.violations)
        result["contrast_avg"] = round(contrast_report.average_contrast, 2)
        result["contrast_score"] = round(contrast_report.contrast_score or 0, 4)
        print(f"        {len(contrast_report.violations)} violations, avg={contrast_report.average_contrast:.2f}:1")

        # 4. Dark pattern audit
        print(f"  [4/6] Running dark pattern audit...")
        dp_auditor = DarkPatternAuditor()
        # Extract visible text from the page
        visible_text = driver.execute_script(
            "return document.body ? document.body.innerText : '';"
        )
        dp_report = dp_auditor.audit(visible_text or "")
        result["dark_pattern_flags"] = len(dp_report.flags)
        result["dark_pattern_score"] = round(dp_report.score, 4)
        print(f"        {len(dp_report.flags)} flags, score={dp_report.score:.3f}")

        # 5. Agentic audit
        print(f"  [5/6] Running agentic audit (keyboard + screen reader)...")
        agentic_auditor = AgenticAuditor()
        agentic_report = agentic_auditor.audit(driver)
        kb_issues = len(agentic_report.keyboard_issues)
        sr_issues = len(agentic_report.screen_reader_issues)
        func_issues = len(agentic_report.functional_issues)
        kb_score = agentic_report.keyboard_score
        sr_score = agentic_report.screen_reader_score
        tab_order = len(agentic_report.tab_order)
        result["keyboard_issues"] = kb_issues
        result["screen_reader_issues"] = sr_issues
        result["functional_issues"] = func_issues
        result["keyboard_score"] = round(kb_score, 4)
        result["screen_reader_score"] = round(sr_score, 4)
        result["tab_order_length"] = tab_order
        result["agentic_only_issues"] = kb_issues + sr_issues + func_issues
        print(f"        KB issues={kb_issues}, SR issues={sr_issues}, functional={func_issues}")

        # 6. Compute DFS
        print(f"  [6/6] Computing DFS...")
        dfs = DesignFairnessScore.from_components(
            accessibility_score=acc_score,
            ethical_score=dp_report.score,
            contrast_score=contrast_report.contrast_score or 0,
            keyboard_score=kb_score,
            screen_reader_score=sr_score,
        )
        result["dfs"] = round(dfs.value, 4)
        result["technical_tier"] = round(dfs.technical.value, 4)
        result["perceptual_tier"] = round(dfs.perceptual.value, 4)
        result["ethical_tier"] = round(dfs.ethical.value, 4)
        print(f"        DFS={dfs.value:.3f}  (Tech={dfs.technical.value:.3f}, Perc={dfs.perceptual.value:.3f}, Eth={dfs.ethical.value:.3f})")

        # Total issues
        total_static = (result.get("accessibility_violations", 0) +
                        result.get("contrast_violations", 0) +
                        result.get("dark_pattern_flags", 0))
        result["total_static_issues"] = total_static
        result["total_issues"] = total_static + result["agentic_only_issues"]

        # Remediation
        try:
            remediation = RemediationEngine()
            all_issues = []
            for v in (violations if acc_score is not None else []):
                for node in v.get("nodes", [])[:2]:
                    all_issues.append({
                        "category": "accessibility",
                        "type": v.get("id", "unknown"),
                        "description": v.get("description", ""),
                        "severity": v.get("impact", "moderate"),
                        "html_snippet": node.get("html", ""),
                    })
            for flag in dp_report.flags:
                all_issues.append({
                    "category": "dark_pattern",
                    "type": flag.label,
                    "description": flag.text[:200],
                    "severity": "high" if flag.score > 0.7 else "medium",
                })
            fixes = remediation.generate(all_issues[:20], {
                "accessibility": acc_score,
                "contrast": contrast_report.contrast_score or 0,
                "ethical": dp_report.score,
                "keyboard": kb_score,
                "screen_reader": sr_score,
            })
            result["fixes_generated"] = len(fixes) if fixes else 0
            print(f"        {result['fixes_generated']} remediation fixes generated.")
        except Exception as e:
            result["fixes_generated"] = 0
            print(f"        Remediation error: {e}")

        # Save per-site JSON report
        report_path = OUTPUT_DIR / f"{name}_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"  Report saved: {report_path}")

    except Exception as e:
        result["error"] = str(e)
        print(f"  ERROR: {e}")
        traceback.print_exc()

    return result


def main():
    print("\n" + "="*60)
    print("  REAL-WORLD VALIDATION EXPERIMENT")
    print("  Auditing 5 production websites with the full DFS pipeline")
    print("="*60)

    driver = create_driver()
    results = []

    try:
        for name, url in SITES:
            try:
                result = audit_site(driver, url, name)
                results.append(result)
            except Exception as e:
                print(f"  SKIP {name}: {e}")
                results.append({"site": name, "url": url, "error": str(e)})
    finally:
        driver.quit()

    # Write CSV summary
    csv_path = OUTPUT_DIR / "results.csv"
    if results:
        keys = list(results[0].keys())
        # Collect all keys from all results
        for r in results:
            for k in r.keys():
                if k not in keys:
                    keys.append(k)

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for r in results:
                writer.writerow(r)

    print(f"\n{'='*60}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"{'Site':<20} {'DFS':>6} {'Issues':>7} {'Agentic':>8} {'Fixes':>6}")
    print(f"{'-'*20} {'-'*6} {'-'*7} {'-'*8} {'-'*6}")
    for r in results:
        if "error" in r and "dfs" not in r:
            print(f"{r['site']:<20} {'ERROR':>6}")
            continue
        print(f"{r['site']:<20} {r.get('dfs', 0):>6.3f} {r.get('total_issues', 0):>7} "
              f"{r.get('agentic_only_issues', 0):>8} {r.get('fixes_generated', 0):>6}")
    print(f"\nResults saved to: {csv_path}")


if __name__ == "__main__":
    main()
