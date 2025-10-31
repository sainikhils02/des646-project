# Multimodal Analysis Update

## Summary of Changes

The AI-Powered Design Assistant now uses **multimodal analysis** with Google Gemini 1.5 Pro, sending actual screenshots and HTML content for comprehensive AI-powered review.

## What Changed

### 1. Multimodal Input Analysis

**Before**: Only sent computed metrics (scores, violation counts) to LLM
**Now**: Sends actual files for AI analysis:
- ✅ Screenshot of the webpage (full page)
- ✅ HTML DOM structure
- ✅ Computed metrics as context

### 2. Model Update

- **Default model**: Changed from `gemini-2.0-flash-exp` to `gemini-1.5-pro`
- **Reason**: Gemini 1.5 Pro has better multimodal (vision) capabilities
- **Note**: Gemini 2.5 Pro doesn't exist yet (latest is 1.5 Pro or 2.0 Flash)

### 3. Comprehensive Analysis Method

New `analyze_comprehensive()` method in `LLMAnalyzer`:

```python
def analyze_comprehensive(
    self,
    screenshot_path: str,           # Path to screenshot
    html_content: str,              # Raw HTML
    url: str,                       # URL being analyzed
    accessibility_data: dict,       # Computed metrics
    contrast_data: dict,            # Computed metrics  
    dark_pattern_data: dict,        # Computed metrics
    custom_prompt: str = None
) -> str
```

**What it does**:
1. Loads screenshot as image
2. Combines screenshot + HTML + metrics into multimodal prompt
3. Sends to Gemini 1.5 Pro for analysis
4. Returns comprehensive report with:
   - Executive summary
   - Accessibility analysis (what Gemini sees in screenshot/HTML)
   - Visual design & contrast issues
   - Dark patterns and ethical concerns
   - Prioritized recommendations
   - Implementation guidance

### 4. Integrated Reporting

**New flow in `llm_reporter.py`**:

1. **Try comprehensive multimodal analysis first**
   - If LLM available: Use `analyze_comprehensive()` with screenshot + HTML
   - Returns integrated report with:
     - Computed metrics summary table at top
     - Full AI analysis of actual webpage
   
2. **Fallback to rule-based + individual LLM calls**
   - If comprehensive analysis fails
   - Uses old method (individual section analysis)

### 5. Enhanced Prompt Structure

The comprehensive prompt includes:

```
## Screenshot Analysis
[Image of webpage]

## Website URL
https://example.com

## Automated Metrics
- Accessibility Score: 0.65
- Contrast Ratio: 3.8:1
- Dark Patterns: 3 detected

## HTML Structure
[Full HTML or first 15,000 chars]

## Your Analysis
[Detailed request for specific sections]
```

## Report Structure

### With Multimodal Analysis (NEW)

```markdown
# Comprehensive Design Audit Report

## Computed Metrics Summary
| Metric | Score | Details |
|--------|-------|---------|
| Accessibility | 65% | 12 violations |
| Contrast | 3.8:1 | 5 low-contrast regions |
| Ethical UX | 70% | 3 potential dark patterns |

---

# AI-Powered Comprehensive Analysis

## Executive Summary
[Gemini's analysis of what it sees in the screenshot and HTML]

## Accessibility Analysis  
[Specific barriers Gemini observes in the actual design]

## Visual Design & Contrast
[Contrast issues Gemini can see in the screenshot]

## Ethical UX & Dark Patterns
[Manipulative elements Gemini identifies]

## Prioritized Recommendations
[HIGH/MEDIUM/LONG-TERM fixes with specifics]

## Implementation Guidance
[Code changes, design improvements, testing strategies]

---

## Technical Details
[Automated audit data for reference]
```

## Key Improvements

### 1. Context-Aware Analysis
**Before**: LLM only knew about violation counts
**Now**: LLM sees the actual webpage and can reference specific visual elements

### 2. Accurate Visual Assessment
**Before**: "12 contrast violations detected"
**Now**: "The blue text on purple background in the hero section is illegible. The footer links blend into the dark background."

### 3. Specific Recommendations
**Before**: "Fix contrast issues"
**Now**: "Change hero text from #3B5998 to #FFFFFF, increase button border from 1px to 2px, add drop shadow to navigation links"

### 4. Real User Perspective
**Before**: Technical metrics only
**Now**: "A user with low vision would struggle to distinguish the 'Submit' button from the background. The form labels are too small at 12px."

## Usage

### In Streamlit UI

1. Check "Enable Gemini Multimodal Analysis"
2. Enter Google AI API key
3. Select model (Gemini 1.5 Pro recommended)
4. Run audit on URL or screenshot
5. Report will include comprehensive AI analysis

### Programmatically

```python
from design_assistant.llm_integration import LLMConfig
from design_assistant.pipeline import DesignAssistant, InputMode

# Configure with Gemini 1.5 Pro
llm_config = LLMConfig(
    api_key="your-key",
    model="gemini-1.5-pro",
    temperature=0.7,
    max_tokens=8000
)

# Create assistant
assistant = DesignAssistant(llm_config=llm_config)

# Run audit - will use multimodal analysis
result = assistant.run(
    InputMode.URL,
    "https://example.com",
    output_dir=Path("outputs")
)

# Report includes screenshot + HTML analysis
```

## Cost Considerations

### Free Tier
- **Gemini 1.5 Pro**: 50 requests/day (free)
- **Gemini 1.5 Flash**: 1,500 requests/day (free)

### Paid Pricing
- **Gemini 1.5 Pro**: $1.25/1M input tokens, $5/1M output tokens
- **Multimodal input**: Images count toward token limit (varies by size)

### Typical Audit Cost
- Screenshot: ~200-400 tokens (varies by resolution)
- HTML (15k chars): ~4,000 tokens
- Output: ~2,000-4,000 tokens
- **Total**: ~$0.03-$0.05 per audit (if exceeding free tier)

## Technical Details

### File Handling

The system automatically extracts file paths from pipeline artifacts:
- `screenshot_path`: Path to full-page screenshot
- `dom_path`: Path to saved HTML file
- `url`: Original URL (for context)

### Image Processing

Uses PIL (Pillow) to load images for Gemini:
```python
import PIL.Image
img = PIL.Image.open(screenshot_path)
content_parts = [img, prompt_text]
```

### HTML Truncation

HTML is truncated to first 15,000 characters if longer:
- Prevents token limit issues
- Still provides enough structure for analysis
- Includes note in prompt about truncation

### Error Handling

Graceful fallback if multimodal analysis fails:
1. Catches exceptions in comprehensive analysis
2. Falls back to rule-based report generation
3. Still includes individual LLM enhancements if available
4. Prints warning but continues operation

## Installation

Ensure dependencies are installed:

```bash
pip install google-generativeai>=0.3.0
pip install Pillow>=10.0.0  # Already in requirements
```

## Testing

1. **Test with URL**:
   ```bash
   streamlit run app.py
   # Select URL mode
   # Enable Gemini analysis
   # Enter URL
   ```

2. **Test with screenshot**:
   ```bash
   # Upload screenshot in UI
   # Enable Gemini analysis
   # HTML won't be available but screenshot will be analyzed
   ```

3. **Verify output**:
   - Check markdown report includes "AI-Powered Comprehensive Analysis"
   - Look for specific visual observations (not just metrics)
   - Verify recommendations reference actual design elements

## Troubleshooting

### "Import PIL.Image could not be resolved"
- Expected if Pillow not installed
- Install: `pip install Pillow>=10.0.0`

### "Multimodal LLM Analysis Error"
- Check API key is valid
- Verify screenshot file exists
- Try smaller screenshot (reduce resolution)
- Check internet connection

### "Analysis too short"
- Increase `max_tokens` to 8000
- Use Gemini 1.5 Pro (more detailed than Flash)
- Check if screenshot loaded correctly

### Falls back to rule-based report
- LLM config not provided or invalid
- Screenshot/HTML files not found
- API error (rate limit, auth failure)
- System will still generate report with computed metrics

## Future Enhancements

- [ ] Support multiple screenshots (different viewport sizes)
- [ ] Analyze screenshot regions separately for detailed feedback
- [ ] Compare before/after screenshots
- [ ] Extract text from screenshot using OCR
- [ ] Annotate screenshot with issue markers
- [ ] Video analysis for animations/interactions
- [ ] A/B test report comparison

## Migration Notes

If you were using the previous version:
- Reports will be longer and more detailed
- API costs may be slightly higher (images count as tokens)
- Free tier might be exhausted faster (50/day vs 1,500/day for Flash)
- Consider using Gemini 1.5 Flash for high-volume usage
- Quality improvement is significant - worth the trade-off

## Conclusion

The multimodal analysis provides:
- ✅ Visual context-aware feedback
- ✅ Specific, actionable recommendations
- ✅ Real user perspective
- ✅ Integrated metrics + AI insights
- ✅ Professional, comprehensive reports

The system now acts like a human UX auditor who can actually see and interpret the design, not just read metrics.
