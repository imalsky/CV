"""Tests for the ADS-backed CV generation helpers."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_cv.py"
SPEC = importlib.util.spec_from_file_location("generate_cv", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def build_config() -> object:
    """Create a minimal config object for helper tests."""

    return MODULE.CvConfig(
        display_name="Isaac Malsky",
        orcid_id="0000-0003-0217-3880",
        name_aliases=("Malsky, Isaac", "Malsky, I.", "Isaac Malsky"),
        ads_query_suffix="database:astronomy",
        exclude_bibcodes=frozenset(),
        section_overrides={},
        normalized_aliases=frozenset(MODULE.normalize_name(alias) for alias in ("Malsky, Isaac", "Malsky, I.", "Isaac Malsky")),
        alias_signatures=frozenset(MODULE.build_author_signature(alias) for alias in ("Malsky, Isaac", "Malsky, I.", "Isaac Malsky")),
    )


class GenerateCvTests(unittest.TestCase):
    """Unit tests for deterministic CV helper logic."""

    def test_compute_h_index(self) -> None:
        self.assertEqual(MODULE.compute_h_index([12, 10, 8, 5, 1]), 4)

    def test_classify_author_section(self) -> None:
        config = build_config()
        authors = ("Rauscher, Eliza", "Kataria, Tiffany", "Malsky, Isaac")
        self.assertEqual(MODULE.classify_author_section(authors, config), "Second, Third or Fourth Author")

    def test_render_publications_orders_entries_newest_first_within_bucket(self) -> None:
        publications = [
            MODULE.RenderedPublication(
                section="First Author",
                sort_date="2024-01-01",
                text="Older first-author paper.",
            ),
            MODULE.RenderedPublication(
                section="First Author",
                sort_date="2025-01-01",
                text="Newer first-author paper.",
            ),
            MODULE.RenderedPublication(
                section="Contributing Author",
                sort_date="2023-01-01",
                text="Collaboration paper.",
            ),
        ]

        rendered = MODULE.render_publications_tex(publications)
        self.assertLess(rendered.find("Newer first-author paper."), rendered.find("Older first-author paper."))
        self.assertLess(rendered.find("First Author"), rendered.find("Contributing Author"))


if __name__ == "__main__":
    unittest.main()
