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
        self.assertIn("\\IfFileExists{generated/software.tex}{\\input{generated/software.tex}}{}", template)
        self.assertNotIn("Run \\texttt{python src/generate\\_cv.py}", template)
        self.assertIn("{\\namefont\\color{color2} \\@firstname~\\@lastname}", template)
        self.assertIn("\\documentclass[11pt,letterpaper,sans]{moderncv}", template)
        self.assertIn("\\usepackage{enumitem}", template)
        self.assertIn("\\newcommand{\\pubheading}[1]", template)
        self.assertIn("\\newcommand{\\pubitem}[1]", template)
        self.assertIn("\\cvitem{2025--present}{Yashnil Mohanty, high school project}", template)
        self.assertNotIn("\\usepackage{newtxtext,newtxmath}", template)

    def test_pdf_only_generator_removes_site_surface(self) -> None:
        self.assertFalse(hasattr(MODULE, "DEFAULT_SITE_DIR"))
        self.assertFalse(hasattr(MODULE, "render_index_html"))
        self.assertNotIn("scholar_url", MODULE.CvConfig.__annotations__)
        config_text = (ROOT / "src" / "cv_config.toml").read_text(encoding="utf-8")
        self.assertNotIn("scholar_url", config_text)

    def test_compute_h_index(self) -> None:
        self.assertEqual(MODULE.compute_h_index([12, 10, 8, 5, 1]), 4)

    def test_sanitize_ads_text_strips_markup_and_normalizes_symbols(self) -> None:
        cleaned = MODULE.sanitize_ads_text("TOI-431 and ν<SUP>2</SUP> Lupi &amp; friends")
        self.assertEqual(cleaned, "TOI-431 and nu2 Lupi & friends")

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

    def test_build_ads_query_includes_orcid_and_aliases(self) -> None:
        query = MODULE.build_ads_query(build_config())
        self.assertIn('orcid:"0000-0003-0217-3880"', query)
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
        self.assertIn("5 published first-author papers, 2 in review,", rendered)
        self.assertIn("400 total citations", rendered)
        self.assertIn("ADS h-index of 17", rendered)
        self.assertIn("\\pubheading{First Author}", rendered)
        self.assertIn("\\pubheading{Contributing Author}", rendered)
        self.assertNotIn("\\cvlistitem{", rendered)
        self.assertIn("\\pubitem{First author paper.}", rendered)

    def test_compute_metrics_counts_only_article_first_author_papers(self) -> None:
        publications = [
            MODULE.AdsPublication(
                bibcode="2025ApJ...1M",
                doctype="article",
                title="Journal paper",
                authors=("Malsky, Isaac",),
                journal="The Astrophysical Journal",
                year="2025",
                sort_date="2025-01-01",
                citation_count=12,
                author_position=1,
            ),
            MODULE.AdsPublication(
                bibcode="2025arXiv..1M",
                doctype="eprint",
                title="Preprint paper",
                authors=("Malsky, Isaac",),
                journal="arXiv e-prints",
                year="2025",
                sort_date="2025-02-01",
                citation_count=3,
                author_position=1,
            ),
            MODULE.AdsPublication(
                bibcode="2024AAS...1M",
                doctype="abstract",
                title="Conference abstract",
                authors=("Malsky, Isaac",),
                journal="Bulletin of the American Astronomical Society",
                year="2024",
                sort_date="2024-01-01",
                citation_count=1,
                author_position=1,
            ),
        ]

        metrics = MODULE.compute_metrics(publications)
        self.assertEqual(metrics.first_author_count, 1)
        self.assertEqual(metrics.total_citations, 16)
        self.assertEqual(metrics.h_index, 2)

    def test_build_publication_entries_skips_ads_titles_already_present_in_manual_entries(self) -> None:
        config = build_config()
        ads_publications = [
            MODULE.AdsPublication(
                bibcode="2025arXiv..1M",
                doctype="eprint",
                title="Accelerating Radiative Transfer for Planetary Atmospheres by Orders of Magnitude with a Transformer-Based Machine Learning Model",
                authors=("Malsky, Isaac", "Kataria, Tiffany"),
                journal="arXiv e-prints",
                year="2025",
                sort_date="2025-02-01",
                citation_count=0,
                author_position=1,
            )
        ]
        manual_publications = [
            MODULE.ManualPublication(
                sort_date="2026-02-01",
                text="\\textbf{Malsky, I.} and Kataria, T. Accelerating Radiative Transfer for Planetary Atmospheres by Orders of Magnitude with a Transformer-Based Machine Learning Model",
                status_label="Submitted to \\emph{ApJ}",
                review_state="submitted",
                category="first_author",
            )
        ]

        rendered = MODULE.build_publication_entries(ads_publications, manual_publications, config)
        self.assertEqual(len(rendered), 1)
        self.assertIn("Submitted to \\emph{ApJ}", rendered[0].text)

    def test_build_software_entries_keeps_ads_software_separate(self) -> None:
        config = build_config()
        software = [
            MODULE.AdsPublication(
                bibcode="2025zndo....1M",
                doctype="software",
                title="ExoRT",
                authors=("Malsky, Isaac", "Kataria, Tiffany"),
                journal="Zenodo",
                year="2025",
                sort_date="2025-02-01",
                citation_count=3,
                author_position=1,
            )
        ]

        rendered = MODULE.build_software_entries(software, config)
        self.assertEqual(len(rendered), 1)
        self.assertEqual(rendered[0].category, "software")
        self.assertIn("ExoRT", rendered[0].text)

    def test_render_software_tex_only_emits_section_when_needed(self) -> None:
        empty_rendered = MODULE.render_software_tex([])
        self.assertEqual(empty_rendered, "")

        rendered = MODULE.render_software_tex(
            [
                MODULE.RenderedPublication(
                    sort_date="2025-02-01",
                    text="Software entry.",
                    category="software",
                )
            ]
        )
        self.assertIn("\\section{Software}", rendered)
        self.assertIn("\\pubitem{Software entry.}", rendered)

    def test_compact_author_name_uses_initials(self) -> None:
        self.assertEqual(MODULE.compact_author_name("Malsky, Isaac"), "Malsky, I.")

    def test_is_ads_proposal_record(self) -> None:
        self.assertTrue(MODULE.is_ads_proposal_record("JWST Proposal. Cycle 4"))
        self.assertFalse(MODULE.is_ads_proposal_record("The Astrophysical Journal"))

    def test_is_ads_meeting_abstract_record(self) -> None:
        self.assertTrue(
            MODULE.is_ads_meeting_abstract_record(
                "American Astronomical Society Meeting Abstracts #245",
                "abstract",
            )
        )
        self.assertTrue(
            MODULE.is_ads_meeting_abstract_record(
                "Bulletin of the American Astronomical Society",
                "article",
            )
        )
        self.assertFalse(
            MODULE.is_ads_meeting_abstract_record(
                "The Astrophysical Journal",
                "article",
            )
        )


if __name__ == "__main__":
    unittest.main()
