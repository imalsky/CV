#!/usr/bin/env python3
"""Generate ADS-backed LaTeX fragments and a minimal GitHub Pages site."""

from __future__ import annotations

import argparse
import html
import os
import re
import sys
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = ROOT / "cv_config.toml"
DEFAULT_MANUAL_PATH = ROOT / "manual_publications.toml"
DEFAULT_GENERATED_DIR = ROOT / "generated"
DEFAULT_SITE_DIR = ROOT / "site"
ALLOWED_SECTIONS: tuple[str, ...] = (
    "First Author",
    "Second, Third or Fourth Author",
    "Contributing Author",
)
NON_ALPHANUMERIC_PATTERN = re.compile(r"[^a-z0-9]+")
LATEX_ESCAPE_MAP = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


@dataclass(frozen=True)
class CvConfig:
    """Static configuration for the ADS-backed CV build."""

    display_name: str
    orcid_id: str
    name_aliases: tuple[str, ...]
    ads_query_suffix: str
    exclude_bibcodes: frozenset[str]
    section_overrides: dict[str, str]
    normalized_aliases: frozenset[str]
    alias_signatures: frozenset[tuple[str, str]]


@dataclass(frozen=True)
class AdsPublication:
    """A publication record fetched from ADS."""

    bibcode: str
    title: str
    authors: tuple[str, ...]  # shape: (n_authors,)
    journal: str
    year: str
    sort_date: str
    citation_count: int
    doi: tuple[str, ...]
    identifiers: tuple[str, ...]
    section: str


@dataclass(frozen=True)
class ManualPublication:
    """A manually curated publication entry."""

    section: str
    sort_date: str
    text: str
    status: str
    notes: str


@dataclass(frozen=True)
class RenderedPublication:
    """A publication entry ready to write into TeX."""

    section: str
    sort_date: str
    text: str


@dataclass(frozen=True)
class Metrics:
    """Computed ADS metrics for the CV header and site."""

    h_index: int
    total_citations: int
    indexed_papers: int
    first_author_count: int


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--manual", type=Path, default=DEFAULT_MANUAL_PATH)
    parser.add_argument("--generated-dir", type=Path, default=DEFAULT_GENERATED_DIR)
    parser.add_argument("--site-dir", type=Path, default=DEFAULT_SITE_DIR)
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Do not fail when the ADS query returns zero indexed papers.",
    )
    return parser.parse_args(argv)


def load_toml(path: Path) -> dict[str, Any]:
    """Load a TOML file from disk."""

    if not path.exists():
        raise RuntimeError(f"Missing required file: {path}")

    with path.open("rb") as file_handle:
        return tomllib.load(file_handle)


def normalize_name(value: str) -> str:
    """Normalize a name string for robust comparisons."""

    return NON_ALPHANUMERIC_PATTERN.sub("", value.casefold())


def escape_tex(value: str) -> str:
    """Escape LaTeX control characters in ADS-provided text."""

    return "".join(LATEX_ESCAPE_MAP.get(character, character) for character in value)


def build_author_signature(value: str) -> tuple[str, str]:
    """Convert an author string into a comparable surname/initial signature."""

    stripped = value.strip()
    if not stripped:
        return ("", "")

    if "," in stripped:
        surname, given_names = stripped.split(",", 1)
    else:
        parts = stripped.split()
        if len(parts) == 1:
            return (normalize_name(parts[0]), "")
        surname = parts[-1]
        given_names = " ".join(parts[:-1])

    initials = "".join(token[0] for token in re.findall(r"[A-Za-z]+", given_names))
    return (normalize_name(surname), initials.casefold())


def load_config(path: Path) -> CvConfig:
    """Load and validate the checked-in CV configuration."""

    raw_config = load_toml(path)

    display_name = str(raw_config.get("display_name", "")).strip()
    orcid_id = str(raw_config.get("orcid_id", "")).strip()
    name_aliases = tuple(str(alias).strip() for alias in raw_config.get("name_aliases", []) if str(alias).strip())
    ads_query_suffix = str(raw_config.get("ads_query_suffix", "")).strip()
    exclude_bibcodes = frozenset(
        str(bibcode).strip() for bibcode in raw_config.get("exclude_bibcodes", []) if str(bibcode).strip()
    )
    raw_overrides = raw_config.get("section_overrides", {})
    section_overrides = {
        str(bibcode).strip(): str(section).strip()
        for bibcode, section in raw_overrides.items()
        if str(bibcode).strip()
    }

    if not display_name:
        raise RuntimeError(f"`display_name` must be set in {path}")
    if not orcid_id:
        raise RuntimeError(f"`orcid_id` must be set in {path}")
    if not name_aliases:
        raise RuntimeError(f"`name_aliases` must contain at least one alias in {path}")

    for bibcode, section in section_overrides.items():
        if section not in ALLOWED_SECTIONS:
            raise RuntimeError(
                f"Invalid section override for {bibcode!r}: {section!r}. "
                f"Expected one of {ALLOWED_SECTIONS}."
            )

    normalized_aliases = frozenset(normalize_name(alias) for alias in name_aliases)
    alias_signatures = frozenset(build_author_signature(alias) for alias in name_aliases)

    return CvConfig(
        display_name=display_name,
        orcid_id=orcid_id,
        name_aliases=name_aliases,
        ads_query_suffix=ads_query_suffix,
        exclude_bibcodes=exclude_bibcodes,
        section_overrides=section_overrides,
        normalized_aliases=normalized_aliases,
        alias_signatures=alias_signatures,
    )


def load_manual_publications(path: Path) -> list[ManualPublication]:
    """Load manual publication entries that should always stay in the CV."""

    raw_manual = load_toml(path)
    entries: list[ManualPublication] = []

    for entry in raw_manual.get("entries", []):
        section = str(entry.get("section", "")).strip()
        sort_date = str(entry.get("sort_date", "")).strip()
        text = str(entry.get("text", "")).strip()
        status = str(entry.get("status", "")).strip()
        notes = str(entry.get("notes", "")).strip()

        if section not in ALLOWED_SECTIONS:
            raise RuntimeError(
                f"Invalid manual publication section {section!r} in {path}. "
                f"Expected one of {ALLOWED_SECTIONS}."
            )
        if not sort_date:
            raise RuntimeError(f"Manual publication entries in {path} require `sort_date`.")
        if not text:
            raise RuntimeError(f"Manual publication entries in {path} require `text`.")

        entries.append(
            ManualPublication(
                section=section,
                sort_date=sort_date,
                text=text,
                status=status,
                notes=notes,
            )
        )

    return entries


def build_ads_query(config: CvConfig) -> str:
    """Build the ADS query string from the checked-in config."""

    query = f'orcid:"{config.orcid_id}"'
    if config.ads_query_suffix:
        query = f"{query} {config.ads_query_suffix}"
    return query


def require_ads_token() -> str:
    """Return the ADS token or fail with a clear setup message."""

    token = os.environ.get("ADS_DEV_KEY", "").strip()
    if not token:
        raise RuntimeError(
            "Missing ADS_DEV_KEY. Create an ADS API token and add it as the "
            "`ADS_DEV_KEY` environment variable or GitHub Actions secret."
        )
    return token


def first_text(value: Any) -> str:
    """Return the first textual value from a scalar or sequence."""

    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return str(value[0]).strip() if value else ""
    return str(value).strip()


def list_text(value: Any) -> tuple[str, ...]:
    """Normalize ADS scalar-or-sequence values into a tuple of strings."""

    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    scalar = str(value).strip()
    return (scalar,) if scalar else ()


def parse_sort_date(pubdate: str, year: str) -> str:
    """Convert ADS date fields into a sortable YYYY-MM-DD string."""

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", pubdate):
        return pubdate
    if re.fullmatch(r"\d{4}-\d{2}", pubdate):
        return f"{pubdate}-01"
    if re.fullmatch(r"\d{4}", pubdate):
        return f"{pubdate}-01-01"
    if re.fullmatch(r"\d{4}", year):
        return f"{year}-01-01"
    return "1900-01-01"


def author_matches(author: str, config: CvConfig) -> bool:
    """Return True when an ADS author string matches the configured researcher."""

    normalized_author = normalize_name(author)
    if normalized_author in config.normalized_aliases:
        return True

    surname, initials = build_author_signature(author)
    if not surname:
        return False

    return (surname, initials) in config.alias_signatures


def classify_author_section(authors: Sequence[str], config: CvConfig) -> str | None:
    """Bucket a paper by author position using the agreed CV rules."""

    for index, author in enumerate(authors, start=1):
        if not author_matches(author, config):
            continue
        if index == 1:
            return "First Author"
        if 2 <= index <= 4:
            return "Second, Third or Fourth Author"
        return "Contributing Author"
    return None


def format_authors_for_tex(authors: Sequence[str], config: CvConfig) -> str:
    """Render an ADS author list with the CV owner highlighted in bold."""

    rendered_authors: list[str] = []
    for author in authors:
        escaped_author = escape_tex(author)
        if author_matches(author, config):
            rendered_authors.append(f"\\textbf{{{escaped_author}}}")
        else:
            rendered_authors.append(escaped_author)
    return ", ".join(rendered_authors)


def ensure_terminal_punctuation(value: str) -> str:
    """Add a trailing period when a fragment does not already end with punctuation."""

    if not value:
        return value
    if value.endswith((".", "?", "!")):
        return value
    return f"{value}."


def render_ads_publication_text(publication: AdsPublication, config: CvConfig) -> str:
    """Render an ADS publication as a custom TeX sentence, not a BibTeX item."""

    authors_tex = format_authors_for_tex(publication.authors, config)
    title_tex = ensure_terminal_punctuation(escape_tex(publication.title))
    journal_tex = ensure_terminal_punctuation(escape_tex(publication.journal))
    year_fragment = f" ({publication.year})." if publication.year else ""
    journal_fragment = f" {journal_tex}" if journal_tex else ""
    return f"{authors_tex}. {title_tex}{year_fragment}{journal_fragment}".strip()


def format_manual_text(publication: ManualPublication) -> str:
    """Append optional status and notes to a manual TeX publication string."""

    fragments = [publication.text]
    if publication.status:
        fragments.append(publication.status)
    if publication.notes:
        fragments.append(publication.notes)
    return " ".join(fragment.strip() for fragment in fragments if fragment.strip())


def fetch_ads_publications(config: CvConfig) -> list[AdsPublication]:
    """Query ADS and return the publications that belong in the CV."""

    require_ads_token()

    try:
        import ads
    except ImportError as exc:
        raise RuntimeError(
            "The `ads` package is not installed. Run `pip install -r requirements.txt` first."
        ) from exc

    field_list = [
        "author",
        "bibcode",
        "citation_count",
        "doi",
        "identifier",
        "pub",
        "pubdate",
        "title",
        "year",
    ]
    query = ads.SearchQuery(
        q=build_ads_query(config),
        fl=field_list,
        rows=200,
        sort="date desc, bibcode desc",
    )

    publications: list[AdsPublication] = []
    seen_bibcodes: set[str] = set()

    for result in query:
        bibcode = first_text(getattr(result, "bibcode", ""))
        if not bibcode or bibcode in seen_bibcodes or bibcode in config.exclude_bibcodes:
            continue

        authors = list_text(getattr(result, "author", ()))
        section = config.section_overrides.get(bibcode) or classify_author_section(authors, config)
        if section is None:
            continue

        seen_bibcodes.add(bibcode)
        title = first_text(getattr(result, "title", ""))
        journal = first_text(getattr(result, "pub", ""))
        year = first_text(getattr(result, "year", ""))
        pubdate = first_text(getattr(result, "pubdate", ""))
        citation_count = int(getattr(result, "citation_count", 0) or 0)
        doi = list_text(getattr(result, "doi", ()))
        identifiers = list_text(getattr(result, "identifier", ()))

        publications.append(
            AdsPublication(
                bibcode=bibcode,
                title=title,
                authors=authors,
                journal=journal,
                year=year,
                sort_date=parse_sort_date(pubdate, year),
                citation_count=citation_count,
                doi=doi,
                identifiers=identifiers,
                section=section,
            )
        )

    return publications


def compute_h_index(citation_counts: Iterable[int]) -> int:
    """Compute the h-index from citation counts."""

    sorted_counts = sorted((max(0, int(count)) for count in citation_counts), reverse=True)
    h_index = 0
    for index, count in enumerate(sorted_counts, start=1):
        if count < index:
            break
        h_index = index
    return h_index


def compute_metrics(publications: Sequence[AdsPublication]) -> Metrics:
    """Compute ADS-backed CV metrics from fetched publications."""

    citation_counts = [publication.citation_count for publication in publications]
    return Metrics(
        h_index=compute_h_index(citation_counts),
        total_citations=sum(citation_counts),
        indexed_papers=len(publications),
        first_author_count=sum(publication.section == "First Author" for publication in publications),
    )


def build_rendered_publications(
    ads_publications: Sequence[AdsPublication],
    manual_publications: Sequence[ManualPublication],
    config: CvConfig,
) -> list[RenderedPublication]:
    """Merge ADS and manual publications into a single renderable list."""

    rendered: list[RenderedPublication] = []

    for publication in ads_publications:
        rendered.append(
            RenderedPublication(
                section=publication.section,
                sort_date=publication.sort_date,
                text=render_ads_publication_text(publication, config),
            )
        )

    for publication in manual_publications:
        rendered.append(
            RenderedPublication(
                section=publication.section,
                sort_date=publication.sort_date,
                text=format_manual_text(publication),
            )
        )

    return rendered


def group_publications_by_section(
    publications: Sequence[RenderedPublication],
) -> dict[str, list[RenderedPublication]]:
    """Group publications by section, newest first within each section."""

    grouped: dict[str, list[RenderedPublication]] = {section: [] for section in ALLOWED_SECTIONS}
    for publication in publications:
        grouped[publication.section].append(publication)

    for section in ALLOWED_SECTIONS:
        grouped[section].sort(key=lambda item: (item.sort_date, item.text.casefold()), reverse=True)

    return grouped


def render_metrics_tex(metrics: Metrics) -> str:
    """Render the ADS metric summary TeX fragment."""

    return (
        "\\item \\textbf{ADS Metrics:} "
        f"h-index {metrics.h_index} \\quad "
        f"Total citations {metrics.total_citations} \\quad "
        f"Indexed papers {metrics.indexed_papers} \\quad "
        f"First-author papers {metrics.first_author_count}\n"
        "\\vspace{0.3em}\n"
    )


def render_publications_tex(publications: Sequence[RenderedPublication]) -> str:
    """Render the bucketed publication list TeX fragment."""

    grouped = group_publications_by_section(publications)
    lines: list[str] = ["\\item", "\\vspace{0.3em}", ""]

    for section in ALLOWED_SECTIONS:
        entries = grouped[section]
        if not entries:
            continue

        lines.append(f"{{\\Large\\textbf{{{section}}}}}")
        lines.append("")
        for publication in entries:
            lines.append(publication.text)
            lines.append("")
        lines.append("\\vspace{0.6em}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_index_html(display_name: str, metrics: Metrics, generated_at: datetime) -> str:
    """Render the GitHub Pages landing page."""

    safe_name = html.escape(display_name)
    generated_label = generated_at.strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_name} | CV</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f3efe6;
      --panel: #fffaf1;
      --ink: #14213d;
      --muted: #5c6773;
      --accent: #8d5524;
      --line: rgba(20, 33, 61, 0.16);
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      font-family: "Georgia", "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(141, 85, 36, 0.12), transparent 35%),
        linear-gradient(180deg, #f6f1e6 0%, var(--bg) 100%);
    }}

    main {{
      max-width: 1080px;
      margin: 0 auto;
      padding: 40px 20px 56px;
    }}

    .hero {{
      display: grid;
      gap: 20px;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      align-items: start;
      margin-bottom: 28px;
    }}

    .panel {{
      background: rgba(255, 250, 241, 0.86);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 24px;
      box-shadow: 0 20px 45px rgba(20, 33, 61, 0.08);
      backdrop-filter: blur(6px);
    }}

    h1 {{
      margin: 0 0 10px;
      font-size: clamp(2rem, 4vw, 3rem);
      line-height: 1.05;
    }}

    p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.6;
    }}

    .metrics {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 10px;
    }}

    .metrics li {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--line);
    }}

    .metrics li:last-child {{
      border-bottom: 0;
      padding-bottom: 0;
    }}

    .cta {{
      display: inline-block;
      margin-top: 18px;
      padding: 11px 18px;
      border-radius: 999px;
      background: var(--ink);
      color: #fffaf1;
      text-decoration: none;
    }}

    .viewer {{
      width: 100%;
      min-height: 78vh;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: #ffffff;
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="panel">
        <h1>{safe_name}</h1>
        <p>Daily ADS-backed CV build with ORCID-based author matching.</p>
        <p>Last updated {generated_label}</p>
        <a class="cta" href="academic_cv.pdf">Download PDF</a>
      </div>
      <div class="panel">
        <ul class="metrics">
          <li><strong>h-index</strong><span>{metrics.h_index}</span></li>
          <li><strong>Total citations</strong><span>{metrics.total_citations}</span></li>
          <li><strong>Indexed papers</strong><span>{metrics.indexed_papers}</span></li>
          <li><strong>First-author papers</strong><span>{metrics.first_author_count}</span></li>
        </ul>
      </div>
    </section>
    <object class="viewer" data="academic_cv.pdf" type="application/pdf">
      <p>Your browser could not embed the PDF. Use the download link above.</p>
    </object>
  </main>
</body>
</html>
"""


def write_text(path: Path, content: str) -> None:
    """Write UTF-8 text to disk, creating parent directories as needed."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ADS-backed CV generation pipeline."""

    args = parse_args(argv)
    config = load_config(args.config)
    manual_publications = load_manual_publications(args.manual)
    ads_publications = fetch_ads_publications(config)

    if not ads_publications and not args.allow_empty:
        raise RuntimeError(
            "The ADS query returned zero indexed papers. Verify the ORCID ID, claims, and ADS_DEV_KEY."
        )

    metrics = compute_metrics(ads_publications)
    rendered_publications = build_rendered_publications(ads_publications, manual_publications, config)
    generated_at = datetime.now(timezone.utc)

    write_text(args.generated_dir / "metrics.tex", render_metrics_tex(metrics))
    write_text(args.generated_dir / "publications.tex", render_publications_tex(rendered_publications))
    write_text(args.site_dir / "index.html", render_index_html(config.display_name, metrics, generated_at))
    write_text(args.site_dir / ".nojekyll", "")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
