# Unified AI-Assisted Framework for Design Fairness Evaluation

A unified framework for evaluating **design fairness** in digital interfaces, combining accessibility compliance, perceptual contrast analysis, ethical dark-pattern detection, and agent-based interaction simulation into a single hierarchical **Design Fairness Score (DFS)**.


## Architecture

```
                              ┌────────────────────────────────┐
                              │  Accessibility Auditor         │
                              │  (axe-core WCAG 2.1)          │
                              ├────────────────────────────────┤
URL / Screenshot ──→ Collect ─┤  Contrast Auditor              │
                              │  (KMeans-CIELAB + Laplacian)   │──→ Fusion ──→ Remediation ──→ Reports
                              ├────────────────────────────────┤     (DFS)      Engine          (PDF/MD/JSON)
                              │  Dark-Pattern Detector          │
                              │  (7 Mathur categories + LLM)   │
                              ├────────────────────────────────┤
                              │  Agentic Auditor               │
                              │  (Keyboard sim + SR walker)    │
                              └────────────────────────────────┘
```

**Design Fairness Score (DFS)** — hierarchical 3-tier formula:
```
DFS = α · Technical + β · Ethical + (1-α-β) · Perceptual

  Technical  = 0.5 · Accessibility + 0.25 · Keyboard + 0.25 · ScreenReader
  Perceptual = Contrast score
  Ethical    = Dark-pattern score

Gating: if Technical < 0.3, DFS is scaled down by Technical/0.3
```
Default weights: α=0.4, β=0.3. All configurable via the Streamlit dashboard.

**Weight rationale:** α=0.4 gives technical accessibility the largest share because WCAG conformance is a legal requirement (ADA Section 508, EU Directive 2016/2102). β=0.3 for ethics reflects that manipulative patterns erode user autonomy. Perceptual takes the remainder (0.3) as contrast affects comfort rather than capability.

---

## Features

| Module | Description |
|--------|-------------|
| **Accessibility Auditor** | WCAG 2.1 compliance checks via axe-core engine (injected into Selenium) |
| **Contrast Auditor** | Dual-method: Laplacian edge detection + KMeans-CIELAB colour segmentation with WCAG ratio computation |
| **Dark-Pattern Detector** | 79 keywords across 7 Mathur et al. taxonomy categories; optional Gemini LLM validation pass |
| **Agentic Auditor** | Simulates keyboard-only Tab navigation (focus indicators, skip-links, traps) + screen-reader ARIA tree traversal (landmarks, headings, alt, labels) |
| **Hierarchical DFS** | 3-tier scoring with gating mechanism that penalises critically inaccessible interfaces |
| **Predictive Remediation** | Generates HTML/CSS/ARIA code patches with per-tier impact estimates (Δ_technical, Δ_perceptual, Δ_ethical) |
| **Streamlit Dashboard** | Interactive UI with radar charts, tier gauges, issue tables, remediation suggestions, and downloadable reports |

---

## Installation

### Prerequisites
- **Python 3.10+**
- **Google Chrome** (for Selenium-based auditing and agentic simulation)
- **ChromeDriver** (auto-installed by `webdriver-manager`)

### Step 1: Clone and install
```bash
git clone https://github.com/sainikhils02/des646-project.git
cd des646-project
python -m venv venv
source venv/bin/activate    # macOS/Linux
# venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### Step 2 (Optional): Enable Google Gemini LLM
The framework works fully without an API key (all modules have rule-based fallbacks). To enable LLM-powered dark-pattern validation and remediation code generation:
```bash
# Get a key from https://aistudio.google.com/apikey
export GOOGLE_API_KEY="your-api-key-here"          # macOS/Linux 
# $env:GOOGLE_API_KEY="your-api-key-here"          # Windows PowerShell
```

Or set it in the `.env` file:
```
GOOGLE_API_KEY=your-api-key-here
```

---

## Usage

### Option 1: Streamlit Dashboard (recommended)
```bash
streamlit run app.py
```
This opens an interactive web UI at `http://localhost:8501` where you can:
- **Enter a URL** or **upload a screenshot** to audit
- **Adjust weights** (α, β) via sliders to see how DFS changes
- **View 3-tier DFS breakdown** with gauge charts (Technical / Perceptual / Ethical)
- **Browse agentic findings**: keyboard issues (focus indicators, skip-links, traps), screen-reader issues (landmarks, headings, ARIA)
- **See remediation suggestions**: before/after code patches with per-tier impact vectors
- **Download reports** in PDF, Markdown, and JSON formats

### Option 2: Command-Line Interface
```bash
# Audit a live URL (runs all 4 auditors + fusion + remediation)
python -m design_assistant url https://example.com --output-dir outputs/

# Audit a local screenshot
python -m design_assistant screenshot ./design.png --output-dir outputs/
```
This generates `audit.json`, `audit.pdf`, and `audit_report.md` in the output directory.

### Option 3: End-to-End Demo on Real URL
```bash
# Runs the full 6-step pipeline on https://example.com and prints detailed results
python scripts/demo_real_url.py
```

---

## Running Experiments (ICoRD'27 Paper)

The experiment suite validates all claims made in the paper. Benchmark experiments run on local HTML fixtures for reproducibility. Real-world and LLM experiments require internet access and (optionally) a Gemini API key.

### Run all benchmark experiments (no internet needed)
```bash
python scripts/run_experiments.py --output-dir experiments/
```

### Run individual benchmark experiments
```bash
python scripts/run_experiments.py --experiment agentic       # Exp1: Agentic vs Static
python scripts/run_experiments.py --experiment sensitivity    # Exp2: DFS Weight Sensitivity
python scripts/run_experiments.py --experiment contrast       # Exp3: Contrast Methods
python scripts/run_experiments.py --experiment darkpattern    # Exp4: Dark Pattern Accuracy
python scripts/run_experiments.py --experiment ablation       # Exp5: Component Ablation
python scripts/run_experiments.py --experiment remediation    # Exp7: Remediation Quality
```

### Run inter-pillar correlation analysis (Exp 6)
```bash
python scripts/generate_paper_figures.py
```
This generates the correlation matrix and 5 publication-quality figures in `figures/`.

### Run real-world validation on 5 production sites
```bash
python scripts/exp_realworld_validation.py
```
Audits: example.com, wikipedia.org, w3.org/WAI, iitk.ac.in, python.org

### Run LLM vs heuristic dark-pattern comparison
```bash
# Requires GOOGLE_API_KEY environment variable
$env:GOOGLE_API_KEY="your-key"                    # Windows PowerShell
python scripts/exp_llm_comparison.py
```

### Experiment Results Summary

| # | Experiment | Data Points | Key Finding |
|---|-----------|------------|-------------|
| 1 | Agentic vs Static | 4 pages | Agentic found **25–44% additional issues** beyond static tools |
| 2 | DFS Sensitivity | 45 configs | Score spread up to **0.315** across weight configs |
| 3 | Contrast Methods | 4 pages | KMeans-CIELAB: **24 violations** vs Laplacian: **0** |
| 4 | Dark Pattern Accuracy | 4 pages | **100% precision**, **98.6% text recall** |
| 5 | Component Ablation | 32 configs | All 3 DFS tiers contribute non-redundant signal |
| 6 | Inter-Pillar Correlation | 315 points | All \|r\| ≤ 0.48 — tiers measure distinct quality dimensions |
| 7 | Remediation Quality | 4 pages | **92.2% fix coverage**, avg DFS improvement **+0.475** |
| 8 | LLM vs Heuristic | 4 pages | LLM suppresses **44% false positives**, confirms **93% genuine** dark patterns |

### Real-World Validation Results

| Site | DFS | Technical | Ethical | Issues | Agentic Issues |
|------|-----|-----------|---------|--------|----------------|
| example.com | 0.673 | 0.933 | 1.000 | 7 | 3 |
| wikipedia.org | 0.598 | 0.733 | 1.000 | 10 | 7 |
| w3.org/WAI | 0.687 | 0.967 | 1.000 | 8 | 2 |
| iitk.ac.in | 0.593 | 0.733 | 1.000 | 13 | 7 |
| python.org | 0.624 | 0.850 | 0.938 | 9 | 5 |
| **Mean** | **0.635** | 0.843 | 0.988 | 9.4 | **4.8** |

Results are saved as CSV files in the `experiments/` directory.

---

## Generated Figures

The `scripts/generate_paper_figures.py` script generates publication-quality figures in `figures/`:

| Figure | File | Description |
|--------|------|-------------|
| DFS Radar Chart | `radar_dfs_breakdown.pdf` | Component scores per benchmark page |
| Sensitivity Heatmap | `heatmap_dfs_sensitivity.pdf` | DFS across α×β weight space for 3 site profiles |
| Agentic vs Static | `bar_agentic_vs_static.pdf` | Stacked bar showing agentic contribution |
| Correlation Matrix | `correlation_matrix.pdf` | Inter-pillar Pearson correlation (proves non-redundancy) |
| Remediation Impact | `bar_remediation_impact.pdf` | Current vs predicted post-fix DFS |

---

## Running Tests
```bash
# Run all 16 unit tests
python -m pytest tests/ -v

# Run specific test files
python -m pytest tests/test_fusion.py -v        # DFS hierarchical scoring
python -m pytest tests/test_contrast.py -v      # Contrast auditor (both methods)
python -m pytest tests/test_remediation.py -v   # Remediation engine
```

---

## Project Structure

```
des646-project/
├── app.py                              # Streamlit dashboard entry point
├── paper.tex                           # ICoRD'27 research paper (LaTeX, Springer LNCS)
├── requirements.txt                    # Python dependencies
├── .env                                # Environment variables (API keys)
│
├── design_assistant/                   # Core framework package
│   ├── __init__.py
│   ├── __main__.py                     # CLI entry point
│   ├── pipeline.py                     # Orchestration: collect → audit → fuse → remediate → report
│   ├── fusion.py                       # Hierarchical DFS (3-tier + gating)
│   ├── remediation.py                  # Predictive remediation (LLM + rule-based fallback)
│   ├── reporting.py                    # PDF / Markdown / JSON report writers
│   ├── llm_integration.py             # Google Gemini multimodal integration
│   │
│   ├── audits/                         # Four audit modules
│   │   ├── accessibility.py           # axe-core WCAG 2.1 wrapper
│   │   ├── contrast.py                # Laplacian + KMeans-CIELAB contrast analysis
│   │   ├── dark_patterns.py           # 7-category dark pattern detector (79 keywords)
│   │   └── agentic.py                 # Keyboard + screen-reader simulation (685 lines)
│   │
│   └── collectors/                     # Data collection
│       ├── selenium_collector.py      # Selenium URL crawler (DOM + screenshot + axe)
│       └── screenshot_loader.py       # Local image loader
│
├── scripts/
│   ├── run_experiments.py             # 6-experiment ICoRD evaluation suite
│   ├── generate_paper_figures.py      # Generate 5 publication-quality figures
│   ├── exp_realworld_validation.py    # Real-world validation on 5 production sites
│   ├── exp_llm_comparison.py          # LLM vs heuristic dark-pattern comparison
│   ├── demo_real_url.py              # End-to-end demo on a real URL
│   └── check_latex.py                # LaTeX environment balance checker
│
├── tests/
│   ├── fixtures/                      # 4 benchmark HTML pages
│   │   ├── good_page.html            # WCAG-compliant reference
│   │   ├── mixed_page.html           # Partially compliant
│   │   ├── bad_page.html             # 20+ deliberate violations
│   │   └── dark_pattern_heavy.html   # All 7 Mathur categories
│   ├── test_contrast.py              # 5 tests (Laplacian + KMeans)
│   ├── test_fusion.py                # 7 tests (DFS hierarchy + gating)
│   └── test_remediation.py           # 4 tests (rules + serialization)
│
├── figures/                           # Generated publication figures (PDF + PNG)
│   ├── radar_dfs_breakdown.pdf
│   ├── heatmap_dfs_sensitivity.pdf
│   ├── bar_agentic_vs_static.pdf
│   ├── correlation_matrix.pdf
│   └── bar_remediation_impact.pdf
│
└── experiments/                       # Generated experiment results (CSV + JSON)
    ├── exp1/ ... exp6/               # Benchmark experiment results
    ├── exp_realworld/                # Real-world validation (5 sites)
    ├── exp_llm/                      # LLM comparison results
    └── demo_real_url/
```

---

## Quick Start: Reproduce All Paper Results

Run these commands in order to reproduce every experiment and figure in the paper:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run all 6 benchmark experiments (Exp 1-5, 7)
python scripts/run_experiments.py --output-dir experiments/

# 3. Generate figures and run correlation analysis (Exp 6)
python scripts/generate_paper_figures.py

# 4. Run real-world validation on 5 production sites
python scripts/exp_realworld_validation.py

# 5. (Optional) Run LLM comparison — requires Gemini API key
$env:GOOGLE_API_KEY="your-key"
python scripts/exp_llm_comparison.py

# 6. (Optional) Launch the Streamlit dashboard
streamlit run app.py
```

---

## Technology Stack

| Layer | Tools & Libraries |
|-------|-------------------|
| **Dashboard** | Streamlit 1.56, Plotly 6.x |
| **Web Auditing** | Selenium 4.x, axe-selenium-python, ChromeDriver |
| **Computer Vision** | OpenCV (KMeans-CIELAB segmentation), NumPy |
| **NLP / Heuristics** | Keyword matching (79 terms), HuggingFace Transformers (optional) |
| **AI Integration** | Google Gemini API (optional, rule-based fallbacks for all modules) |
| **Reporting** | ReportLab (PDF), Matplotlib (charts), Markdown, JSON |
| **Testing** | pytest 9.x |
| **Language** | Python 3.10+ |

---

## Team

Venkatesh Akula (220109), Venkata Sritan (220280), Sai Nikhil (221095), Tejasri Saladi (220941), Nayan Verma (220703)

**Indian Institute of Technology Kanpur** — DES646: AI in Design, 2024–25
