#!/usr/bin/env python3
"""Validate and package skills from skills/ into distributable .skill bundles.

A .skill file is a zip archive whose single top-level entry is the skill folder,
containing SKILL.md plus any references/, scripts/ or assets/.

Usage:
    py scripts/package_skill.py                 # validate + package every skill
    py scripts/package_skill.py git-commits     # one skill
    py scripts/package_skill.py --check         # validate only, build nothing
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
DIST_DIR = REPO_ROOT / "dist"

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_NAME = 64
MAX_DESCRIPTION = 1024
EXCLUDED = {".git", ".DS_Store", "__pycache__", "Thumbs.db"}


def parse_frontmatter(skill_md: Path) -> dict[str, str]:
    """Pull the top-level scalar keys out of a SKILL.md YAML frontmatter block."""
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError("SKILL.md does not start with a '---' frontmatter block")
    end = text.find("\n---", 3)
    if end == -1:
        raise ValueError("unterminated frontmatter block")
    fields: dict[str, str] = {}
    key = None
    for line in text[3:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match:
            key, value = match.group(1), match.group(2).strip()
            fields[key] = value.strip("'\"")
        elif key and line.startswith((" ", "\t")):
            fields[key] = f"{fields[key]} {line.strip()}".strip()
    return fields


def validate(skill_dir: Path) -> list[str]:
    errors = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{skill_dir.name}: no SKILL.md"]
    try:
        fields = parse_frontmatter(skill_md)
    except ValueError as exc:
        return [f"{skill_dir.name}: {exc}"]

    name = fields.get("name", "")
    description = fields.get("description", "")
    if not name:
        errors.append(f"{skill_dir.name}: frontmatter is missing 'name'")
    else:
        if name != skill_dir.name:
            errors.append(f"{skill_dir.name}: frontmatter name '{name}' != folder name")
        if not NAME_RE.match(name):
            errors.append(f"{skill_dir.name}: name must be lowercase-with-hyphens")
        if len(name) > MAX_NAME:
            errors.append(f"{skill_dir.name}: name exceeds {MAX_NAME} characters")
    if not description:
        errors.append(f"{skill_dir.name}: frontmatter is missing 'description'")
    elif len(description) > MAX_DESCRIPTION:
        errors.append(
            f"{skill_dir.name}: description is {len(description)} chars, "
            f"max {MAX_DESCRIPTION}"
        )
    return errors


def package(skill_dir: Path) -> Path:
    DIST_DIR.mkdir(exist_ok=True)
    target = DIST_DIR / f"{skill_dir.name}.skill"
    files = sorted(
        path
        for path in skill_dir.rglob("*")
        if path.is_file() and not EXCLUDED & set(path.relative_to(skill_dir).parts)
    )
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in files:
            bundle.write(path, Path(skill_dir.name) / path.relative_to(skill_dir))
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skills", nargs="*", help="skill folder names (default: all)")
    parser.add_argument(
        "--check", action="store_true", help="validate only, do not build bundles"
    )
    args = parser.parse_args()

    if args.skills:
        selected = [SKILLS_DIR / name for name in args.skills]
        missing = [d.name for d in selected if not d.is_dir()]
        if missing:
            print(f"error: no such skill(s): {', '.join(missing)}", file=sys.stderr)
            return 2
    else:
        selected = sorted(d for d in SKILLS_DIR.iterdir() if d.is_dir())

    errors = [error for skill_dir in selected for error in validate(skill_dir)]
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"validated {len(selected)} skill(s)")
    if args.check:
        return 0
    for skill_dir in selected:
        target = package(skill_dir)
        size_kb = target.stat().st_size / 1024
        print(f"  {target.relative_to(REPO_ROOT)}  ({size_kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
