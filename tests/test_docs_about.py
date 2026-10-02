"""The About page links only to this author's public sites and profiles.

The same page lives in triaina and kinect-forge. This keeps both copies to the
same rule, so a link to a private repository or a stray site fails here.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ABOUT = ROOT / "docs" / "about.md"

ALLOWED = (
    "https://nikolareljin.github.io/",
    "https://github.com/nikolareljin",
    "https://www.linkedin.com/in/nikolareljin",
)


def links() -> list[str]:
    return re.findall(r"\]\(([^)]+)\)", ABOUT.read_text(encoding="utf-8"))


def test_about_links_are_allowed():
    bad = [u for u in links() if not u.startswith(ALLOWED)]
    assert not bad, f"About links outside the allowed sites: {bad}"


def test_about_links_both_siblings():
    found = links()
    for site in ("triaina", "kinect-forge"):
        assert f"https://nikolareljin.github.io/{site}/" in found


def test_about_in_nav():
    nav = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    assert re.search(r"^  - About: about\.md$", nav, re.MULTILINE)
