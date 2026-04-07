"""Tests for Marianne's Scholar-backed CV generator."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "generate_cv.py"
SPEC = importlib.util.spec_from_file_location("generate_cv", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def build_config() -> object:
    """Create a minimal config object for helper tests."""

    aliases = ("Cowherd, Marianne", "Cowherd, M.", "Marianne Cowherd")
    return MODULE.CvConfig(
        display_name="Marianne Cowherd",
        scholar_url="https://scholar.google.com/citations?user=RN_5PCcAAAAJ",
        scholar_user_id="RN_5PCcAAAAJ",
        name_aliases=aliases,
        excluded_title_slugs=frozenset({MODULE.normalize_title("Prediction of human population responses to toxic compounds by a collaborative competition")}),
        normalized_aliases=frozenset(MODULE.normalize_text(alias) for alias in aliases),
        alias_signatures=frozenset(MODULE.build_author_signature(alias) for alias in aliases),
    )


class GenerateCvTests(unittest.TestCase):
    """Unit tests for deterministic CV helper logic."""

    def test_compute_h_index(self) -> None:
        self.assertEqual(MODULE.compute_h_index([20, 12, 3, 1]), 3)

    def test_extract_scholar_user_id(self) -> None:
        self.assertEqual(
            MODULE.extract_scholar_user_id("https://scholar.google.com/citations?user=RN_5PCcAAAAJ&hl=en"),
            "RN_5PCcAAAAJ",
        )

    def test_find_author_position(self) -> None:
        config = build_config()
        authors = ("Manuela Girotto", "Claire Bachand", "Marianne Cowherd")
        self.assertEqual(MODULE.find_author_position(authors, config), 3)

    def test_compact_author_name_uses_initials(self) -> None:
        self.assertEqual(MODULE.compact_author_name("Marianne Cowherd"), "Cowherd, M.")

    def test_build_publication_entries_applies_override_and_manual_heading(self) -> None:
        config = build_config()
        fixture_publications = MODULE.load_fixture_publications(ROOT / "tests" / "fixtures" / "scholar_publications.json")
        manual_data = MODULE.load_manual_publications(ROOT / "src" / "manual_publications.toml")

        included_publications = [
            publication
            for publication in fixture_publications
            if publication.title_slug not in config.excluded_title_slugs
        ]

        published_entries, manual_entries = MODULE.build_publication_entries(included_publications, manual_data, config)
        rendered = MODULE.render_publications_tex(published_entries, manual_data.manual_heading, manual_entries)
        expected = (ROOT / "tests" / "fixtures" / "expected_publications.tex").read_text(encoding="utf-8")
        self.assertEqual(rendered, expected)

    def test_format_scholar_publication_falls_back_to_auto_render(self) -> None:
        config = build_config()
        publication = MODULE.ScholarPublication(
            title="New peer-reviewed snow paper",
            title_slug=MODULE.normalize_title("New peer-reviewed snow paper"),
            authors=("Marianne Cowherd", "Daniel Feldman"),
            journal="Journal of Snow Science",
            citation_text="Journal of Snow Science 12 (3), 1-9, 2026",
            year="2026",
            sort_date="2026-01-01",
            citation_count=4,
            author_position=1,
            pub_url="https://example.com/snow-paper",
        )

        rendered = MODULE.format_scholar_publication(publication, config)
        self.assertIn("\\textbf{Cowherd, M.}", rendered)
        self.assertIn("\\textit{Journal of Snow Science}.", rendered)
        self.assertNotIn("\\url{https://example.com/snow-paper}", rendered)

    def test_is_abstract_publication(self) -> None:
        self.assertTrue(
            MODULE.is_abstract_publication(
                "AGU Fall Meeting Abstracts",
                "AGU Fall Meeting Abstracts 2024",
                "https://ui.adsabs.harvard.edu/abs/2024AGUFMC21E.0395C/abstract",
            )
        )
        self.assertTrue(
            MODULE.is_abstract_publication(
                "21st Conference on Mountain Meteorology",
                "21st Conference on Mountain Meteorology",
                "https://scholar.google.com/scholar?cluster=123",
            )
        )
        self.assertFalse(
            MODULE.is_abstract_publication(
                "Environmental Research Letters",
                "Environmental Research Letters 18 (7), 2023",
                "https://doi.org/10.1088/1748-9326/acd804",
            )
        )

    def test_unmatched_override_raises(self) -> None:
        config = build_config()
        scholar_publications = [
            MODULE.ScholarPublication(
                title="Completely different title",
                title_slug=MODULE.normalize_title("Completely different title"),
                authors=("Marianne Cowherd",),
                journal="Journal",
                citation_text="Journal, 2026",
                year="2026",
                sort_date="2026-01-01",
                citation_count=0,
                author_position=1,
                pub_url="",
            )
        ]
        manual_data = MODULE.ManualData(
            manual_heading="",
            published_overrides={
                MODULE.normalize_title("Expected title"): MODULE.PublishedOverride(
                    match_title="Expected title",
                    title_slug=MODULE.normalize_title("Expected title"),
                    text="Override text",
                    append_text="",
                    sort_date="2026-01-01",
                )
            },
            manual_entries=[],
        )

        with self.assertRaises(RuntimeError):
            MODULE.build_publication_entries(scholar_publications, manual_data, config)


if __name__ == "__main__":
    unittest.main()
