"""Command-line interface for running the design assistant pipeline."""
from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import DesignAssistant, InputMode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the AI-Powered Design Assistant")
    parser.add_argument("mode", choices=[item.value for item in InputMode])
    parser.add_argument("value", help="URL or path to screenshot, depending on mode")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory to store audit artifacts",
    )
    parser.add_argument("--alpha", type=float, default=0.5, help="Accessibility weight")
    parser.add_argument("--beta", type=float, default=0.5, help="Ethical UX weight")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    assistant = DesignAssistant(alpha=args.alpha, beta=args.beta)
    result = assistant.run(InputMode(args.mode), args.value, output_dir=args.output_dir)
    print(f"Design Fairness Score: {result.fairness.value:.2f}")
    if result.accessibility:
        print(f"Accessibility Score: {result.accessibility.score:.2f}")
    print(f"Contrast Average: {result.contrast.average_contrast:.2f}")
    print(f"Ethical UX Score: {result.dark_patterns.score:.2f}")
    print(f"Artifacts written to {args.output_dir.resolve()}")


if __name__ == "__main__":  # pragma: no cover
    main()
