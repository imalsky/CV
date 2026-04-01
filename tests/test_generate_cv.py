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

    aliases = ("Malsky, Isaac", "Malsky, I.", "Isaac Malsky")
    return MODULE.CvConfig(
        display_name="Isaac Malsky",
        orcid_id="0000-0003-0217-3880",
        name_aliases=aliases,
        ads_query_suffix="database:astronomy",
        exclude_bibcodes=frozenset(),
        scholar_url="https://scholar.google.com/citations?user=8UH3LhoAAAAJ",
        normalized_aliases=frozenset(MODULE.normalize_name(alias) for alias in aliases),
        alias_signatures=frozenset(MODULE.build_author_signature(alias) for alias in aliases),
    )


class GenerateCvTests(unittest.TestCase):
    """Unit tests for deterministic CV helper logic."""

    def test_compute_h_index(self) -> None:
        self.assertEqual(MODULE.compute_h_index([12, 10, 8, 5, 1]), 4)

    def test_find_author_position(self) -> None:
        config = build_config()
        authors = ("Rauscher, Eliza", "Kataria, Tiffany", "Malsky, Isaac")
        self.assertEqual(MODULE.find_author_position(authors, config), 3)

    def test_build_ads_query_falls_back_to_aliases(self) -> None:
        config = build_config()
        config = MODULE.CvConfig(
            display_name=config.display_name,
            orcid_id="",
            name_aliases=config.name_aliases,
            ads_query_suffix=config.ads_query_suffix,
            exclude_bibcodes=config.exclude_bibcodes,
            scholar_url=config.scholar_url,
            normalized_aliases=config.normalized_aliases,
            alias_signatures=config.alias_signatures,
        )
        query = MODULE.build_ads_query(config)
        self.assertIn('author:"Malsky, Isaac"', query)
        self.assertIn("database:astronomy", query)

    def test_render_selected_research_orders_entries_newest_first(self) -> None:
        publications = [
            MODULE.RenderedPublication(
                sort_date="2024-01-01",
                text="Older paper.",
            ),
            MODULE.RenderedPublication(
                sort_date="2025-01-01",
                text="Newer paper.",
            ),
        ]

        rendered = MODULE.render_selected_research_tex(
            publications,
            MODULE.Metrics(17, 400, 22, 5),
            in_review_count=2,
        )
        self.assertIn("5 published first-author papers, 2 in review, and an ADS h-index of 17.", rendered)
        self.assertLess(rendered.find("Newer paper."), rendered.find("Older paper."))


if __name__ == "__main__":
    unittest.main()
