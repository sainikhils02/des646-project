"""Agentic auditing: keyboard-only navigation and screen-reader simulation.

This module goes beyond static DOM analysis by *interacting* with a live page
through Selenium, simulating how real users with assistive technologies
experience the interface.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.remote.webelement import WebElement
except ImportError:  # pragma: no cover
    webdriver = None
    By = None
    Keys = None
    ActionChains = None
    WebElement = None


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AgenticIssue:
    """A single issue discovered through agentic interaction."""

    category: str          # "keyboard" | "screen_reader" | "functional"
    severity: str          # "critical" | "serious" | "moderate" | "minor"
    description: str
    element_info: Optional[str] = None   # selector or tag info
    wcag_criterion: Optional[str] = None
    recommendation: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "severity": self.severity,
            "description": self.description,
            "element_info": self.element_info,
            "wcag_criterion": self.wcag_criterion,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class AgenticReport:
    """Aggregated results of agentic interaction auditing."""

    keyboard_score: float
    screen_reader_score: float
    keyboard_issues: List[AgenticIssue]
    screen_reader_issues: List[AgenticIssue]
    functional_issues: List[AgenticIssue]
    tab_order: List[Dict[str, Any]]
    aria_tree_summary: Dict[str, Any]

    @property
    def total_issues(self) -> int:
        return len(self.keyboard_issues) + len(self.screen_reader_issues) + len(self.functional_issues)

    @property
    def combined_score(self) -> float:
        return (self.keyboard_score * 0.5) + (self.screen_reader_score * 0.5)

    def to_dict(self) -> dict:
        return {
            "keyboard_score": self.keyboard_score,
            "screen_reader_score": self.screen_reader_score,
            "combined_score": self.combined_score,
            "total_issues": self.total_issues,
            "keyboard_issues": [i.to_dict() for i in self.keyboard_issues],
            "screen_reader_issues": [i.to_dict() for i in self.screen_reader_issues],
            "functional_issues": [i.to_dict() for i in self.functional_issues],
            "tab_order_length": len(self.tab_order),
            "aria_tree_summary": self.aria_tree_summary,
        }


# ---------------------------------------------------------------------------
# Auditor
# ---------------------------------------------------------------------------

class AgenticAuditor:
    """Simulates keyboard-only and screen-reader user interactions.

    Requires an active Selenium WebDriver session (the page must already be
    loaded).  Call ``audit(driver)`` to run the full suite of interaction
    checks.
    """

    def __init__(
        self,
        *,
        max_tabs: int = 150,
        focus_wait: float = 0.05,
        keyboard_baseline: int = 10,
        sr_baseline: int = 15,
    ) -> None:
        self.max_tabs = max_tabs
        self.focus_wait = focus_wait
        self.keyboard_baseline = max(keyboard_baseline, 1)
        self.sr_baseline = max(sr_baseline, 1)

    def audit(self, driver: Any) -> AgenticReport:
        """Run the complete agentic audit suite on the currently-loaded page."""
        if webdriver is None or driver is None:
            raise RuntimeError("Selenium is required for agentic auditing.")

        keyboard_issues, tab_order = self._audit_keyboard(driver)
        sr_issues, aria_summary = self._audit_screen_reader(driver)
        functional_issues = self._audit_functional(driver)

        kb_penalty = len(keyboard_issues) / self.keyboard_baseline
        keyboard_score = max(0.0, 1.0 - kb_penalty)

        sr_penalty = len(sr_issues) / self.sr_baseline
        screen_reader_score = max(0.0, 1.0 - sr_penalty)

        return AgenticReport(
            keyboard_score=keyboard_score,
            screen_reader_score=screen_reader_score,
            keyboard_issues=keyboard_issues,
            screen_reader_issues=sr_issues,
            functional_issues=functional_issues,
            tab_order=tab_order,
            aria_tree_summary=aria_summary,
        )

    # ------------------------------------------------------------------
    # Keyboard-only navigation audit
    # ------------------------------------------------------------------

    def _audit_keyboard(self, driver: Any) -> Tuple[List[AgenticIssue], List[Dict[str, Any]]]:
        """Simulate Tab keypresses and analyse focus behaviour."""
        issues: List[AgenticIssue] = []
        tab_order: List[Dict[str, Any]] = []
        seen_elements: set = set()

        # Count total interactive elements on the page
        interactive_count = driver.execute_script("""
            const interactives = document.querySelectorAll(
                'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
            );
            return interactives.length;
        """)

        # Check for skip navigation link
        has_skip_link = driver.execute_script("""
            const links = document.querySelectorAll('a[href^="#"]');
            for (const link of links) {
                const text = (link.textContent || '').toLowerCase();
                if (text.includes('skip') || text.includes('main content') || text.includes('navigation')) {
                    return true;
                }
            }
            return false;
        """)

        if not has_skip_link and interactive_count > 5:
            issues.append(AgenticIssue(
                category="keyboard",
                severity="moderate",
                description="No skip-navigation link found. Keyboard users must tab through all navigation items to reach main content.",
                wcag_criterion="2.4.1 Bypass Blocks",
                recommendation="Add a visually-hidden skip link at the top of the page: <a href='#main-content' class='skip-link'>Skip to main content</a>",
            ))

        # Send Tab keys and track focus
        body = driver.find_element(By.TAG_NAME, "body")
        body.click()  # Ensure focus starts from body
        time.sleep(0.1)

        previous_element = None
        cycle_start_id = None

        for i in range(self.max_tabs):
            ActionChains(driver).send_keys(Keys.TAB).perform()
            time.sleep(self.focus_wait)

            focused = driver.execute_script("""
                const el = document.activeElement;
                if (!el || el === document.body) return null;

                const rect = el.getBoundingClientRect();
                const styles = window.getComputedStyle(el);
                const outlineStyle = styles.outline || styles.outlineStyle || '';
                const outlineWidth = parseInt(styles.outlineWidth) || 0;
                const boxShadow = styles.boxShadow || '';

                return {
                    tag: el.tagName.toLowerCase(),
                    id: el.id || null,
                    className: el.className || null,
                    role: el.getAttribute('role') || null,
                    ariaLabel: el.getAttribute('aria-label') || null,
                    text: (el.textContent || '').trim().substring(0, 80),
                    tabIndex: el.tabIndex,
                    isVisible: rect.width > 0 && rect.height > 0,
                    hasVisibleFocus: (outlineWidth > 0 && outlineStyle !== 'none') ||
                                     (boxShadow !== '' && boxShadow !== 'none'),
                    selector: el.id ? '#' + el.id : el.tagName.toLowerCase() +
                              (el.className ? '.' + el.className.split(' ')[0] : ''),
                    position: { x: Math.round(rect.x), y: Math.round(rect.y) }
                };
            """)

            if focused is None:
                continue

            element_key = focused.get("selector", "") + focused.get("text", "")[:30]

            # Detect focus cycle (we've looped back)
            if element_key in seen_elements:
                if cycle_start_id is None:
                    cycle_start_id = element_key
                elif element_key == cycle_start_id:
                    break  # Full cycle detected
                continue

            seen_elements.add(element_key)
            tab_order.append({
                "index": len(tab_order),
                "tag": focused.get("tag"),
                "selector": focused.get("selector"),
                "text": focused.get("text", "")[:50],
                "has_visible_focus": focused.get("hasVisibleFocus", False),
                "is_visible": focused.get("isVisible", True),
                "role": focused.get("role"),
            })

            # Check: no visible focus indicator
            if not focused.get("hasVisibleFocus", True):
                issues.append(AgenticIssue(
                    category="keyboard",
                    severity="serious",
                    description=f"Element <{focused['tag']}> receives focus but has no visible focus indicator.",
                    element_info=focused.get("selector"),
                    wcag_criterion="2.4.7 Focus Visible",
                    recommendation="Add CSS focus styles: outline: 2px solid #005fcc; outline-offset: 2px;",
                ))

            # Check: invisible/off-screen element receives focus
            if not focused.get("isVisible", True):
                issues.append(AgenticIssue(
                    category="keyboard",
                    severity="serious",
                    description=f"Hidden element <{focused['tag']}> receives keyboard focus (zero-size bounding box).",
                    element_info=focused.get("selector"),
                    wcag_criterion="2.4.3 Focus Order",
                    recommendation="Set tabindex='-1' on hidden elements or use display:none/visibility:hidden.",
                ))

            previous_element = focused

        # Check: interactive elements not reached by Tab
        reached_count = len(tab_order)
        if interactive_count > 0 and reached_count < interactive_count * 0.6:
            issues.append(AgenticIssue(
                category="keyboard",
                severity="critical",
                description=f"Only {reached_count}/{interactive_count} interactive elements are reachable via Tab key. "
                            f"{interactive_count - reached_count} elements may be keyboard-inaccessible.",
                wcag_criterion="2.1.1 Keyboard",
                recommendation="Ensure all interactive elements are focusable. Use native HTML elements (button, a) "
                               "or add tabindex='0' and keyboard event handlers.",
            ))

        # Check for focus trap via JS
        has_focus_trap = driver.execute_script("""
            const modals = document.querySelectorAll('[role="dialog"], [aria-modal="true"], .modal');
            for (const modal of modals) {
                const style = window.getComputedStyle(modal);
                if (style.display !== 'none' && style.visibility !== 'hidden') {
                    const focusables = modal.querySelectorAll(
                        'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
                    );
                    if (focusables.length === 0) return 'empty_trap';
                    return 'modal_open';
                }
            }
            return 'none';
        """)

        if has_focus_trap == "empty_trap":
            issues.append(AgenticIssue(
                category="keyboard",
                severity="critical",
                description="An open modal/dialog contains no focusable elements — keyboard users are trapped.",
                wcag_criterion="2.1.2 No Keyboard Trap",
                recommendation="Ensure modals contain at least one focusable element and implement focus trapping within the modal.",
            ))

        return issues, tab_order

    # ------------------------------------------------------------------
    # Screen-reader simulation audit
    # ------------------------------------------------------------------

    def _audit_screen_reader(self, driver: Any) -> Tuple[List[AgenticIssue], Dict[str, Any]]:
        """Walk the ARIA tree and check screen-reader semantics."""
        issues: List[AgenticIssue] = []

        aria_data = driver.execute_script("""
            function walkAriaTree() {
                const result = {
                    landmarks: [],
                    headings: [],
                    images_without_alt: [],
                    buttons_without_name: [],
                    links_without_name: [],
                    inputs_without_label: [],
                    aria_live_regions: [],
                    aria_hidden_with_focusable: [],
                    total_interactive: 0,
                    total_with_accessible_name: 0,
                };

                // Landmarks
                const landmarks = document.querySelectorAll(
                    '[role="banner"], [role="navigation"], [role="main"], [role="contentinfo"], ' +
                    '[role="complementary"], [role="search"], header, nav, main, footer, aside'
                );
                landmarks.forEach(el => {
                    result.landmarks.push({
                        tag: el.tagName.toLowerCase(),
                        role: el.getAttribute('role') || el.tagName.toLowerCase(),
                        label: el.getAttribute('aria-label') || el.getAttribute('aria-labelledby') || ''
                    });
                });

                // Headings hierarchy
                const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6, [role="heading"]');
                let prevLevel = 0;
                headings.forEach(h => {
                    const level = parseInt(h.tagName?.replace('H', '') || h.getAttribute('aria-level') || '0');
                    result.headings.push({
                        level: level,
                        text: (h.textContent || '').trim().substring(0, 60),
                        skip: level > prevLevel + 1 && prevLevel > 0
                    });
                    prevLevel = level;
                });

                // Images without alt
                document.querySelectorAll('img').forEach(img => {
                    const alt = img.getAttribute('alt');
                    const role = img.getAttribute('role');
                    if (alt === null && role !== 'presentation' && role !== 'none') {
                        result.images_without_alt.push({
                            src: (img.src || '').substring(0, 100),
                            selector: img.id ? '#' + img.id : 'img'
                        });
                    }
                });

                // Buttons without accessible name
                document.querySelectorAll('button, [role="button"]').forEach(btn => {
                    result.total_interactive++;
                    const name = btn.getAttribute('aria-label') ||
                                 btn.getAttribute('aria-labelledby') ||
                                 btn.getAttribute('title') ||
                                 (btn.textContent || '').trim();
                    if (name) result.total_with_accessible_name++;
                    else {
                        result.buttons_without_name.push({
                            selector: btn.id ? '#' + btn.id : btn.tagName.toLowerCase(),
                            html: btn.outerHTML.substring(0, 120)
                        });
                    }
                });

                // Links without accessible name
                document.querySelectorAll('a[href]').forEach(link => {
                    result.total_interactive++;
                    const name = link.getAttribute('aria-label') ||
                                 link.getAttribute('aria-labelledby') ||
                                 link.getAttribute('title') ||
                                 (link.textContent || '').trim();
                    if (name) result.total_with_accessible_name++;
                    else {
                        result.links_without_name.push({
                            href: (link.href || '').substring(0, 100),
                            html: link.outerHTML.substring(0, 120)
                        });
                    }
                });

                // Inputs without label
                document.querySelectorAll('input, select, textarea').forEach(input => {
                    if (input.type === 'hidden') return;
                    result.total_interactive++;
                    const id = input.id;
                    const hasLabel = id && document.querySelector('label[for="' + id + '"]');
                    const ariaLabel = input.getAttribute('aria-label') || input.getAttribute('aria-labelledby');
                    const title = input.getAttribute('title');
                    const placeholder = input.getAttribute('placeholder');
                    if (hasLabel || ariaLabel || title) {
                        result.total_with_accessible_name++;
                    } else {
                        result.inputs_without_label.push({
                            type: input.type || input.tagName.toLowerCase(),
                            name: input.name || '',
                            placeholder: placeholder || '',
                            selector: id ? '#' + id : input.tagName.toLowerCase()
                        });
                    }
                });

                // ARIA live regions
                document.querySelectorAll('[aria-live]').forEach(el => {
                    result.aria_live_regions.push({
                        role: el.getAttribute('role') || '',
                        ariaLive: el.getAttribute('aria-live'),
                        text: (el.textContent || '').trim().substring(0, 60)
                    });
                });

                // aria-hidden with focusable children
                document.querySelectorAll('[aria-hidden="true"]').forEach(el => {
                    const focusables = el.querySelectorAll(
                        'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
                    );
                    if (focusables.length > 0) {
                        result.aria_hidden_with_focusable.push({
                            selector: el.id ? '#' + el.id : el.tagName.toLowerCase(),
                            focusable_count: focusables.length
                        });
                    }
                });

                return result;
            }
            return walkAriaTree();
        """)

        if not aria_data:
            aria_data = {}

        # Analyse headings
        headings = aria_data.get("headings", [])
        h1_count = sum(1 for h in headings if h.get("level") == 1)
        if h1_count == 0:
            issues.append(AgenticIssue(
                category="screen_reader",
                severity="serious",
                description="No <h1> heading found. Screen readers rely on headings to convey page structure.",
                wcag_criterion="1.3.1 Info and Relationships",
                recommendation="Add a single <h1> element describing the main page purpose.",
            ))
        elif h1_count > 1:
            issues.append(AgenticIssue(
                category="screen_reader",
                severity="moderate",
                description=f"Multiple <h1> headings found ({h1_count}). Best practice is a single <h1> per page.",
                wcag_criterion="1.3.1 Info and Relationships",
                recommendation="Use a single <h1> and structure sub-sections with <h2>, <h3>, etc.",
            ))

        skipped_headings = [h for h in headings if h.get("skip")]
        if skipped_headings:
            issues.append(AgenticIssue(
                category="screen_reader",
                severity="moderate",
                description=f"Heading hierarchy skips levels ({len(skipped_headings)} skips detected). "
                            "Screen reader users may lose context.",
                wcag_criterion="1.3.1 Info and Relationships",
                recommendation="Maintain sequential heading levels (h1 → h2 → h3) without skipping.",
            ))

        # Landmarks
        landmarks = aria_data.get("landmarks", [])
        landmark_roles = {lm.get("role", "") for lm in landmarks}
        if "main" not in landmark_roles and "MAIN" not in landmark_roles:
            issues.append(AgenticIssue(
                category="screen_reader",
                severity="serious",
                description="No <main> landmark found. Screen reader users cannot quickly navigate to primary content.",
                wcag_criterion="1.3.1 Info and Relationships",
                recommendation="Wrap the primary content area in a <main> element.",
            ))
        if "navigation" not in landmark_roles and "nav" not in {lm.get("tag", "") for lm in landmarks}:
            issues.append(AgenticIssue(
                category="screen_reader",
                severity="moderate",
                description="No <nav> landmark found. Navigation regions should be identified for assistive technology.",
                wcag_criterion="1.3.1 Info and Relationships",
                recommendation="Wrap navigation links in a <nav> element with aria-label if multiple navs exist.",
            ))

        # Images without alt
        no_alt_images = aria_data.get("images_without_alt", [])
        if no_alt_images:
            issues.append(AgenticIssue(
                category="screen_reader",
                severity="critical",
                description=f"{len(no_alt_images)} image(s) lack alt text. Screen readers cannot describe these to users.",
                element_info=", ".join(img["selector"] for img in no_alt_images[:5]),
                wcag_criterion="1.1.1 Non-text Content",
                recommendation="Add descriptive alt attributes. Use alt='' for decorative images with role='presentation'.",
            ))

        # Buttons without accessible name
        no_name_btns = aria_data.get("buttons_without_name", [])
        if no_name_btns:
            issues.append(AgenticIssue(
                category="screen_reader",
                severity="critical",
                description=f"{len(no_name_btns)} button(s) have no accessible name. "
                            "Screen readers will announce them as 'button' with no context.",
                element_info=", ".join(b["selector"] for b in no_name_btns[:3]),
                wcag_criterion="4.1.2 Name, Role, Value",
                recommendation="Add text content, aria-label, or aria-labelledby to each button.",
            ))

        # Links without accessible name
        no_name_links = aria_data.get("links_without_name", [])
        if no_name_links:
            issues.append(AgenticIssue(
                category="screen_reader",
                severity="serious",
                description=f"{len(no_name_links)} link(s) have no accessible name.",
                element_info=", ".join(l.get("selector", l.get("tag", "unknown")) for l in no_name_links[:3]),
                wcag_criterion="4.1.2 Name, Role, Value",
                recommendation="Add descriptive text content or aria-label to each link.",
            ))

        # Inputs without labels
        no_label_inputs = aria_data.get("inputs_without_label", [])
        if no_label_inputs:
            issues.append(AgenticIssue(
                category="screen_reader",
                severity="critical",
                description=f"{len(no_label_inputs)} form input(s) have no associated label.",
                element_info=", ".join(inp["selector"] for inp in no_label_inputs[:3]),
                wcag_criterion="1.3.1 Info and Relationships",
                recommendation="Associate each input with a <label for='id'> or use aria-label.",
            ))

        # aria-hidden with focusable children
        hidden_focusable = aria_data.get("aria_hidden_with_focusable", [])
        if hidden_focusable:
            issues.append(AgenticIssue(
                category="screen_reader",
                severity="critical",
                description=f"{len(hidden_focusable)} aria-hidden region(s) contain focusable elements. "
                            "Keyboard users can reach elements that screen readers cannot announce.",
                element_info=", ".join(h["selector"] for h in hidden_focusable[:3]),
                wcag_criterion="4.1.2 Name, Role, Value",
                recommendation="Remove focusable children from aria-hidden regions or set tabindex='-1'.",
            ))

        aria_summary = {
            "landmarks_count": len(landmarks),
            "headings_count": len(headings),
            "images_without_alt": len(no_alt_images),
            "buttons_without_name": len(no_name_btns),
            "links_without_name": len(no_name_links),
            "inputs_without_label": len(no_label_inputs),
            "aria_live_regions": len(aria_data.get("aria_live_regions", [])),
            "aria_hidden_focusable": len(hidden_focusable),
            "accessible_name_coverage": (
                f"{aria_data.get('total_with_accessible_name', 0)}/{aria_data.get('total_interactive', 0)}"
            ),
        }

        return issues, aria_summary

    # ------------------------------------------------------------------
    # Functional interaction audit
    # ------------------------------------------------------------------

    def _audit_functional(self, driver: Any) -> List[AgenticIssue]:
        """Check for functional interaction issues."""
        issues: List[AgenticIssue] = []

        # Check for auto-playing media
        autoplay_media = driver.execute_script("""
            const media = document.querySelectorAll('video, audio');
            const autoplaying = [];
            media.forEach(el => {
                if (el.autoplay && !el.paused && !el.muted) {
                    autoplaying.push({
                        tag: el.tagName.toLowerCase(),
                        src: (el.src || el.currentSrc || '').substring(0, 100)
                    });
                }
            });
            return autoplaying;
        """)

        if autoplay_media:
            issues.append(AgenticIssue(
                category="functional",
                severity="serious",
                description=f"{len(autoplay_media)} media element(s) auto-play with sound. "
                            "This can disorient screen reader users and violate WCAG.",
                wcag_criterion="1.4.2 Audio Control",
                recommendation="Disable autoplay or ensure media starts muted. Provide clear play/pause controls.",
            ))

        # Check for prefers-reduced-motion support
        has_motion_support = driver.execute_script("""
            const sheets = document.styleSheets;
            for (let i = 0; i < sheets.length; i++) {
                try {
                    const rules = sheets[i].cssRules || sheets[i].rules;
                    for (let j = 0; j < rules.length; j++) {
                        if (rules[j].media && rules[j].media.mediaText &&
                            rules[j].media.mediaText.includes('prefers-reduced-motion')) {
                            return true;
                        }
                    }
                } catch (e) {
                    // Cross-origin stylesheets — skip
                }
            }
            return false;
        """)

        # Check if page has animations
        has_animations = driver.execute_script("""
            const animated = document.querySelectorAll('[class*="anim"], [class*="transition"], [class*="fade"]');
            const cssAnimations = document.querySelectorAll('*');
            let animCount = 0;
            for (let i = 0; i < Math.min(cssAnimations.length, 200); i++) {
                const style = window.getComputedStyle(cssAnimations[i]);
                if (style.animationName && style.animationName !== 'none') animCount++;
                if (style.transition && style.transition !== 'all 0s ease 0s' && style.transition !== 'none 0s ease 0s') animCount++;
            }
            return animCount > 0 || animated.length > 0;
        """)

        if has_animations and not has_motion_support:
            issues.append(AgenticIssue(
                category="functional",
                severity="moderate",
                description="Page uses animations but does not respect prefers-reduced-motion media query.",
                wcag_criterion="2.3.3 Animation from Interactions",
                recommendation="Add @media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }",
            ))

        # Check for proper page language
        page_lang = driver.execute_script("""
            return document.documentElement.getAttribute('lang') || '';
        """)

        if not page_lang:
            issues.append(AgenticIssue(
                category="functional",
                severity="serious",
                description="Page does not declare a language. Screen readers need lang attribute to determine pronunciation.",
                wcag_criterion="3.1.1 Language of Page",
                recommendation="Add lang attribute to <html>: <html lang='en'>",
            ))

        # Check for viewport meta disabling zoom
        no_zoom = driver.execute_script("""
            const viewport = document.querySelector('meta[name="viewport"]');
            if (!viewport) return false;
            const content = viewport.getAttribute('content') || '';
            return content.includes('maximum-scale=1') ||
                   content.includes('user-scalable=no') ||
                   content.includes('user-scalable=0');
        """)

        if no_zoom:
            issues.append(AgenticIssue(
                category="functional",
                severity="critical",
                description="Viewport meta tag disables user zooming. Users with low vision cannot enlarge content.",
                wcag_criterion="1.4.4 Resize Text",
                recommendation="Remove maximum-scale=1 and user-scalable=no from viewport meta tag.",
            ))

        return issues
