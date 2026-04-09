"""Tests for the ADS-backed CV generation helpers."""

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

    aliases = ("Malsky, Isaac", "Malsky, I.", "Isaac Malsky")
    return MODULE.CvConfig(
        display_name="Isaac Malsky",
        orcid_id="0000-0003-0217-3880",
        name_aliases=aliases,
        ads_query_suffix="database:astronomy",
        exclude_bibcodes=frozenset(),
        normalized_aliases=frozenset(MODULE.normalize_name(alias) for alias in aliases),
        alias_signatures=frozenset(MODULE.build_author_signature(alias) for alias in aliases),
    )


class GenerateCvTests(unittest.TestCase):
    """Unit tests for deterministic CV helper logic."""

    def test_latex_template_uses_generated_publications_fragment(self) -> None:
        template = (ROOT / "latex" / "academic_cv.tex").read_text(encoding="utf-8")
        self.assertIn("\\input{generated/publications.tex}", template)
        self.assertNotIn("Run \\texttt{python src/generate\\_cv.py}", template)
        self.assertIn("{\\namefont\\color{color2} \\@firstname~\\@lastname}", template)

    def test_pdf_only_generator_removes_site_surface(self) -> None:
        self.assertFalse(hasattr(MODULE, "DEFAULT_SITE_DIR"))
        self.assertFalse(hasattr(MODULE, "render_index_html"))
        self.assertNotIn("scholar_url", MODULE.CvConfig.__annotations__)
        config_text = (ROOT / "src" / "cv_config.toml").read_text(encoding="utf-8")
        self.assertNotIn("scholar_url", config_text)

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
            normalized_aliases=config.normalized_aliases,
            alias_signatures=config.alias_signatures,
        )
        query = MODULE.build_ads_query(config)
        self.assertIn('author:"Malsky, Isaac"', query)
        self.assertIn("database:astronomy", query)

    def test_format_authors_compact_keeps_middle_author_visible(self) -> None:
        config = build_config()
        authors = (
            "Kennedy, T.",
            "Rauscher, E.",
            "Malsky, Isaac",
            "Roman, M.",
            "Beltz, H.",
        )
        rendered = MODULE.format_authors_compact(authors, config, author_position=3)
        self.assertIn("\\textbf{Malsky, I.}", rendered)
        self.assertIn("et al.", rendered)

    def test_render_publications_includes_citation_summary_and_categories(self) -> None:
        publications = [
            MODULE.RenderedPublication(
                sort_date="2025-01-01",
                text="First author paper.",
                category="first_author",
            ),
            MODULE.RenderedPublication(
                sort_date="2024-01-01",
                text="Middle author paper.",
                category="middle_author",
            ),
            MODULE.RenderedPublication(
                sort_date="2023-01-01",
                text="Contributing paper.",
                category="contributing",
            ),
        ]

        rendered = MODULE.render_publications_tex(
            publications,
            MODULE.Metrics(17, 400, 22, 5),
            in_review_count=2,
        )
        self.assertIn("400 total citations", rendered)
        self.assertIn("\\subsection{First Author}", rendered)
        self.assertIn("\\subsection{Other Papers}", rendered)

    def test_compact_author_name_uses_initials(self) -> None:
        self.assertEqual(MODULE.compact_author_name("Malsky, Isaac"), "Malsky, I.")

    def test_is_ads_proposal_record(self) -> None:
        self.assertTrue(MODULE.is_ads_proposal_record("JWST Proposal. Cycle 4"))
        self.assertFalse(MODULE.is_ads_proposal_record("The Astrophysical Journal"))


if __name__ == "__main__":
    unittest.main()
