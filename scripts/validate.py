#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys
import tomllib


MAX_NF_LINES = 220
MAX_BYTES = 24000

RELATIVE_RUNTIME = (
    Path("skills/development-pipeline-v2/SKILL.md"),
    Path("skills/development-pipeline-v2/agents/openai.yaml"),
    Path("agents/dp-v2-implementer.toml"),
    Path("agents/dp-v2-reviewer.toml"),
    Path("agents/dp-v2-verifier.toml"),
)


def fail(message):
    raise ValueError(message)


def read_regular(path):
    if path.is_symlink() or not path.is_file():
        fail(f"not a regular non-symlink file: {path}")
    return path.read_text(encoding="utf-8")


def parse_simple_yaml(text):
    result = {}
    section = None
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        key, separator, raw_value = raw_line.strip().partition(":")
        if not separator:
            fail(f"invalid YAML line: {raw_line!r}")
        if indent == 0:
            section = key
            result[section] = {}
            if raw_value.strip():
                fail(f"top-level scalar is not supported: {raw_line!r}")
            continue
        if indent != 2 or section is None:
            fail(f"unsupported YAML shape: {raw_line!r}")
        value = raw_value.strip()
        if value == "true":
            parsed = True
        elif value == "false":
            parsed = False
        elif len(value) >= 2 and value[0] == value[-1] == '"':
            parsed = value[1:-1]
        else:
            parsed = value
        result[section][key] = parsed
    return result


def parse_frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        fail("SKILL.md frontmatter must start with ---")
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise ValueError("SKILL.md frontmatter is not closed") from error
    data = {}
    for line in lines[1:end]:
        key, separator, value = line.partition(":")
        if not separator:
            fail(f"invalid frontmatter line: {line!r}")
        data[key.strip()] = value.strip()
    return data


def require_markers(text, markers, label):
    missing = [marker for marker in markers if marker not in text]
    if missing:
        fail(f"{label} missing markers: {missing}")


def validate(root, installed):
    runtime = {relative: root / relative for relative in RELATIVE_RUNTIME}
    texts = {relative: read_regular(path) for relative, path in runtime.items()}

    skill_root = root / "skills/development-pipeline-v2"
    actual_skill_files = sorted(
        path.relative_to(skill_root).as_posix()
        for path in skill_root.rglob("*")
        if path.is_file()
    )
    if actual_skill_files != ["SKILL.md", "agents/openai.yaml"]:
        fail(f"unexpected Skill files: {actual_skill_files}")

    skill_text = texts[Path("skills/development-pipeline-v2/SKILL.md")]
    frontmatter = parse_frontmatter(skill_text)
    if frontmatter.get("name") != "development-pipeline-v2":
        fail("unexpected Skill name")
    if "explicitly invokes" not in frontmatter.get("description", ""):
        fail("Skill description must discriminate explicit invocation")

    yaml_text = texts[Path("skills/development-pipeline-v2/agents/openai.yaml")]
    yaml_data = parse_simple_yaml(yaml_text)
    if yaml_data.get("policy", {}).get("allow_implicit_invocation") is not False:
        fail("allow_implicit_invocation must be boolean false")

    expected_agents = {
        Path("agents/dp-v2-implementer.toml"): ("dp-v2-implementer", "workspace-write"),
        Path("agents/dp-v2-reviewer.toml"): ("dp-v2-reviewer", "read-only"),
        Path("agents/dp-v2-verifier.toml"): ("dp-v2-verifier", "workspace-write"),
    }
    agents = {}
    for relative, expected in expected_agents.items():
        data = tomllib.loads(texts[relative])
        if (data.get("name"), data.get("sandbox_mode")) != expected:
            fail(f"unexpected agent identity: {relative}")
        instructions = data.get("developer_instructions")
        if not isinstance(instructions, str) or not instructions.strip():
            fail(f"missing developer_instructions: {relative}")
        agents[relative] = instructions

    require_markers(
        skill_text,
        (
            "$development-pipeline-v2",
            "AUDITED_FULL_ACCESS",
            "payload_id",
            "candidate_cycle=none",
            "cycle_effect=NONE|FORM_CANDIDATE",
            "CHARACTERIZE",
            "deadline-exceeded",
            "DESIGN_NOT_ACCEPTED",
            "CANDIDATE_NOT_ACCEPTED",
        ),
        "SKILL.md",
    )
    require_markers(
        agents[Path("agents/dp-v2-implementer.toml")],
        ("RED|CHARACTERIZE|GREEN|FIX", "PASS or BLOCKED", "payload_id", "cycle_effect"),
        "implementer",
    )
    require_markers(
        agents[Path("agents/dp-v2-reviewer.toml")],
        ("DESIGN or CANDIDATE", "PASS, VALID_FINDINGS, or BLOCKED", "design_id", "payload_id"),
        "reviewer",
    )
    require_markers(
        agents[Path("agents/dp-v2-verifier.toml")],
        ("BASELINE, RED, or FULL", "PASS, FAIL_CANDIDATE, or BLOCKED", "counterfactual", "payload_id"),
        "verifier",
    )

    total_bytes = sum(path.stat().st_size for path in runtime.values())
    total_nf_lines = sum(
        1 for text in texts.values() for line in text.splitlines() if line.strip()
    )
    if total_bytes > MAX_BYTES:
        fail(f"runtime byte budget exceeded: {total_bytes} > {MAX_BYTES}")
    if total_nf_lines > MAX_NF_LINES:
        fail(f"runtime line budget exceeded: {total_nf_lines} > {MAX_NF_LINES}")

    combined = "\n".join(texts.values()).lower()
    for forbidden in ("ponytail", "superpowers"):
        if forbidden in combined:
            fail(f"forbidden dependency/reference: {forbidden}")

    if not installed:
        spec = read_regular(root / "docs/development-pipeline-v2-spec.md")
        if "状态：`Accepted`" not in spec:
            fail("spec is not Accepted")

    return {
        "installed": installed,
        "runtime_files": len(runtime),
        "nf_lines": total_nf_lines,
        "bytes": total_bytes,
        "explicit_only": True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--installed", type=Path)
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    root = args.installed.expanduser().resolve() if args.installed else repo_root
    try:
        result = validate(root, installed=args.installed is not None)
    except (OSError, ValueError, tomllib.TOMLDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": True, **result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
