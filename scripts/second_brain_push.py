"""Push the second-brain Obsidian vault (notes + card figures) to the dashboard.

Syncs wikis/, knowledge/, projects/ and questions/ (never inbox/ or sources/). Aborts if any
note trips the vault's own secret redactor, so a leaked key is never uploaded.

    python scripts/second_brain_push.py [--dry-run]
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import push_common  # noqa: E402

FOLDERS = ("wikis", "knowledge", "projects", "questions")
FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.S)
LONG_RUN = re.compile(r"[A-Za-z0-9_\-]{20,}")
WIKILINK = re.compile(r"\[\[([^\]|#]+)")


def parse(text: str) -> tuple[dict[str, str], str]:
    """Frontmatter as flat strings (enough for title/status/aliases) plus the body."""
    m = FRONTMATTER.match(text)
    if not m:
        return {}, text
    fm = dict(
        (k.strip(), v.strip())
        for k, _, v in (line.partition(":") for line in m.group(1).splitlines())
        if k.strip() and not k.startswith(" ")
    )
    return fm, text[m.end() :]


def aliases_of(raw: str) -> list[str]:
    return [a.strip().strip("\"'") for a in raw.strip("[]").split(",") if a.strip()]


def load_vault(vault: Path) -> list[dict]:
    notes = []
    for folder in FOLDERS:
        for f in sorted((vault / folder).rglob("*.md")):
            fm, body = parse(f.read_text(encoding="utf-8-sig"))
            title = fm.get("title", f.stem).strip("\"'")
            notes.append(
                {
                    "path": f.relative_to(vault).as_posix(),
                    "folder": folder,
                    "title": title,
                    "aliases": aliases_of(fm.get("aliases", "")) or [title],
                    "status": fm.get("status"),
                    "frontmatter": {
                        k: v for k, v in fm.items() if k not in ("title", "aliases", "status")
                    },
                    "body": body,
                }
            )
    return notes


def broken_links(notes: list[dict], vault: Path) -> int:
    """Wikilinks matching no title, alias or filename anywhere in the vault (sources/ included)."""
    known = set()
    for f in vault.rglob("*.md"):
        fm, _ = parse(f.read_text(encoding="utf-8-sig"))
        known |= {f.stem.lower(), fm.get("title", "").strip("\"'").lower()}
        known |= {a.lower() for a in aliases_of(fm.get("aliases", ""))}
    return sum(
        1
        for n in notes
        for target in WIKILINK.findall(n["body"])
        if target.strip().lower() not in known
    )


def leaks(notes: list[dict], vault: Path) -> list[str]:
    """Paths with a credential-shaped blob: a vault-redactor match holding a 20+ char opaque run.

    Requiring the long run skips the redactor's prose hits ("token is unset", "--token cap").
    """
    tool = vault / "inbox" / "tools" / "extract_sessions.py"
    spec = importlib.util.spec_from_file_location("vault_redactor", tool)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    patterns = [*module.SECRETS, module.OPAQUE]
    return [
        n["path"]
        for n in notes
        if any(
            LONG_RUN.search(m.group(0)) and module.redact(m.group(0)) != m.group(0)
            for pat in patterns
            for m in pat.finditer(n["body"])
        )
    ]


def last_commit(vault: Path) -> str:
    out = subprocess.run(
        ["git", "-C", str(vault), "log", "-1", "--format=%h %cs %s"],
        capture_output=True,
        text=True,
    )
    return out.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = push_common.load_config()
    vault = Path(config.get("SECOND_BRAIN_PATH") or Path.home() / "second-brain")
    notes = load_vault(vault)
    if bad := leaks(notes, vault):
        print(
            "Refusing to push; possible secrets in:", *bad, sep="\n  ", file=sys.stderr
        )
        return 1
    meta = {
        "last_commit": last_commit(vault),
        "drafts": sum(1 for n in notes if n["status"] == "draft"),
        "broken_links": broken_links(notes, vault),
        "wiki_topics": sorted(
            {n["path"].split("/")[1] for n in notes if n["folder"] == "wikis"}
        ),
    }
    print(f"{len(notes)} notes; {meta}")
    if args.dry_run:
        return 0
    if not push_common.post_json(
        "/internal/second-brain/sync",
        {"meta": meta, "notes": notes},
        config,
        timeout=60,
    ):
        print("Push failed (check URL/secret)", file=sys.stderr)
        return 1
    print("Pushed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
