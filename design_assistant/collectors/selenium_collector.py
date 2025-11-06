"""Collects DOM, text, and screenshot artifacts via Selenium."""
from __future__ import annotations

import os
import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional, Protocol

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service as ChromeService  # type: ignore[import]
except ImportError:  # pragma: no cover - optional dependency
    webdriver = None
    By = None
    ChromeService = None

try:
    from axe_selenium_python import Axe  # type: ignore[import]
except ImportError:  # pragma: no cover - optional dependency
    Axe = None

try:  # pragma: no cover - optional dependency
    from webdriver_manager.chrome import ChromeDriverManager  # type: ignore[import]
    from webdriver_manager.core.utils import ChromeType  # type: ignore[import]
except ImportError:  # pragma: no cover
    ChromeDriverManager = None
    ChromeType = None

from .screenshot_loader import ScreenshotArtifacts, ScreenshotLoader

if TYPE_CHECKING:  # pragma: no cover - for type checking only
    from selenium.webdriver.remote.webdriver import WebDriver
    from ..audits.accessibility import AccessibilityReport
else:  # pragma: no cover - runtime fallback
    WebDriver = Any
    AccessibilityReport = Any


class DriverFactory(Protocol):
    def __call__(self) -> Any:
        ...


@dataclass(frozen=True)
class SeleniumArtifacts:
    """Artifacts captured from a live URL."""

    url: str
    dom_path: Path
    screenshot: ScreenshotArtifacts
    visible_text: str
    axe_json_path: Optional[Path]
    axe_results: Optional[dict]
    accessibility: Optional[AccessibilityReport]


class SeleniumCollector:
    """Fetches page artifacts using a provided Selenium WebDriver."""

    def __init__(
        self,
        driver_factory: Optional[DriverFactory] = None,
        *,
        sleep_after_load: float = 2.0,
        timeout: int = 30,
    ) -> None:
        self.driver_factory = driver_factory or self._default_driver_factory
        self.sleep_after_load = sleep_after_load
        self.timeout = timeout
        self.screenshot_loader = ScreenshotLoader()

    def collect(self, url: str, *, output_dir: Path) -> SeleniumArtifacts:
        if webdriver is None:
            raise RuntimeError(
                "Selenium is not available. Install selenium and configure a WebDriver."
            )

        output_dir.mkdir(parents=True, exist_ok=True)
        driver = self.driver_factory()
        dom_path = output_dir / "page_dom.html"
        visible_text = ""
        screenshot_path = output_dir / "screenshot.png"
        axe_json_path = None
        axe_results: Optional[dict] = None
        accessibility_report = None
        try:
            driver.set_page_load_timeout(self.timeout)
            driver.get(url)
            time.sleep(self.sleep_after_load)

            dom_path.write_text(driver.page_source, encoding="utf-8")

            if By is not None:
                try:
                    body = driver.find_element(By.TAG_NAME, "body")
                    visible_text = body.text
                except Exception:
                    visible_text = ""

            # Capture full-page screenshot (including content below fold)
            screenshot_bytes = self._capture_full_page_screenshot(driver)
            screenshot = self.screenshot_loader.load_from_bytes(
                screenshot_bytes, output_path=screenshot_path
            )

            if Axe is not None:
                axe = Axe(driver)
                axe.inject()
                # Use a custom minimal runner that returns JSON-stringified results to avoid
                # Chrome DevTools Runtime.callFunctionOn deserialization issues with large objects.
                try:
                    axe_results = self._run_axe_minimal(driver)
                except Exception:
                    # Fallback to library run; still try to stringify client-side to reduce issues
                    axe_results = self._run_axe_stringified(driver)

                axe_json_path = output_dir / "axe_results.json"
                try:
                    with open(axe_json_path, "w", encoding="utf-8") as f:
                        json.dump(axe_results, f, ensure_ascii=False, indent=2)
                except Exception:
                    # As a last resort, use library writer if available
                    try:
                        axe.write_results(axe_results, str(axe_json_path))
                    except Exception:
                        pass
        finally:
            driver.quit()

        return SeleniumArtifacts(
            url=url,
            dom_path=dom_path,
            screenshot=screenshot,
            visible_text=visible_text,
            axe_json_path=axe_json_path,
            axe_results=axe_results,
            accessibility=accessibility_report,
        )

    def _run_axe_minimal(self, driver: Any) -> dict:
        """Run axe-core in the page and return a minimal, serializable result.

        This avoids returning the full axe result object (which can contain non-serializable
        handles) by JSON-stringifying only the needed fields.
        """
        script = """
        const callback = arguments[0];
        try {
            const context = document;
            const options = {
                resultTypes: ['violations','incomplete'],
                runOnly: { type: 'tag', values: ['wcag2a','wcag2aa'] },
                reporter: 'v2'
            };
            // axe is provided by axe.inject()
            window.axe.run(context, options).then(results => {
                const minimal = {
                    violations: results.violations || [],
                    incomplete: results.incomplete || []
                };
                callback(JSON.stringify(minimal));
            }).catch(err => {
                callback(JSON.stringify({ error: String(err) }));
            });
        } catch (e) {
            callback(JSON.stringify({ error: String(e) }));
        }
        """
        raw = driver.execute_async_script(script)
        try:
            return json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            # If parsing fails, return a best-effort structure
            return {"error": "Failed to parse axe results", "raw": str(raw)[:1000]}

    def _run_axe_stringified(self, driver: Any) -> dict:
        """Fallback runner that returns the full results but stringified client-side."""
        script = """
        const callback = arguments[0];
        try {
            window.axe.run(document, { reporter: 'v2' }).then(results => {
                callback(JSON.stringify(results));
            }).catch(err => {
                callback(JSON.stringify({ error: String(err) }));
            });
        } catch (e) {
            callback(JSON.stringify({ error: String(e) }));
        }
        """
        raw = driver.execute_async_script(script)
        try:
            return json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            return {"error": "Failed to parse fallback axe results", "raw": str(raw)[:1000]}

    def _default_driver_factory(self) -> Any:
        if webdriver is None:
            raise RuntimeError("Selenium is not installed.")

        if not hasattr(webdriver, "Chrome"):
            raise RuntimeError(
                "No default WebDriver available. Provide driver_factory explicitly."
            )

        options = webdriver.ChromeOptions()
        # Headless + sandbox-safe defaults for WSL and CI environments.
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--window-size=1920,1080")

        binary = self._resolve_chrome_binary()
        if not binary:
            raise RuntimeError(
                "Google Chrome binary not found. Please either:\n"
                "1. Install Google Chrome on Windows (recommended), or\n"
                "2. Set CHROME_BINARY environment variable:\n"
                "   - PowerShell: $env:CHROME_BINARY = \"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe\"\n"
                '   - WSL/Bash: export CHROME_BINARY="/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"\n'
                "3. Make it permanent:\n"
                "   - PowerShell: Add to $PROFILE\n"
                "   - WSL/Bash: Add export to ~/.bashrc"
            )
        options.binary_location = binary

        service = None
        driver_path = self._resolve_chromedriver_path()
        if driver_path and ChromeService is not None:
            service = ChromeService(driver_path)

        try:
            if service is not None:
                return webdriver.Chrome(service=service, options=options)
            return webdriver.Chrome(options=options)
        except Exception as exc:  # pragma: no cover - propagate meaningful error
            guidance = (
                "Failed to initialize ChromeDriver. Verify Google Chrome is installed or "
                "set CHROME_BINARY and CHROMEDRIVER_PATH environment variables."
            )
            raise RuntimeError(guidance) from exc

    def _resolve_chrome_binary(self) -> Optional[str]:
        explicit = os.getenv("CHROME_BINARY")
        if explicit and Path(explicit).exists():
            return explicit

        # Windows-specific paths (PowerShell/native Windows)
        windows_candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
        ]
        
        # WSL-specific paths (Linux subsystem)
        wsl_candidates = [
            "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
            "/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        ]
        
        # Linux native paths
        linux_candidates = [
            shutil.which("google-chrome"),
            shutil.which("google-chrome-stable"),
            shutil.which("chrome"),
            "/opt/google/chrome/chrome",
            "/usr/bin/google-chrome",
        ]
        
        # Combine all candidates
        candidates = windows_candidates + wsl_candidates + linux_candidates
        
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return str(candidate)
        return None

    def _resolve_chromedriver_path(self) -> Optional[str]:
        explicit = os.getenv("CHROMEDRIVER_PATH")
        if explicit and Path(explicit).exists():
            return explicit

        system_driver = shutil.which("chromedriver")
        if system_driver:
            return system_driver

        if ChromeDriverManager is not None:
            try:
                kwargs = {"chrome_type": ChromeType.GOOGLE} if ChromeType is not None else {}
                return ChromeDriverManager(**kwargs).install()
            except Exception:
                return None
        return None
    
    def _capture_full_page_screenshot(self, driver: Any) -> bytes:
        """Capture full-page screenshot including content below the fold.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            PNG screenshot bytes of the entire page
        """
        # Get full page dimensions
        total_width = driver.execute_script("return document.body.scrollWidth")
        total_height = driver.execute_script("return document.body.scrollHeight")
        viewport_width = driver.execute_script("return window.innerWidth")
        viewport_height = driver.execute_script("return window.innerHeight")
        
        # Set window size to capture full width (height will be handled by scrolling)
        driver.set_window_size(total_width, viewport_height)
        time.sleep(0.5)  # Let page adjust
        
        # Calculate number of scrolls needed
        rectangles = []
        i = 0
        while i < total_height:
            # Scroll to position
            driver.execute_script(f"window.scrollTo(0, {i})")
            time.sleep(0.2)  # Brief pause for content to render
            
            # Capture viewport
            screenshot_bytes = driver.get_screenshot_as_png()
            rectangles.append({
                'screenshot': screenshot_bytes,
                'offset': i
            })
            
            i += viewport_height
        
        # Stitch screenshots together using PIL/OpenCV
        try:
            from PIL import Image
            import io
            
            images = []
            for rect in rectangles:
                img = Image.open(io.BytesIO(rect['screenshot']))
                images.append(img)
            
            # Create full canvas
            full_image = Image.new('RGB', (total_width, total_height))
            
            # Paste each screenshot at correct offset
            current_y = 0
            for i, img in enumerate(images):
                full_image.paste(img, (0, current_y))
                current_y += viewport_height
                # Handle last image which might be partial
                if current_y > total_height:
                    break
            
            # Crop to exact height
            full_image = full_image.crop((0, 0, total_width, total_height))
            
            # Convert to bytes
            output = io.BytesIO()
            full_image.save(output, format='PNG')
            return output.getvalue()
            
        except ImportError:
            # Fallback: if PIL not available, return single viewport screenshot
            driver.execute_script("window.scrollTo(0, 0)")
            return driver.get_screenshot_as_png()
