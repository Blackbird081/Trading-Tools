from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote


@dataclass
class CoverageSlice:
    name: str
    covered: int
    total: int
    lines_pct: float
    statements_pct: float | None = None
    functions_pct: float | None = None
    branches_pct: float | None = None


def _badge_color(pct: float) -> str:
    if pct >= 85.0:
        return "brightgreen"
    if pct >= 70.0:
        return "yellow"
    return "red"


def _badge_url(label: str, pct: float) -> str:
    message = f"{pct:.2f}%"
    return f"https://img.shields.io/badge/{quote(label)}-{quote(message)}-{_badge_color(pct)}"


def _load_python_coverage(path: Path) -> CoverageSlice:
    payload = json.loads(path.read_text(encoding="utf-8"))
    totals = payload["totals"]
    covered = int(totals["covered_lines"])
    total = int(totals["num_statements"])
    lines_pct = float(totals["percent_covered"])
    return CoverageSlice(
        name="Python (pytest-cov)",
        covered=covered,
        total=total,
        lines_pct=lines_pct,
        statements_pct=lines_pct,
    )


def _load_frontend_coverage(path: Path) -> CoverageSlice:
    payload = json.loads(path.read_text(encoding="utf-8"))
    total = payload["total"]
    lines_total = int(total["lines"]["total"])
    lines_covered = int(total["lines"]["covered"])
    return CoverageSlice(
        name="Frontend (Vitest)",
        covered=lines_covered,
        total=lines_total,
        lines_pct=float(total["lines"]["pct"]),
        statements_pct=float(total["statements"]["pct"]),
        functions_pct=float(total["functions"]["pct"]),
        branches_pct=float(total["branches"]["pct"]),
    )


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}%"


def _render_markdown(
    generated_at: str,
    source: str,
    python: CoverageSlice,
    frontend: CoverageSlice,
    python_status: str,
    frontend_status: str,
) -> str:
    total_lines = python.total + frontend.total
    covered_lines = python.covered + frontend.covered
    overall_pct = (covered_lines / total_lines * 100.0) if total_lines else 0.0

    python_badge = _badge_url("python coverage", python.lines_pct)
    frontend_badge = _badge_url("frontend coverage", frontend.lines_pct)
    overall_badge = _badge_url("overall coverage", overall_pct)

    return "\n".join(
        [
            "# TEST_COVERAGE_LATEST",
            "",
            f"- Generated at (UTC): {generated_at}",
            f"- Source: {source}",
            f"- Python test status: {python_status}",
            f"- Frontend test status: {frontend_status}",
            "",
            "## Badges",
            "",
            f"![Python Coverage]({python_badge})",
            f"![Frontend Coverage]({frontend_badge})",
            f"![Overall Coverage]({overall_badge})",
            "",
            "## Coverage Summary",
            "",
            "| Suite | Lines | Statements | Functions | Branches | Covered/Total (Lines) |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
            (
                f"| {python.name} | {_fmt_pct(python.lines_pct)} | {_fmt_pct(python.statements_pct)} "
                f"| {_fmt_pct(python.functions_pct)} | {_fmt_pct(python.branches_pct)} "
                f"| {python.covered}/{python.total} |"
            ),
            (
                f"| {frontend.name} | {_fmt_pct(frontend.lines_pct)} | {_fmt_pct(frontend.statements_pct)} "
                f"| {_fmt_pct(frontend.functions_pct)} | {_fmt_pct(frontend.branches_pct)} "
                f"| {frontend.covered}/{frontend.total} |"
            ),
            f"| Overall (line-weighted) | {overall_pct:.2f}% | - | - | - | {covered_lines}/{total_lines} |",
            "",
            "## CI Notes",
            "",
            "- Python gate in CI: `--cov-fail-under=80`.",
            "- Frontend coverage is reported as artifact + summary; threshold can be enforced later if needed.",
            "- This file is a lightweight snapshot; raw HTML/LCOV artifacts stay out of Git history.",
            "",
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate markdown coverage snapshot.")
    parser.add_argument("--python-json", required=True, type=Path)
    parser.add_argument("--frontend-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--badge-output", type=Path)
    parser.add_argument("--source", default="local")
    parser.add_argument("--python-status", default="unknown")
    parser.add_argument("--frontend-status", default="unknown")
    args = parser.parse_args()

    python = _load_python_coverage(args.python_json)
    frontend = _load_frontend_coverage(args.frontend_json)

    rendered = _render_markdown(
        generated_at=datetime.now(UTC).isoformat(),
        source=args.source,
        python=python,
        frontend=frontend,
        python_status=args.python_status,
        frontend_status=args.frontend_status,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")

    if args.badge_output is not None:
        total_lines = python.total + frontend.total
        covered_lines = python.covered + frontend.covered
        overall_pct = (covered_lines / total_lines * 100.0) if total_lines else 0.0
        badges = "\n".join(
            [
                f"- Python: {_badge_url('python coverage', python.lines_pct)}",
                f"- Frontend: {_badge_url('frontend coverage', frontend.lines_pct)}",
                f"- Overall: {_badge_url('overall coverage', overall_pct)}",
                "",
            ],
        )
        args.badge_output.parent.mkdir(parents=True, exist_ok=True)
        args.badge_output.write_text(badges, encoding="utf-8")

    print(f"Coverage report written: {args.output}")


if __name__ == "__main__":
    main()
