#!/usr/bin/env python3
"""End-to-end pipeline demo on a REAL public URL.

Demonstrates that the entire framework works beyond test fixtures:
  1. Selenium collects DOM + screenshot from a live URL
  2. Contrast auditor analyses the screenshot (KMeans-CIELAB)
  3. Dark-pattern auditor scans visible text
  4. Agentic auditor simulates keyboard + screen-reader interaction
  5. DFS fusion computes the hierarchical score
  6. Remediation engine generates code fixes with impact predictions
"""
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent if (Path(__file__).resolve().parent.parent / "design_assistant").exists() else Path("/Users/venkatesh/Documents/des646-project")
sys.path.insert(0, str(PROJECT_ROOT))

import cv2
import numpy as np

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

from design_assistant.fusion import DesignFairnessScore
from design_assistant.audits.contrast import ContrastAuditor
from design_assistant.audits.dark_patterns import DarkPatternAuditor
from design_assistant.audits.agentic import AgenticAuditor
from design_assistant.remediation import RemediationEngine


def get_driver():
    opts = ChromeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,1024")
    try:
        service = ChromeService(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=opts)
    except Exception:
        return webdriver.Chrome(options=opts)


def main():
    # Use a well-known public site
    TARGET_URL = "https://example.com"
    OUTPUT_DIR = PROJECT_ROOT / "experiments" / "demo_real_url"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  END-TO-END DEMO ON REAL URL")
    print(f"  Target: {TARGET_URL}")
    print(f"{'='*60}\n")

    driver = get_driver()
    try:
        # Step 1: Collect
        print("[1/6] Collecting page...")
        t0 = time.time()
        driver.get(TARGET_URL)
        time.sleep(2)
        
        # Screenshot
        png = driver.get_screenshot_as_png()
        arr = np.frombuffer(png, dtype=np.uint8)
        screenshot = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        cv2.imwrite(str(OUTPUT_DIR / "screenshot.png"), screenshot)
        
        # Page text
        page_text = driver.execute_script("return document.body.innerText || '';")
        page_html = driver.execute_script("return document.documentElement.outerHTML || '';")
        
        print(f"    ✓ Screenshot: {screenshot.shape[1]}x{screenshot.shape[0]}")
        print(f"    ✓ Text length: {len(page_text)} chars")
        print(f"    ✓ HTML length: {len(page_html)} chars")
        collection_time = time.time() - t0

        # Step 2: Contrast Audit
        print("\n[2/6] Running contrast audit (KMeans-CIELAB)...")
        t0 = time.time()
        contrast_auditor = ContrastAuditor(method="kmeans_cielab")
        contrast_report = contrast_auditor.audit(screenshot)
        contrast_time = time.time() - t0
        print(f"    ✓ Violations: {len(contrast_report.violations)}")
        print(f"    ✓ Contrast score: {contrast_report.contrast_score:.4f}")
        print(f"    ✓ Avg contrast: {contrast_report.average_contrast:.3f}")
        print(f"    ✓ Time: {contrast_time*1000:.0f}ms")

        # Step 3: Dark Pattern Audit
        print("\n[3/6] Running dark-pattern audit...")
        t0 = time.time()
        dp_auditor = DarkPatternAuditor()
        dp_report = dp_auditor.audit(page_text)
        dp_time = time.time() - t0
        print(f"    ✓ Flags: {len(dp_report.flags)}")
        print(f"    ✓ Ethical score: {dp_report.score:.4f}")
        if dp_report.flags:
            for f in dp_report.flags[:3]:
                print(f"      → [{f.label}] {f.text[:60]}...")
        print(f"    ✓ Time: {dp_time*1000:.0f}ms")

        # Step 4: Agentic Audit (keyboard + screen-reader)
        print("\n[4/6] Running agentic audit (keyboard + screen-reader)...")
        t0 = time.time()
        driver.get(TARGET_URL)  # Fresh load
        time.sleep(1)
        agentic = AgenticAuditor()
        agentic_report = agentic.audit(driver)
        agentic_time = time.time() - t0
        print(f"    ✓ Keyboard score: {agentic_report.keyboard_score:.4f}")
        print(f"    ✓ Screen-reader score: {agentic_report.screen_reader_score:.4f}")
        print(f"    ✓ Keyboard issues: {len(agentic_report.keyboard_issues)}")
        print(f"    ✓ Screen-reader issues: {len(agentic_report.screen_reader_issues)}")
        print(f"    ✓ Functional issues: {len(agentic_report.functional_issues)}")
        print(f"    ✓ Tab order: {len(agentic_report.tab_order)} elements")
        print(f"    ✓ Time: {agentic_time*1000:.0f}ms")
        
        if agentic_report.keyboard_issues:
            print("    Keyboard issues found:")
            for i in agentic_report.keyboard_issues[:3]:
                print(f"      → [{i.severity}] {i.description[:80]}")
        if agentic_report.screen_reader_issues:
            print("    Screen-reader issues found:")
            for i in agentic_report.screen_reader_issues[:3]:
                print(f"      → [{i.severity}] {i.description[:80]}")
        if agentic_report.functional_issues:
            print("    Functional issues found:")
            for i in agentic_report.functional_issues[:3]:
                print(f"      → [{i.severity}] {i.description[:80]}")

        # Step 5: DFS Fusion
        print("\n[5/6] Computing hierarchical DFS...")
        dfs = DesignFairnessScore.from_components(
            accessibility_score=None,
            ethical_score=dp_report.score,
            contrast_score=contrast_report.contrast_score,
            keyboard_score=agentic_report.keyboard_score,
            screen_reader_score=agentic_report.screen_reader_score,
        )
        print(f"    ✓ Composite DFS: {dfs.value:.4f}")
        print(f"    ✓ Technical tier: {dfs.technical.value:.4f} (weight {dfs.technical.weight})")
        print(f"    ✓ Perceptual tier: {dfs.perceptual.value:.4f} (weight {dfs.perceptual.weight})")
        print(f"    ✓ Ethical tier: {dfs.ethical.value:.4f} (weight {dfs.ethical.weight})")
        print(f"    ✓ Sub-scores: {dfs.technical.sub_scores}")

        # Step 6: Remediation
        print("\n[6/6] Generating remediation suggestions...")
        all_issues = []
        for v in contrast_report.violations[:5]:
            all_issues.append({"category": "contrast", "severity": "moderate", "description": v.description or "Low contrast"})
        for f in dp_report.flags[:5]:
            all_issues.append({"category": "dark_pattern", "severity": "serious", "description": f"Dark pattern ({f.label}): {f.text[:80]}"})
        for issue in (list(agentic_report.keyboard_issues) + list(agentic_report.screen_reader_issues) + list(agentic_report.functional_issues))[:10]:
            all_issues.append({
                "category": issue.category, "severity": issue.severity,
                "description": issue.description, "element_info": issue.element_info,
                "wcag_criterion": issue.wcag_criterion, "recommendation": issue.recommendation,
            })

        remediation = RemediationEngine()
        t0 = time.time()
        if all_issues:
            rem_report = remediation.generate(
                issues=all_issues, html_snippet=page_html[:3000],
                current_scores={"technical": dfs.technical.value, "perceptual": dfs.perceptual.value, "ethical": dfs.ethical.value},
            )
            rem_time = time.time() - t0
            print(f"    ✓ Issues processed: {len(all_issues)}")
            print(f"    ✓ Fixes generated: {len(rem_report.suggestions)}")
            print(f"    ✓ Predicted DFS delta: {rem_report.total_predicted_dfs_delta:+.4f}")
            print(f"    ✓ Time: {rem_time*1000:.0f}ms")
            if rem_report.suggestions:
                print("    Top fixes:")
                for s in rem_report.suggestions[:3]:
                    print(f"      → [{s.priority}] {s.explanation[:70]}")
                    print(f"        Impact: T={s.predicted_impact.get('technical',0):+.3f} "
                          f"P={s.predicted_impact.get('perceptual',0):+.3f} "
                          f"E={s.predicted_impact.get('ethical',0):+.3f}")
        else:
            rem_report = None
            print("    ✓ No issues found — no remediation needed!")

        # Summary
        total_time = collection_time + contrast_time + dp_time + agentic_time
        total_issues = (len(agentic_report.keyboard_issues) + len(agentic_report.screen_reader_issues) 
                       + len(agentic_report.functional_issues) + len(contrast_report.violations) + len(dp_report.flags))

        print(f"\n{'='*60}")
        print(f"  DEMO SUMMARY")
        print(f"{'='*60}")
        print(f"  URL:              {TARGET_URL}")
        print(f"  Total issues:     {total_issues}")
        print(f"    - Contrast:     {len(contrast_report.violations)}")
        print(f"    - Dark pattern: {len(dp_report.flags)}")
        print(f"    - Keyboard:     {len(agentic_report.keyboard_issues)}")
        print(f"    - Screen-reader:{len(agentic_report.screen_reader_issues)}")
        print(f"    - Functional:   {len(agentic_report.functional_issues)}")
        print(f"  DFS:              {dfs.value:.4f}")
        print(f"    Technical:      {dfs.technical.value:.4f}")
        print(f"    Perceptual:     {dfs.perceptual.value:.4f}")
        print(f"    Ethical:        {dfs.ethical.value:.4f}")
        if rem_report:
            print(f"  Fixes generated:  {len(rem_report.suggestions)}")
            print(f"  Pred. improvement:{rem_report.total_predicted_dfs_delta:+.4f}")
        print(f"  Total time:       {total_time:.1f}s")
        print(f"{'='*60}\n")

        # Save results
        result = {
            "url": TARGET_URL,
            "dfs": dfs.to_dict(),
            "contrast": {"violations": len(contrast_report.violations), "score": contrast_report.contrast_score},
            "dark_patterns": {"flags": len(dp_report.flags), "score": dp_report.score},
            "agentic": agentic_report.to_dict(),
            "remediation": rem_report.to_dict() if rem_report else None,
            "timing": {
                "collection_s": round(collection_time, 2),
                "contrast_ms": round(contrast_time*1000, 1),
                "dark_pattern_ms": round(dp_time*1000, 1),
                "agentic_ms": round(agentic_time*1000, 1),
            },
        }
        with open(OUTPUT_DIR / "results.json", "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"  Results saved to: {OUTPUT_DIR / 'results.json'}")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
