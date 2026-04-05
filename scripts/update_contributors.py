import datetime as dt
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README_TARGETS = [path for path in [ROOT / "README.md", ROOT / "astrbot_plugin_sysinfoimg" / "README.md"] if path.exists()]
CONTRIBUTORS_MD = ROOT / "CONTRIBUTORS.md"
START = "<!-- CONTRIBUTORS:START -->"
END = "<!-- CONTRIBUTORS:END -->"


def run_git_shortlog() -> list[tuple[str, int]]:
    result = subprocess.run(
        ["git", "shortlog", "-sne", "--all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    grouped: dict[str, dict[str, object]] = {}
    pattern = re.compile(r"^\s*(\d+)\s+(.+?)\s+<([^>]+)>\s*$")
    for line in result.stdout.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        commits = int(match.group(1))
        name = match.group(2).strip()
        email = match.group(3).strip()
        key = name.casefold()
        if key not in grouped:
            grouped[key] = {"name": name, "email": email, "commits": 0}
        grouped[key]["commits"] = int(grouped[key]["commits"]) + commits
    rows = [(str(item["name"]), int(item["commits"])) for item in grouped.values()]
    rows.sort(key=lambda item: (-item[1], item[0].casefold()))
    return rows


def render_readme_section(rows: list[tuple[str, int]]) -> str:
    if not rows:
        return "- No contributors yet"
    return "\n".join(f"- {name} - {commits} commits" for name, commits in rows)


def replace_between_markers(text: str, replacement: str) -> str:
    if START not in text or END not in text:
        raise RuntimeError("Contributor markers not found in README")
    prefix, rest = text.split(START, 1)
    _, suffix = rest.split(END, 1)
    return f"{prefix}{START}\n{replacement}\n{END}{suffix}"


def write_contributors_md(rows: list[tuple[str, int]]) -> None:
    lines = [
        "# Contributors",
        "",
        f"> Auto-generated from `git shortlog -sne --all` on {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "| Name | Commits |",
        "| --- | ---: |",
    ]
    if rows:
        lines.extend(f"| {name} | {commits} |" for name, commits in rows)
    else:
        lines.append("| None | 0 |")
    CONTRIBUTORS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows = run_git_shortlog()
    replacement = render_readme_section(rows)
    for target in README_TARGETS:
        text = target.read_text(encoding="utf-8-sig")
        target.write_text(replace_between_markers(text, replacement), encoding="utf-8")
    write_contributors_md(rows)


if __name__ == "__main__":
    main()
