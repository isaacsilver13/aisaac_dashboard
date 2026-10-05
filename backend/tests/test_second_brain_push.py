import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import second_brain_push as sbp  # noqa: E402

REDACTOR = """import re
SECRETS = [re.compile(r"\\bsk-[A-Za-z0-9]{16,}")]
OPAQUE = re.compile(r"[A-Za-z0-9_\\-]{24,}")
def redact(s):
    for p in SECRETS:
        s = p.sub("[REDACTED]", s)
    return s
"""


def _vault(tmp_path, body):
    (tmp_path / "inbox" / "tools").mkdir(parents=True, exist_ok=True)
    (tmp_path / "inbox" / "tools" / "extract_sessions.py").write_text(REDACTOR)
    (tmp_path / "wikis" / "apps").mkdir(parents=True, exist_ok=True)
    (tmp_path / "wikis" / "apps" / "index.md").write_text(
        '---\ntitle: "Apps"\naliases: ["Apps", app list]\nstatus: draft\n---\n' + body
    )
    return tmp_path


def test_parse_and_load(tmp_path):
    notes = sbp.load_vault(_vault(tmp_path, "see [[App List]] and [[Nope]]"))
    assert notes[0]["path"] == "wikis/apps/index.md"
    assert notes[0]["aliases"] == ["Apps", "app list"] and notes[0]["status"] == "draft"
    assert sbp.broken_links(notes, tmp_path) == 1


def test_leak_detected_but_prose_is_not(tmp_path):
    clean = sbp.load_vault(_vault(tmp_path, "the token is unset; --token cap"))
    assert sbp.leaks(clean, tmp_path) == []
    dirty = sbp.load_vault(_vault(tmp_path, "key sk-abcdefghijklmnopqrstuvwx1234"))
    assert sbp.leaks(dirty, tmp_path) == ["wikis/apps/index.md"]


def test_frontmatter_forwarded_without_the_fields_stored_elsewhere(tmp_path):
    vault = _vault(tmp_path, "body")
    (vault / "wikis" / "apps" / "index.md").write_text(
        '---\ntype: wiki-index\ntitle: "Apps"\naliases: [Apps]\nstatus: draft\n'
        "updated: 2026-10-02\n---\nbody"
    )
    note = sbp.load_vault(vault)[0]
    assert note["frontmatter"] == {"type": "wiki-index", "updated": "2026-10-02"}
