# AI-Powered Design Assistant

An end-to-end prototype that audits digital interfaces for accessibility, contrast compliance, and dark pattern risks. It follows the build guide specification provided in `AI-Powered Design Assistant.txt`.

## Features

- Accepts either a live URL (via Selenium) or a pre-captured screenshot.
- Runs axe-core driven accessibility checks when Selenium is available.
- Detects low-contrast regions with OpenCV heuristics.
- Flags potential dark patterns using a Hugging Face transformer (or keyword fallback).
- Aggregates subscores into an overall Design Fairness Score with adjustable weights.
- Generates JSON and PDF audit artifacts.
- Provides a Streamlit dashboard for interactive exploration.

## Project Structure

```
├── app.py                        # Streamlit UI
├── design_assistant/
│   ├── audits/                   # Accessibility, contrast, and dark pattern modules
│   ├── collectors/               # URL and screenshot ingestion utilities
│   ├── fusion.py                 # Score aggregation helpers
│   ├── pipeline.py               # High-level orchestration
│   ├── reporting.py              # JSON/PDF report writers
│   └── models/                   # Model utilities placeholder
├── tests/                        # Minimal unit tests
├── data/                         # Place datasets here (ignored by Git)
├── requirements.txt              # Python dependencies
└── README.md
```

## Getting Started

1. **Create and activate a virtual environment** (Python 3.10+):

   **PowerShell (Windows):**
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

   **WSL/Bash/Linux:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. **Install core dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Chrome setup**:
   - Install Google Chrome on Windows (recommended) - the collector will automatically find it.
   - Or manually set the Chrome binary path (see Browser setup tips below).

4. **Run the Streamlit dashboard**:

   ```bash
   streamlit run app.py
   ```

5. **Fine-tune the dark pattern classifier** (optional): follow the sample notebook or script in `notebooks/` (to be added) using datasets from Kaggle or Hugging Face.

### Browser setup tips (optional)

The collector automatically searches for Chrome in standard Windows locations. If Chrome isn't found, you can manually set the path:

**PowerShell (Windows):**
```powershell
$env:CHROME_BINARY = "C:\Program Files\Google\Chrome\Application\chrome.exe"
```

To make it permanent, add to your PowerShell profile:
```powershell
notepad $PROFILE
# Add: $env:CHROME_BINARY = "C:\Program Files\Google\Chrome\Application\chrome.exe"
```

**WSL/Bash:**
```bash
export CHROME_BINARY="/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
```

To make it permanent:
```bash
echo 'export CHROME_BINARY="/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"' >> ~/.bashrc
source ~/.bashrc
```

**Chromedriver:**
The app uses `webdriver-manager` to automatically download the matching Chromedriver. To use a specific driver:

- PowerShell: `$env:CHROMEDRIVER_PATH = "C:\path\to\chromedriver.exe"`
- WSL/Bash: `export CHROMEDRIVER_PATH="/path/to/chromedriver"`

## AI-Enhanced Analysis with Gemini 2.0 Flash (Optional)

The Design Assistant can integrate with Google's Gemini 2.0 Flash to provide enhanced natural language analysis, contextual explanations, and intelligent recommendations beyond rule-based reporting.

### Benefits of LLM Integration

- **Contextual Analysis**: AI provides nuanced explanations of how violations affect real users
- **Prioritized Recommendations**: Gemini suggests prioritized action plans based on severity and impact
- **Enhanced Insights**: Combines automated metrics with AI reasoning for comprehensive reports
- **User Impact Assessment**: Explains accessibility issues from the user's perspective
- **Cost-Effective**: Free tier includes 1,500 requests/day

### Setup Instructions

1. **Get a Google AI API Key**:
   - Visit [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
   - Sign in with your Google account
   - Click "Create API Key" 
   - Copy your API key

2. **Set the API key as an environment variable** (recommended):

   **PowerShell:**
   ```powershell
   $env:GOOGLE_API_KEY = "your-api-key-here"
   ```

   To make it permanent:
   ```powershell
   [System.Environment]::SetEnvironmentVariable('GOOGLE_API_KEY', 'your-api-key-here', 'User')
   ```

   **WSL/Bash:**
   ```bash
   export GOOGLE_API_KEY="your-api-key-here"
   ```

   To make it permanent:
   ```bash
   echo 'export GOOGLE_API_KEY="your-api-key-here"' >> ~/.bashrc
   source ~/.bashrc
   ```

3. **Enable in Streamlit Dashboard**:
   - Launch the app: `streamlit run app.py`
   - In the sidebar, check "Enable Gemini 2.0 Flash Analysis"
   - Enter your API key (or leave empty if already set as env variable)
   - Configure model, temperature, and max tokens as desired
   - Run audits as normal - reports will now include AI-powered insights

### Cost Considerations

✅ **Free Tier**: Google AI offers a generous free tier:
- **Gemini 2.0 Flash**: 1,500 requests/day (free)
- **Gemini 1.5 Flash**: 1,500 requests/day (free)
- **Gemini 1.5 Pro**: 50 requests/day (free)

A typical audit uses:
- 500-1,000 input tokens (audit data)
- 1,000-3,000 output tokens (analysis)
- Estimated cost: **FREE** for most users

**Paid pricing** (if exceeding free tier):
- **Gemini 2.0 Flash**: $0.075 per 1M input tokens, $0.30 per 1M output tokens
- **Gemini 1.5 Flash**: $0.075 per 1M input tokens, $0.30 per 1M output tokens
- **Gemini 1.5 Pro**: $1.25 per 1M input tokens, $5 per 1M output tokens

**Tips to stay within free tier**:
- Use Gemini 2.0 Flash (default) for best performance
- 1,500 audits/day is typically more than sufficient
- No cost optimization needed for most users

### Custom Prompts (Advanced)

You can customize the prompts sent to Gemini by modifying `design_assistant/llm_integration.py`:

```python
llm_config = LLMConfig(
    api_key="your-api-key",
    model="gemini-2.0-flash-exp",
    custom_prompt_template="Your custom analysis prompt..."
)
```

## Configuration Notes

- PDF generation requires `reportlab`; install `reportlab` on platforms where GUI-less PDF export is desired.
- OpenCV functions rely on `opencv-python` (or the headless variant in server environments).
- The transformer-based dark pattern detector defaults to `distilbert-base-uncased-finetuned-sst-2-english`. Replace `model_name_or_path` in `DarkPatternAuditor` with your fine-tuned checkpoint.
- LLM integration requires the `google-generativeai` package (installed via `requirements.txt`) and a valid Google AI API key.

## Testing

An illustrative unit test exists for the contrast auditor. Run the test suite via:

```bash
pytest
```

## Data Placement

Place training and evaluation datasets in the `data/` directory. Each audit invocation writes artifacts (DOM, screenshots, results) under `outputs/`.

## Next Steps

- Add notebooks or scripts for model fine-tuning and evaluation.
- Implement screenshot annotation overlays for contrast violations.
- Expand keyword heuristics and calibrate thresholds based on labelled datasets.
