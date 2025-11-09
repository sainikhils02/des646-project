# AI-Powered Design Assistant

The **AI-Powered Design Assistant** is a comprehensive tool designed to evaluate digital designs for **fairness**, **accessibility**, and **ethical user experience**. Built with **Python** and **Streamlit**, it performs automated audits on either live web pages (via URL) or uploaded screenshots, generating a holistic **Design Fairness Score** that reflects accessibility compliance, visual contrast, and ethical UX patterns.

---

## 🚀 Key Features

- **Multi-Modal Input:** Analyze designs from a live **URL** or a **screenshot** (PNG/JPG).
- **Accessibility Auditing:** Performs WCAG compliance checks using the `axe-core` engine through Selenium.
- **Contrast Analysis:** Uses OpenCV-based heuristics to detect low-contrast text and UI regions.
- **Ethical UX Scoring:** Identifies manipulative “dark patterns” using a Transformer-based NLP model (Hugging Face or custom fine-tuned).
- **AI-Enhanced Analysis:** Optionally integrates **Google Gemini** for multimodal validation and natural-language audit insights.
- **Interactive Dashboard:** Streamlit interface with Plotly visualizations for real-time exploration of audit results and trends.
- **Comprehensive Reporting:** Generates structured reports in **Markdown**, **PDF**, and **JSON** formats.
- **Audit History:** Saves all audits for historical analysis, comparison, and progress tracking.
- **Configurable Pipeline:** Modular architecture allows customization of thresholds and scoring weights.

---

## 🧠 Technology Stack

| Layer | Tools & Libraries |
|-------|-------------------|
| **Frontend** | Streamlit, Plotly |
| **Auditing** | Selenium, axe-core, OpenCV |
| **AI/NLP** | Google Gemini (optional), Hugging Face Transformers |
| **Reporting** | Markdown, ReportLab (PDF), JSON |
| **Language** | Python 3.8+ |

---

## ⚙️ Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/sainikhils02/des646-project.git
cd des646-project
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate    # macOS/Linux
# venv\Scripts\activate     # Windows
```

### 3. Install dependencies
If you already have a `requirements.txt` file:
```bash
pip install -r requirements.txt
```

If not, create one with:
```
streamlit
pandas
plotly
axe-selenium-python
opencv-python
transformers
reportlab
selenium
```

Then run:
```bash
pip install -r requirements.txt
```

### 4. (Optional) Enable Gemini AI Integration
To enable Google Gemini-based AI analysis:

1. Get an API key from [Google AI Studio](https://aistudio.google.com/apikey)
2. Set it as an environment variable:

```bash
# macOS/Linux
export GOOGLE_API_KEY="YOUR_API_KEY"

# Windows PowerShell
$env:GOOGLE_API_KEY="YOUR_API_KEY"
```

---

## 💻 Running the Application

### Option 1 – Streamlit Dashboard
```bash
streamlit run app.py
```

This opens the interactive web UI in your browser.

**Dashboard sections:**
1. **Home** – Overview of the tool’s features.  
2. **Audit** – Input URL or screenshot, adjust weights, and run the audit.  
3. **Reports** – Visual summaries (radar/gauge charts, tables, scores).  
4. **History** – Explore or delete past audits.  
5. **About** – Details on methods and technologies used.

### Option 2 – Command-Line Interface
Run directly from CLI:
```bash
python -m design_assistant <mode> <value> [--output-dir <path>]
```

**Examples:**
```bash
python -m design_assistant url https://example.com --output-dir audits/
python -m design_assistant screenshot ./design.png
```

---

## 🧩 Project Structure

```
des646-project/
│
├── app.py                          # Streamlit app entry point
├── design_assistant/
│   ├── pipeline.py                 # Core orchestration logic
│   ├── fusion.py                   # Score computation logic
│   ├── reporting.py                # JSON / MD / PDF writers
│   ├── llm_integration.py          # Gemini model integration
│   ├── audits/
│   │   ├── accessibility.py        # axe-core wrapper
│   │   ├── contrast.py             # OpenCV contrast analysis
│   │   ├── dark_patterns.py        # NLP-based dark pattern detection
│   ├── collectors/
│   │   ├── selenium_collector.py   # DOM + Screenshot from URLs
│   │   ├── screenshot_loader.py    # Local image ingestion
│   └── ...
├── outputs/                        # Generated reports and JSONs
├── scripts/
│   └── fine_tune_dark_patterns.py  # Model fine-tuning utility
└── requirements.txt
```

---

## 🧪 Fine-Tuning the Dark Pattern Model

You can fine-tune your own Transformer-based model for dark pattern classification:

```bash
python scripts/fine_tune_dark_patterns.py   /path/to/train.csv   /path/to/val.csv   --model "distilbert-base-uncased"   --output-dir "custom-dark-pattern-model"
```

The CSVs must include:
- `text` — UI text content
- `label` — dark pattern category (e.g., *Urgency*, *Confirm-shaming*)

Once trained, you can plug the model into the pipeline via the `DarkPatternAuditor`.

---

## ⚙️ Configuration Options

| Config Area | Description |
|--------------|--------------|
| **Environment Variables** | API keys, service credentials, etc. |
| **Audit Thresholds** | WCAG contrast ratios, dark-pattern confidence cutoffs |
| **Weight Parameters** | α (Accessibility) and β (Ethical UX) coefficients |
| **Reports** | Output format and save directory |
| **Session Persistence** | Enables saving historical audits to local storage |

---

## 🤝 Contributing

We welcome contributions to improve this tool!  
To contribute:

1. Fork this repository  
2. Create a new feature branch  
3. Commit your changes with clear messages  
4. Submit a Pull Request to `main`

**Guidelines:**
- Follow existing code style  
- Add comments for complex logic  
- Test thoroughly before submitting  

---

## 📚 Acknowledgments

- [Streamlit](https://streamlit.io/) – Web framework  
- [axe-core](https://www.deque.com/axe/) – Accessibility engine  
- [Plotly](https://plotly.com/) – Data visualization  
- [Google Gemini](https://aistudio.google.com/) – Multimodal AI model  
- [Hugging Face Transformers](https://huggingface.co/) – NLP models  
- [OpenCV](https://opencv.org/) – Image processing  
- [ReportLab](https://www.reportlab.com/) – PDF generation  

---

## 📈 Future Work & TRL Roadmap

Our current implementation demonstrates a **functional prototype (TRL-4)**, validated as a proof of concept through live audits and reporting.  
To progress to **TRL-5**, we aim for systematic validation in simulated environments and acceptance testing.  
Further progress to **TRL-6+** will involve extended trials, deployment in production environments, and collaboration with UX and accessibility experts for real-world validation.
