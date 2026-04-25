#!/usr/bin/env python3
"""Experiment: LLM (Gemini) vs Heuristic-only dark-pattern detection.

Compares the keyword-heuristic dark-pattern detector against the LLM-validated
approach to measure false-positive suppression and overall quality.

Usage:
    set GOOGLE_API_KEY=your-key
    python scripts/exp_llm_comparison.py

Output:
    experiments/exp_llm/results.csv
    experiments/exp_llm/comparison_details.json
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

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_DIR = PROJECT_ROOT / "experiments" / "exp_llm"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"

# Rate limit: free tier has 5 RPM; need 60s+ between calls
LLM_DELAY_SECONDS = 65
MAX_RETRIES = 3


def load_fixture_text(driver, fixture_name: str) -> str:
    """Load a fixture HTML file and return visible text."""
    fixture_path = FIXTURES_DIR / fixture_name
    driver.get(f"file:///{fixture_path.as_posix()}")
    time.sleep(1)
    return driver.execute_script(
        "return document.body ? document.body.innerText : '';"
    )


def run_heuristic_audit(text: str) -> dict:
    """Run heuristic-only dark-pattern detection."""
    from design_assistant.audits.dark_patterns import DarkPatternAuditor
    auditor = DarkPatternAuditor()
    report = auditor.audit(text)
    return {
        "score": report.score,
        "flag_count": len(report.flags),
        "flags": [f.to_dict() for f in report.flags],
    }


def run_llm_validation(text: str, heuristic_flags: list, api_key: str) -> dict:
    """Run LLM validation on heuristic flags to suppress false positives."""
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("models/gemini-2.5-flash-lite")

    if not heuristic_flags:
        return {
            "score": 1.0,
            "confirmed_count": 0,
            "suppressed_count": 0,
            "confirmed_flags": [],
            "suppressed_flags": [],
            "llm_raw": "No flags to validate.",
        }

    # Build validation prompt
    flags_text = "\n".join([
        f"  {i+1}. [{f['label']}] (confidence={f['score']:.2f}): \"{f['text'][:200]}\""
        for i, f in enumerate(heuristic_flags)
    ])

    prompt = f"""You are an independent UX ethics auditor. A heuristic detector has flagged the following text segments as potential dark patterns on a webpage.

Your task: For EACH flagged segment, determine whether it is a GENUINE dark pattern or a FALSE POSITIVE (benign persuasion, standard UI copy, or informational text).

Flagged segments:
{flags_text}

For each segment, respond with:
- "CONFIRMED" if it is genuinely manipulative (pressures, tricks, or misleads users)
- "FALSE_POSITIVE" if it is benign, informational, or standard UI practice

Respond in strict JSON format:
{{
  "validations": [
    {{
      "index": 1,
      "verdict": "CONFIRMED" or "FALSE_POSITIVE",
      "reasoning": "brief explanation"
    }}
  ]
}}

Only emit JSON, no other text."""

    import re
    generation_config = {"temperature": 0.2, "max_output_tokens": 2000}

    # Retry loop for rate limiting
    raw_text = None
    for attempt in range(MAX_RETRIES):
        try:
            response = model.generate_content(prompt, generation_config=generation_config)
            raw_text = (response.text or "").strip()
            break  # Success
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                wait = 30 * (attempt + 1)  # 30s, 60s, 90s
                print(f"    Rate limited (attempt {attempt+1}/{MAX_RETRIES}), waiting {wait}s...")
                time.sleep(wait)
            else:
                return {
                    "score": None, "error": err_str,
                    "confirmed_count": 0, "suppressed_count": 0,
                    "confirmed_flags": [], "suppressed_flags": [],
                    "llm_raw": err_str,
                }

    if raw_text is None:
        return {
            "score": None, "error": "All retries exhausted",
            "confirmed_count": 0, "suppressed_count": 0,
            "confirmed_flags": [], "suppressed_flags": [],
            "llm_raw": "Rate limit exceeded after all retries.",
        }

    try:
        # Parse JSON response
        cleaned = raw_text
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()

        parsed = json.loads(cleaned)
        validations = parsed.get("validations", [])

        confirmed = []
        suppressed = []
        for v in validations:
            idx = v.get("index", 0) - 1
            if 0 <= idx < len(heuristic_flags):
                flag = heuristic_flags[idx].copy()
                flag["llm_verdict"] = v.get("verdict", "UNKNOWN")
                flag["llm_reasoning"] = v.get("reasoning", "")
                if v.get("verdict") == "CONFIRMED":
                    confirmed.append(flag)
                else:
                    suppressed.append(flag)

        # Recompute score with only confirmed patterns
        total_sentences = max(len(heuristic_flags), 1)
        confirmed_ratio = len(confirmed) / total_sentences
        llm_score = max(0.0, 1.0 - confirmed_ratio)

        return {
            "score": round(llm_score, 4),
            "confirmed_count": len(confirmed),
            "suppressed_count": len(suppressed),
            "confirmed_flags": confirmed,
            "suppressed_flags": suppressed,
            "llm_raw": raw_text[:1000],
        }

    except Exception as e:
        return {
            "score": None, "error": str(e),
            "confirmed_count": 0, "suppressed_count": 0,
            "confirmed_flags": [], "suppressed_flags": [],
            "llm_raw": str(e),
        }


def main():
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        # Try .env file
        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("GOOGLE_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()

    llm_available = bool(api_key) and api_key != "your-google-api-key"

    print("\n" + "="*60)
    print("  LLM vs HEURISTIC DARK-PATTERN COMPARISON")
    print(f"  LLM available: {llm_available}")
    print("="*60)

    fixtures = [
        ("good_page.html", "Good Page"),
        ("mixed_page.html", "Mixed Page"),
        ("bad_page.html", "Bad Page"),
        ("dark_pattern_heavy.html", "Dark-Heavy Page"),
    ]

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=opts)

    results = []
    all_details = []

    try:
        for fixture_file, display_name in fixtures:
            print(f"\n--- {display_name} ({fixture_file}) ---")

            # Get visible text
            text = load_fixture_text(driver, fixture_file)
            print(f"  Text length: {len(text)} chars")

            # Heuristic audit
            heuristic = run_heuristic_audit(text)
            print(f"  Heuristic: {heuristic['flag_count']} flags, score={heuristic['score']:.3f}")

            # LLM validation
            llm_result = {"score": None, "confirmed_count": 0, "suppressed_count": 0,
                          "confirmed_flags": [], "suppressed_flags": [], "llm_raw": "LLM not available"}
            if llm_available and heuristic["flag_count"] > 0:
                print(f"  Running LLM validation (waiting {LLM_DELAY_SECONDS}s for rate limit)...")
                time.sleep(LLM_DELAY_SECONDS)
                llm_result = run_llm_validation(text, heuristic["flags"], api_key)
                if llm_result.get("error"):
                    print(f"  LLM Error: {llm_result['error']}")
                else:
                    print(f"  LLM: {llm_result['confirmed_count']} confirmed, "
                          f"{llm_result['suppressed_count']} suppressed, "
                          f"score={llm_result['score']:.3f}")
            elif not llm_available:
                print(f"  LLM not available — using heuristic-only results.")
            else:
                print(f"  No flags to validate with LLM.")
                llm_result["score"] = 1.0

            row = {
                "page": display_name,
                "heuristic_flags": heuristic["flag_count"],
                "heuristic_score": heuristic["score"],
                "llm_confirmed": llm_result["confirmed_count"],
                "llm_suppressed": llm_result["suppressed_count"],
                "llm_score": llm_result.get("score"),
                "false_positive_rate": (
                    round(llm_result["suppressed_count"] / max(heuristic["flag_count"], 1), 3)
                    if llm_result.get("score") is not None else None
                ),
            }
            results.append(row)
            all_details.append({
                "page": display_name,
                "heuristic": heuristic,
                "llm": llm_result,
            })

    finally:
        driver.quit()

    # Save CSV
    csv_path = OUTPUT_DIR / "results.csv"
    if results:
        keys = list(results[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for r in results:
                writer.writerow(r)

    # Save detailed JSON
    details_path = OUTPUT_DIR / "comparison_details.json"
    with open(details_path, "w", encoding="utf-8") as f:
        json.dump(all_details, f, indent=2, default=str)

    # Print summary
    print(f"\n{'='*60}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"{'Page':<20} {'Heur.Flags':>11} {'Heur.Score':>11} {'LLM.Conf':>9} "
          f"{'LLM.Supp':>9} {'LLM.Score':>10} {'FP Rate':>8}")
    print("-" * 78)
    for r in results:
        llm_score_str = f"{r['llm_score']:.3f}" if r['llm_score'] is not None else "N/A"
        fp_str = f"{r['false_positive_rate']:.1%}" if r['false_positive_rate'] is not None else "N/A"
        print(f"{r['page']:<20} {r['heuristic_flags']:>11} {r['heuristic_score']:>11.3f} "
              f"{r['llm_confirmed']:>9} {r['llm_suppressed']:>9} {llm_score_str:>10} {fp_str:>8}")

    print(f"\nCSV: {csv_path}")
    print(f"Details: {details_path}")


if __name__ == "__main__":
    main()
