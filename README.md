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

## AI-Enhanced Analysis with Google Gemini (Optional)

The Design Assistant integrates with Google's Gemini AI models to provide advanced multimodal analysis, combining visual understanding (screenshot analysis) with code analysis (HTML/DOM inspection) for comprehensive design insights.

### Benefits of LLM Integration

- **Multimodal Analysis**: Gemini analyzes both the visual screenshot AND the HTML structure simultaneously
- **Visual Understanding**: AI identifies design issues by actually "seeing" the interface like a user would
- **Contextual Explanations**: Provides nuanced explanations of how violations affect real users
- **Prioritized Recommendations**: Suggests action plans based on severity, impact, and user experience
- **Enhanced Insights**: Combines automated metrics with AI reasoning for comprehensive reports
- **User Impact Assessment**: Explains accessibility and fairness issues from the user's perspective
- **Cost-Effective**: Generous free tier with 1,500 requests/day for Gemini 2.5 Flash

### Setup Instructions

1. **Install Google Generative AI Package**:

   The package is included in `requirements.txt`, but if you need to install it separately:
   ```bash
   pip install google-generativeai
   ```

2. **Get a Google AI API Key**:
   - Visit [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
   - Sign in with your Google account
   - Click "Create API Key"
   - Copy your API key

3. **Set the API key as an environment variable** (recommended):

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

4. **Enable in Streamlit Dashboard**:
   - Launch the app: `streamlit run app.py`
   - In the sidebar, check "Enable Gemini Analysis"
   - Enter your API key (or leave empty if already set as env variable)
   - Select your preferred model:
     - **models/gemini-2.5-pro** (recommended for best quality multimodal analysis)
     - **models/gemini-2.5-flash** (faster, still excellent quality)
     - **models/gemini-2.0-flash-exp** (experimental features)
     - **models/gemini-flash-latest** (always uses latest stable flash model)
   - Configure temperature (0.0-1.0) and max tokens as desired
   - Run audits as normal - reports will now include AI-powered comprehensive insights

### How It Works

When Gemini analysis is enabled, the system:

1. **Captures Visual + Code Data**: Takes a screenshot AND extracts the HTML DOM
2. **Runs Automated Audits**: Computes accessibility scores, contrast metrics, and dark pattern detection
3. **Sends to Gemini**: Provides both the screenshot image and HTML code to Gemini for analysis
4. **Receives AI Insights**: Gemini analyzes the visual design AND code structure simultaneously
5. **Combines Results**: Integrates automated metrics with AI-powered contextual analysis in the report

The multimodal approach allows Gemini to identify issues that pure automation might miss, such as:
- Visual hierarchy problems visible in screenshots but not in HTML
- Color contrast issues in context of the overall design
- Dark patterns that rely on visual deception
- User experience issues requiring visual understanding

**Tips to optimize usage**:
- Use **Gemini 2.5 Pro** (default) for best quality - 50 free requests/day is typically sufficient
- Use **Gemini 2.5 Flash** for higher volume needs - 1,500 free requests/day
- Free tier is usually more than enough for development and small-scale auditing
- Multimodal analysis (image + text) provides significantly better insights than text-only

### Verifying Your Setup

To verify that Gemini is properly configured, run this test in your terminal:

**PowerShell:**
```powershell
python -c "import google.generativeai as genai; import os; genai.configure(api_key=os.getenv('GOOGLE_API_KEY')); print('✓ Gemini SDK installed'); print('✓ API key configured' if os.getenv('GOOGLE_API_KEY') else '✗ API key not found'); models = genai.list_models(); print(f'✓ Found {len([m for m in models if \"generateContent\" in m.supported_generation_methods])} available models')"
```

**WSL/Bash:**
```bash
python -c "import google.generativeai as genai; import os; genai.configure(api_key=os.getenv('GOOGLE_API_KEY')); print('✓ Gemini SDK installed'); print('✓ API key configured' if os.getenv('GOOGLE_API_KEY') else '✗ API key not found'); models = genai.list_models(); print(f'✓ Found {len([m for m in models if \"generateContent\" in m.supported_generation_methods])} available models')"
```

Expected output:
```
✓ Gemini SDK installed
✓ API key configured
✓ Found 40+ available models
```

### Troubleshooting

**"ModuleNotFoundError: No module named 'google.generativeai'"**
- Solution: Install the package: `pip install google-generativeai`
- Make sure you're in the correct virtual environment

**"LLM analyzer available: False" in debug output**
- Check that `GOOGLE_API_KEY` environment variable is set
- Verify the API key is valid at [aistudio.google.com](https://aistudio.google.com)
- Restart your terminal/PowerShell after setting environment variables

**"404 model not found" errors**
- Use the correct model name format with `models/` prefix: `models/gemini-2.5-pro`
- Check available models with the verification command above
- Ensure your API key has access to the requested model

**"No Gemini analysis in report"**
- Enable "Enable Gemini Analysis" checkbox in Streamlit sidebar
- Check console output for DEBUG messages showing LLM initialization
- Verify the audit completed successfully and generated artifacts

### Custom Prompts (Advanced)

You can customize the analysis prompts by modifying `design_assistant/llm_integration.py`:

```python
llm_config = LLMConfig(
    api_key="your-api-key",
    model="models/gemini-2.5-pro",
    temperature=0.3,
    max_tokens=2000
)

# The prompts are in the analyze_comprehensive() method
# Modify the content variable to customize what Gemini analyzes
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
