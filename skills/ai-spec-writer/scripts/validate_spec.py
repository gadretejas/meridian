#!/usr/bin/env python3
"""
Validate a SPEC.md file for completeness against the six-domain framework.

Usage:
    python validate_spec.py <path/to/SPEC.md>

Exit codes:
    0 - All checks pass
    1 - One or more checks fail

Checks:
    - Presence of all six domain sections
    - Boundaries section has all three tiers (Always, Ask First, Never)
    - Commands section has at least one code block
    - Code Style section has at least one code block
"""

import re
import sys
from pathlib import Path

# Six required domain sections (case-insensitive heading match)
REQUIRED_SECTIONS = [
    ("Commands", r"^#{1,3}\s+Commands\b"),
    ("Testing", r"^#{1,3}\s+Testing\b"),
    ("Project Structure", r"^#{1,3}\s+Project\s+Structure\b"),
    ("Code Style", r"^#{1,3}\s+Code\s+Style\b"),
    ("Git Workflow", r"^#{1,3}\s+Git\s+Workflow\b"),
    ("Boundaries", r"^#{1,3}\s+Boundaries\b"),
]

# Three boundary tiers
BOUNDARY_TIERS = [
    ("Always", r"^#{1,4}\s+Always\b"),
    ("Ask First", r"^#{1,4}\s+Ask\s+First\b"),
    ("Never", r"^#{1,4}\s+Never\b"),
]


def find_section_content(text: str, section_pattern: str) -> str | None:
    """Return the content of a section from its heading to the next same-or-higher level heading."""
    lines = text.split("\n")
    start = None
    start_level = None
    for i, line in enumerate(lines):
        if re.match(section_pattern, line, re.IGNORECASE):
            start = i
            start_level = len(line) - len(line.lstrip("#"))
            break
    if start is None:
        return None
    # Collect until next heading of same or higher level
    content_lines = [lines[start]]
    for line in lines[start + 1 :]:
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            if level <= start_level:
                break
        content_lines.append(line)
    return "\n".join(content_lines)


def has_code_block(text: str) -> bool:
    """Check if text contains at least one fenced code block or inline backtick command."""
    return bool(re.search(r"```[\s\S]*?```", text) or re.search(r"`[^`]+`", text))


def validate(spec_path: str) -> tuple[bool, list[str]]:
    """Validate a SPEC.md file. Returns (all_passed, list of messages)."""
    path = Path(spec_path)
    if not path.exists():
        return False, [f"FAIL: File not found: {spec_path}"]

    text = path.read_text(encoding="utf-8")
    messages: list[str] = []
    all_passed = True

    # Check required sections
    for name, pattern in REQUIRED_SECTIONS:
        if re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
            messages.append(f"  PASS: '{name}' section found")
        else:
            messages.append(f"  FAIL: '{name}' section missing")
            all_passed = False

    # Check boundary tiers
    boundaries = find_section_content(text, r"^#{1,3}\s+Boundaries\b")
    if boundaries:
        for tier_name, tier_pattern in BOUNDARY_TIERS:
            if re.search(tier_pattern, boundaries, re.MULTILINE | re.IGNORECASE):
                messages.append(f"  PASS: Boundary tier '{tier_name}' found")
            else:
                messages.append(f"  FAIL: Boundary tier '{tier_name}' missing")
                all_passed = False
    else:
        for tier_name, _ in BOUNDARY_TIERS:
            messages.append(f"  FAIL: Boundary tier '{tier_name}' missing (no Boundaries section)")
            all_passed = False

    # Check Commands has code block
    commands = find_section_content(text, r"^#{1,3}\s+Commands\b")
    if commands and has_code_block(commands):
        messages.append("  PASS: 'Commands' section has code block")
    elif commands:
        messages.append("  FAIL: 'Commands' section has no code block")
        all_passed = False
    # (if no commands section, already reported above)

    # Check Code Style has code block
    code_style = find_section_content(text, r"^#{1,3}\s+Code\s+Style\b")
    if code_style and has_code_block(code_style):
        messages.append("  PASS: 'Code Style' section has code block")
    elif code_style:
        messages.append("  FAIL: 'Code Style' section has no code block")
        all_passed = False

    return all_passed, messages


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_spec.py <path/to/SPEC.md>")
        sys.exit(1)

    spec_path = sys.argv[1]
    print(f"Validating: {spec_path}\n")

    passed, messages = validate(spec_path)

    for msg in messages:
        print(msg)

    print()
    if passed:
        print("Result: ALL CHECKS PASSED")
        sys.exit(0)
    else:
        print("Result: INCOMPLETE — see FAIL items above")
        sys.exit(1)


if __name__ == "__main__":
    main()
