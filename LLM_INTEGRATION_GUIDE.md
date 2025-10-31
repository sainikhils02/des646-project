# LLM Integration Implementation Guide

## Overview

The AI-Powered Design Assistant now includes **Google Gemini 2.0 Flash integration** to enhance audit reports with AI-powered natural language analysis. This combines automated rule-based audits with intelligent contextual insights from Google's Gemini 2.0 Flash model.

## What's New

### 1. LLM Integration Module (`design_assistant/llm_integration.py`)

A comprehensive module providing GPT-4o integration with:

- **LLMConfig**: Configuration dataclass with customizable settings
  - `api_key`: Google AI API key (auto-loads from `GOOGLE_API_KEY` env variable)
  - `model`: Model selection (default: `gemini-2.0-flash-exp`, supports `gemini-1.5-pro`, `gemini-1.5-flash`)
  - `temperature`: Creativity control (0.0-2.0, default: 0.7)
  - `max_tokens`: Response length limit (default: 4000)
  - `custom_prompt_template`: Optional prompt overrides

- **LLMAnalyzer**: Core analysis engine with four specialized methods:
  - `analyze_accessibility()`: Analyzes WCAG violations with user impact explanations
  - `analyze_contrast()`: Evaluates contrast issues with visual design recommendations
  - `analyze_dark_patterns()`: Ethical assessment of manipulative design patterns
  - `generate_recommendations()`: Prioritized action plan based on all findings

### 2. Enhanced Report Generation

#### Updated `design_assistant/llm_reporter.py`

- Now accepts `LLMConfig` in constructor
- Automatically integrates LLM analysis into each report section
- Falls back gracefully to rule-based reporting if LLM is unavailable
- Merges AI insights with automated metrics for comprehensive analysis

**New Report Structure**:
```
## Section (e.g., Accessibility Analysis)
**Scores and metrics** (rule-based)

### AI-Powered Analysis
[Gemini 2.0 Flash contextual insights]

### Violations Breakdown
[Automated audit data]
```

#### Updated Report Writers

- **MarkdownReportWriter**: Accepts `llm_config` parameter
- **PDFReportWriter**: Accepts `llm_config` parameter
- Both pass configuration to `LLMReportGenerator`

### 3. Pipeline Integration (`design_assistant/pipeline.py`)

- `DesignAssistant` constructor now accepts `llm_config` parameter
- Automatically propagates LLM configuration to all report writers
- Zero changes needed to existing audit logic

### 4. Streamlit Dashboard Enhancement (`app.py`)

New sidebar section: **🤖 AI Enhancement (Optional)**

**Features**:
- Checkbox to enable/disable Gemini 2.0 Flash analysis
- API key input (password field, reads from environment variable)
- Model selection dropdown (gemini-2.0-flash-exp, gemini-1.5-pro, gemini-1.5-flash)
- Temperature slider (creativity control, 0.0-2.0)
- Max tokens input (response length)
- Real-time configuration status indicators

**User Experience**:
- Graceful degradation if API key missing
- Free tier information and usage tips
- Clear status indicators (✅ enabled, ⚠️ missing key)

### 5. Documentation Updates

#### README.md

New section: **AI-Enhanced Analysis with Gemini 2.0 Flash (Optional)**

Includes:
- Benefits overview (including free tier)
- Step-by-step setup instructions (PowerShell and WSL/Bash)
- API key acquisition guide
- Free tier details and paid pricing
- Custom prompt configuration examples

#### requirements.txt

- Added `google-generativeai>=0.3.0` dependency

## How It Works

### Without LLM (Default Behavior)

1. Run automated audits (accessibility, contrast, dark patterns)
2. Generate rule-based reports using templates
3. Export JSON/PDF/Markdown with metrics and standard explanations

### With LLM Enabled

1. Run automated audits (same as before)
2. **For each report section**:
   - Prepare audit data (violations, scores, flags)
   - Send to Gemini 2.0 Flash with specialized prompt
   - Receive contextual analysis and recommendations
   - Merge AI insights with rule-based content
3. Export enhanced reports with both automated metrics and AI explanations

### Example LLM Prompts

**Accessibility Analysis**:
```
You are an accessibility expert. Analyze these WCAG violations:
[violation data]

Current score: 0.65

Provide:
1. Root cause analysis
2. User impact explanation
3. Prioritization guidance
```

**Recommendations Generation**:
```
You are a UX consultant. Given this audit summary:
- Accessibility: 12 violations
- Contrast: Avg 3.8:1
- Dark patterns: 3 detected

Generate a prioritized action plan with:
1. Quick wins (1-2 weeks)
2. Medium-term improvements
3. Long-term strategy
```

## Configuration Examples

### Basic Usage (Environment Variable)

```bash
# Set API key once
export GOOGLE_API_KEY="your-api-key"

# Run app - LLM will auto-enable if checkbox selected
streamlit run app.py
```

### Programmatic Usage

```python
from design_assistant.llm_integration import LLMConfig
from design_assistant.pipeline import DesignAssistant

# Configure LLM
llm_config = LLMConfig(
    api_key="your-api-key",
    model="gemini-2.0-flash-exp",
    temperature=0.7,
    max_tokens=4000
)

# Create assistant with LLM
assistant = DesignAssistant(llm_config=llm_config)

# Run audit - reports will include AI analysis
result = assistant.run(InputMode.URL, "https://example.com")
```

### Custom Prompts

```python
llm_config = LLMConfig(
    api_key="your-api-key",
    model="gemini-2.0-flash-exp",
    custom_prompt_template="""
    As a WCAG expert, analyze these violations focusing on:
    - Legal compliance risks
    - Remediation complexity
    - User impact severity
    
    Violations: {violations}
    Score: {score}
    """
)
```

## Cost Management

### Free Tier Limits

| Model | Free Requests/Day | Paid Cost (if exceeded) |
|-------|-------------------|-------------------------|
| Gemini 2.0 Flash | 1,500 | $0.075/1M in, $0.30/1M out |
| Gemini 1.5 Flash | 1,500 | $0.075/1M in, $0.30/1M out |
| Gemini 1.5 Pro | 50 | $1.25/1M in, $5/1M out |

### Usage Tips

1. **Free tier is generous**: 1,500 audits/day covers most use cases
2. **Gemini 2.0 Flash recommended**: Best performance, same free tier as 1.5 Flash
3. **No cost optimization needed**: Unless running thousands of audits daily
4. **Paid tier is affordable**: Even if exceeded, costs are ~$0.0003-$0.001 per audit

## Error Handling

The integration includes comprehensive error handling:

- **Missing API key**: Falls back to rule-based reporting, prints warning
- **Invalid API key**: Catches authentication errors, continues with templates
- **Rate limits**: Google AI SDK handles automatic retries with backoff
- **Timeout**: Configurable timeout, falls back gracefully
- **Import errors**: If `google-generativeai` package missing, LLM features disabled but app works

## Testing Without API Key

You can test the entire pipeline without LLM:

```bash
# Don't set GOOGLE_API_KEY
streamlit run app.py

# Uncheck "Enable Gemini 2.0 Flash Analysis" in sidebar
# Reports will use rule-based generation only
```

## Architecture Benefits

1. **Modular Design**: LLM integration is completely optional
2. **Backward Compatible**: Existing code works without changes
3. **Graceful Degradation**: Missing API key doesn't break functionality
4. **Extensible**: Easy to add new analysis methods or custom prompts
5. **Model Agnostic**: Can switch between OpenAI models easily

## Future Enhancements

Potential improvements:

- Support for other LLM providers (Anthropic Claude, OpenAI)
- Caching of LLM responses to reduce API calls
- A/B testing rule-based vs LLM-enhanced reports
- Fine-tuned Gemini models specifically for accessibility analysis
- Batch analysis of multiple pages with comparative insights
- User feedback loop to improve prompts
- Image analysis using Gemini's multimodal capabilities

## Quick Reference

### Enable LLM (Streamlit UI)
1. Check "Enable Gemini 2.0 Flash Analysis" in sidebar
2. Enter API key or set `GOOGLE_API_KEY` env variable
3. Configure model and parameters
4. Run audit normally

### Enable LLM (Python API)
```python
from design_assistant.llm_integration import LLMConfig

llm_config = LLMConfig(api_key="your-api-key")
assistant = DesignAssistant(llm_config=llm_config)
```

### Disable LLM
- Streamlit: Uncheck the checkbox
- Python: Pass `llm_config=None` or omit parameter

### Check if LLM is Active
- Streamlit: Look for "✅ LLM enabled" in sidebar
- Reports: Look for "AI-Powered Analysis" sections

## Support

For issues or questions:
1. Check that `google-generativeai` package is installed: `pip install google-generativeai>=0.3.0`
2. Verify API key is valid: `echo $GOOGLE_API_KEY` (Unix) or `$env:GOOGLE_API_KEY` (PowerShell)
3. Get API key at: https://aistudio.google.com/apikey
4. Review error messages in terminal/console
