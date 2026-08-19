#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Generate Kiro Powers from the Agent Skills (SKILL.md is the source of truth).

For each skills/<skill>/SKILL.md this writes powers/<skill>/POWER.md with Kiro frontmatter
(name, displayName, description, keywords, author) derived from the SKILL.md frontmatter, and
copies the skill's references/*.md into powers/<skill>/steering/ so they can be loaded on demand
via Kiro's readSteering. A "## Available Steering Files" section is appended listing them.

This mirrors the pattern in aws-samples/amazon-nova-samples (nova-prompter): edit the SKILL.md,
then re-run this script. Never hand-edit POWER.md.

Usage:
    uv run scripts/sync_powers.py            # regenerate all powers
    uv run scripts/sync_powers.py --check    # exit 1 if any POWER.md is stale (for CI)
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
POWERS_DIR = ROOT / "powers"
AUTHOR = "Adewale Akinfaderin"

GENERATED_HEADER = "<!-- GENERATED from skills/{skill}/SKILL.md by scripts/sync_powers.py. Do not edit by hand; edit the SKILL.md and re-run the script. -->"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split a markdown file into (frontmatter dict, body). Minimal YAML: scalars + folded `>`."""
    if not text.startswith("---"):
        return {}, text
    end = text.index("\n---", 3)
    fm_raw = text[3:end].strip("\n")
    body = text[end + 4:].lstrip("\n")
    fm: dict = {}
    key = None
    buf: list[str] = []

    def flush():
        nonlocal key, buf
        if key is not None:
            fm[key] = " ".join(s.strip() for s in buf).strip()
        key, buf = None, []

    for line in fm_raw.split("\n"):
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m and not line.startswith(" "):
            flush()
            key = m.group(1)
            val = m.group(2)
            if val in (">", "|", ">-", "|-"):
                buf = []
            elif val:
                fm[key] = val.strip()
                key = None
            else:
                buf = []
        elif key is not None:
            buf.append(line)
    flush()
    return fm, body


def keywords_for(name: str, description: str) -> list[str]:
    """Derive activation keywords from the skill name + a fixed AR vocabulary."""
    base = ["automated reasoning", "bedrock", "guardrail", "AR policy"]
    verb = name.replace("ar-policy-", "").replace("ar-", "").replace("-", " ")
    base.insert(0, verb)
    # pull a couple of distinctive API-ish words from the description
    for kw in ["ApplyGuardrail", "INGEST_CONTENT", "annotations", "fidelity", "quality report",
               "rewrite", "Valid@N", "test", "deploy", "scenarios"]:
        if kw.lower() in description.lower() and kw.lower() not in " ".join(base).lower():
            base.append(kw)
    return base[:8]


def display_name(name: str) -> str:
    pretty = name.replace("ar-policy-", "AR ").replace("ar-", "AR ").replace("-", " ")
    return "Automated Reasoning: " + pretty.title().replace("Ar ", "")


def build_power(skill_dir: Path) -> Path | None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return None
    name = skill_dir.name
    fm, body = parse_frontmatter(skill_md.read_text())
    description = re.sub(r"\s+", " ", fm.get("description", "")).strip()
    # Keep the description tight: the capability sentences up to the first "Use ... when" /
    # trigger block (keywords drive Kiro activation, not the long trigger list).
    description = re.split(r"\s+Use this skill\b|\s+Use for\b|\s+Trigger\b|\s+Also trigger\b", description)[0].strip()

    power_dir = POWERS_DIR / name
    power_dir.mkdir(parents=True, exist_ok=True)

    # Copy the skill's own references/ into steering/ (Kiro loads these via readSteering).
    steering_files: list[str] = []
    refs = skill_dir / "references"
    steering = power_dir / "steering"
    if steering.exists():
        shutil.rmtree(steering)
    if refs.exists():
        steering.mkdir(parents=True, exist_ok=True)
        for ref in sorted(refs.glob("*.md")):
            shutil.copy2(ref, steering / ref.name)
            steering_files.append(ref.name)

    kws = ", ".join(f'"{k}"' for k in keywords_for(name, description))
    lines = [
        "---",
        f'name: "{name}"',
        f'displayName: "{display_name(name)}"',
        f'description: "{description}"',
        f"keywords: [{kws}]",
        f'author: "{AUTHOR}"',
        "---",
        "",
        GENERATED_HEADER.format(skill=name),
        "",
        body.rstrip(),
    ]
    if steering_files:
        lines += [
            "",
            "## Available Steering Files",
            "",
        ]
        for sf in steering_files:
            lines.append(f'- **{sf}**: load on demand with `readSteering` (`steeringFile="{sf}"`).')
    out = power_dir / "POWER.md"
    out.write_text("\n".join(lines) + "\n")
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--check", action="store_true", help="Exit 1 if any POWER.md would change (CI mode).")
    args = p.parse_args()

    skill_dirs = sorted(d for d in SKILLS_DIR.iterdir() if (d / "SKILL.md").exists())
    if not skill_dirs:
        sys.exit("No skills found under skills/.")

    stale = []
    for sd in skill_dirs:
        target = POWERS_DIR / sd.name / "POWER.md"
        before = target.read_text() if target.exists() else None
        if args.check:
            # generate to memory by writing then comparing would mutate; instead build + compare
            build_power(sd)
            after = target.read_text()
            if before != after:
                stale.append(sd.name)
        else:
            build_power(sd)
            print(f"wrote powers/{sd.name}/POWER.md")

    if args.check and stale:
        sys.exit(f"Stale POWER.md for: {', '.join(stale)}. Run: uv run scripts/sync_powers.py")
    if not args.check:
        print(f"\nGenerated {len(skill_dirs)} powers. Install with: ./install-powers.sh")


if __name__ == "__main__":
    main()
