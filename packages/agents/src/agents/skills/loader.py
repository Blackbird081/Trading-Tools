"""Skills Loader — discover and load agent skill definitions.

★ Inspired by Dexter's skills/loader.ts.
★ Skills are Markdown files with YAML frontmatter.
★ Discovery order: builtin → user (~/.trading/skills/) → project (.trading/skills/).
★ Later sources override earlier ones (project > user > builtin).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

logger = logging.getLogger("agents.skills")

SkillSource = Literal["builtin", "user", "project"]

BUILTIN_SKILLS_DIR = Path(__file__).parent / "builtin"
USER_SKILLS_DIR = Path.home() / ".trading" / "skills"
PROJECT_SKILLS_DIR = Path(".trading") / "skills"


@dataclass
class SkillMetadata:
    """Lightweight skill info loaded at startup."""

    name: str
    description: str
    path: Path
    source: SkillSource


@dataclass
class Skill(SkillMetadata):
    """Full skill definition with instructions."""

    instructions: str


def discover_skills() -> list[SkillMetadata]:
    """Discover all available skills from all sources.

    ★ Later sources override earlier ones.
    ★ Returns list of SkillMetadata (lightweight, no instructions loaded).
    """
    skills: dict[str, SkillMetadata] = {}

    for source, directory in [
        ("builtin", BUILTIN_SKILLS_DIR),
        ("user", USER_SKILLS_DIR),
        ("project", PROJECT_SKILLS_DIR),
    ]:
        if not directory.exists():
            continue
        for skill_file in directory.glob("*.md"):
            metadata = _parse_skill_metadata(skill_file, source)  # type: ignore[arg-type]
            if metadata:
                skills[metadata.name] = metadata  # Later sources override

    result = list(skills.values())
    if result:
        logger.debug("Discovered %d skills: %s", len(result), [s.name for s in result])
    return result


def load_skill(name: str) -> Skill | None:
    """Load a skill by name (with full instructions).

    ★ Loads on-demand to avoid reading all files at startup.
    """
    skills = discover_skills()
    metadata = next((s for s in skills if s.name == name), None)
    if metadata is None:
        return None

    try:
        content = metadata.path.read_text(encoding="utf-8")
        _, instructions = _parse_frontmatter(content)
        return Skill(
            name=metadata.name,
            description=metadata.description,
            path=metadata.path,
            source=metadata.source,
            instructions=instructions,
        )
    except Exception:
        logger.exception("Failed to load skill: %s", name)
        return None


def build_skills_section_for_prompt() -> str:
    """Build skills section for system prompt injection."""
    skills = discover_skills()
    if not skills:
        return ""

    lines = [f"- **{s.name}**: {s.description}" for s in skills]
    return (
        "## Available Skills\n\n"
        + "\n".join(lines)
        + "\n\n## Skill Usage Policy\n\n"
        + "- Khi một skill phù hợp với task, hãy gọi nó NGAY LẬP TỨC\n"
        + "- Skills cung cấp workflow chuyên biệt cho các task phức tạp\n"
        + "- Không gọi cùng một skill hai lần cho cùng một query"
    )


def _parse_skill_metadata(path: Path, source: SkillSource) -> SkillMetadata | None:
    """Parse skill metadata from YAML frontmatter."""
    try:
        content = path.read_text(encoding="utf-8")
        frontmatter, _ = _parse_frontmatter(content)
        if not frontmatter:
            return None
        name = frontmatter.get("name", path.stem)
        description = frontmatter.get("description", "")
        if not name or not description:
            return None
        return SkillMetadata(name=name, description=description, path=path, source=source)
    except Exception:
        logger.debug("Failed to parse skill metadata: %s", path)
        return None


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter from Markdown content.

    Returns (frontmatter_dict, body_content).
    """
    if not content.startswith("---"):
        return {}, content

    match = re.match(r"^---\n(.*?)\n---\n(.*)", content, re.DOTALL)
    if not match:
        return {}, content

    frontmatter_str = match.group(1)
    body = match.group(2)

    # Simple YAML key: value parser (no nested structures)
    frontmatter: dict[str, str] = {}
    for line in frontmatter_str.split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            frontmatter[key.strip()] = value.strip().strip('"').strip("'")

    return frontmatter, body
