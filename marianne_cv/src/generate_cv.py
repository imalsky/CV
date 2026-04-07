#!/usr/bin/env python3
"""Generate the Scholar-backed publications fragment and landing page for Marianne's CV."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = ROOT / "src" / "cv_config.toml"
DEFAULT_MANUAL_PATH = ROOT / "src" / "manual_publications.toml"
DEFAULT_GENERATED_DIR = ROOT / "generated"
DEFAULT_SITE_DIR = ROOT / "compiled"
NON_ALPHANUMERIC_PATTERN = re.compile(r"[^a-z0-9]+")
SCHOLAR_USER_PATTERN = re.compile(r"[?&]user=([A-Za-z0-9_-]+)")
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
SCHOLAR_REQUEST_TIMEOUT_SECONDS = 20
FREE_PROXY_TIMEOUT_SECONDS = 2
FREE_PROXY_WAIT_SECONDS = 30
ABSTRACT_VENUE_KEYWORDS = (
    "abstract",
    "conference",
    "meeting",
    "symposium",
)


@dataclass(frozen=True)
class CvConfig:
    """Static configuration for Marianne's Scholar-backed CV build."""

    display_name: str
    scholar_url: str
    scholar_user_id: str
    name_aliases: tuple[str, ...]
    excluded_title_slugs: frozenset[str]
    normalized_aliases: frozenset[str]
    alias_signatures: frozenset[tuple[str, str]]


@dataclass(frozen=True)
class ScholarPublication:
    """A publication record fetched from Google Scholar."""

    title: str
    title_slug: str
    authors: tuple[str, ...]  # shape: (n_authors,)
    journal: str
    citation_text: str
    year: str
    sort_date: str
    citation_count: int
    author_position: int | None
    pub_url: str


@dataclass(frozen=True)
class PublishedOverride:
    """Manual override or add-on for a Scholar publication."""

    match_title: str
    title_slug: str
    text: str
    append_text: str
    sort_date: str


@dataclass(frozen=True)
class ManualPublication:
    """A manually curated unpublished publication entry."""

    sort_date: str
    text: str


@dataclass(frozen=True)
class ManualData:
    """All manual publication content needed to preserve Marianne's CV."""

    manual_heading: str
    published_overrides: dict[str, PublishedOverride]
    manual_entries: list[ManualPublication]


@dataclass(frozen=True)
class RenderedPublication:
    """A publication entry ready to write into TeX."""

    sort_date: str
    text: str


@dataclass(frozen=True)
class Metrics:
    """Scholar-backed metrics for the compiled site."""

    h_index: int
    total_citations: int
    included_papers: int


def log_progress(message: str) -> None:
    """Print a progress line immediately for long-running local and CI builds."""

    print(message, flush=True)


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
        help="Do not fail when the filtered Scholar query returns zero included publications.",
    )
    return parser.parse_args(argv)


def load_toml(path: Path) -> dict[str, Any]:
    """Load a TOML file from disk."""

    if not path.exists():
        raise RuntimeError(f"Missing required file: {path}")

    with path.open("rb") as file_handle:
        return tomllib.load(file_handle)


def normalize_text(value: str) -> str:
    """Normalize a string for robust comparisons."""

    return NON_ALPHANUMERIC_PATTERN.sub("", value.casefold())


def normalize_title(value: str) -> str:
    """Normalize a publication title for matching."""

    return normalize_text(value)


def escape_tex(value: str) -> str:
    """Escape LaTeX control characters in text."""

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
            return (normalize_text(parts[0]), "")
        surname = parts[-1]
        given_names = " ".join(parts[:-1])

    initials = "".join(token[0] for token in re.findall(r"[A-Za-z]+", given_names))
    return (normalize_text(surname), initials.casefold())


def extract_scholar_user_id(scholar_url: str) -> str:
    """Extract the Scholar user id from a profile URL."""

    match = SCHOLAR_USER_PATTERN.search(scholar_url)
    return match.group(1) if match else ""


def load_config(path: Path) -> CvConfig:
    """Load and validate the checked-in CV configuration."""

    raw_config = load_toml(path)

    display_name = str(raw_config.get("display_name", "")).strip()
    scholar_url = str(raw_config.get("scholar_url", "")).strip()
    scholar_user_id = str(raw_config.get("scholar_user_id", "")).strip() or extract_scholar_user_id(scholar_url)
    name_aliases = tuple(str(alias).strip() for alias in raw_config.get("name_aliases", []) if str(alias).strip())
    excluded_title_slugs = frozenset(
        normalize_title(str(title))
        for title in raw_config.get("exclude_titles", [])
        if str(title).strip()
    )

    if not display_name:
        raise RuntimeError(f"`display_name` must be set in {path}")
    if not scholar_user_id:
        raise RuntimeError(f"`scholar_user_id` or a Scholar URL with `?user=` must be set in {path}")
    if not name_aliases:
        raise RuntimeError(f"`name_aliases` must contain at least one alias in {path}")

    normalized_aliases = frozenset(normalize_text(alias) for alias in name_aliases)
    alias_signatures = frozenset(build_author_signature(alias) for alias in name_aliases)

    return CvConfig(
        display_name=display_name,
        scholar_url=scholar_url,
        scholar_user_id=scholar_user_id,
        name_aliases=name_aliases,
        excluded_title_slugs=excluded_title_slugs,
        normalized_aliases=normalized_aliases,
        alias_signatures=alias_signatures,
    )


def load_manual_publications(path: Path) -> ManualData:
    """Load manual publication entries and per-paper overrides."""

    raw_manual = load_toml(path)
    manual_heading = str(raw_manual.get("manual_heading", "")).strip()
    published_overrides: dict[str, PublishedOverride] = {}
    manual_entries: list[ManualPublication] = []

    for entry in raw_manual.get("published_overrides", []):
        match_title = str(entry.get("match_title", "")).strip()
        text = str(entry.get("text", "")).strip()
        append_text = str(entry.get("append_text", "")).strip()
        sort_date = str(entry.get("sort_date", "")).strip()
        title_slug = normalize_title(match_title)

        if not match_title:
            raise RuntimeError(f"Published overrides in {path} require `match_title`.")
        if not text and not append_text:
            raise RuntimeError(f"Published overrides in {path} require `text` or `append_text`.")
        if title_slug in published_overrides:
            raise RuntimeError(f"Duplicate published override for `{match_title}` in {path}.")

        published_overrides[title_slug] = PublishedOverride(
            match_title=match_title,
            title_slug=title_slug,
            text=text,
            append_text=append_text,
            sort_date=sort_date,
        )

    for entry in raw_manual.get("manual_entries", []):
        sort_date = str(entry.get("sort_date", "")).strip()
        text = str(entry.get("text", "")).strip()

        if not sort_date:
            raise RuntimeError(f"Manual entries in {path} require `sort_date`.")
        if not text:
            raise RuntimeError(f"Manual entries in {path} require `text`.")

        manual_entries.append(ManualPublication(sort_date=sort_date, text=text))

    return ManualData(
        manual_heading=manual_heading,
        published_overrides=published_overrides,
        manual_entries=manual_entries,
    )


def parse_sort_date(year: str) -> str:
    """Convert a publication year into a sortable YYYY-MM-DD string."""

    if re.fullmatch(r"\d{4}", year):
        return f"{year}-01-01"
    return "1900-01-01"


def parse_author_list(value: str | Sequence[str]) -> tuple[str, ...]:
    """Normalize Scholar author metadata into a tuple of strings."""

    if isinstance(value, str):
        authors = [author.strip() for author in value.split(" and ")]
    else:
        authors = [str(author).strip() for author in value]
    return tuple(author for author in authors if author)


def is_abstract_publication(journal: str, citation_text: str, pub_url: str) -> bool:
    """Return True for abstract or conference-style Scholar entries."""

    combined = " ".join(part.casefold() for part in (journal, citation_text) if part)
    if any(keyword in combined for keyword in ABSTRACT_VENUE_KEYWORDS):
        return True

    return "/abstract" in pub_url.casefold()


def create_scholar_client() -> Any:
    """Create a Scholar session configured with a working free proxy."""

    try:
        from scholarly import ProxyGenerator, scholarly
    except ImportError as exc:
        raise RuntimeError(
            "The `scholarly` package is not installed. Run `src/build_local_cv.sh` or "
            "`python -m pip install -r src/requirements.txt` in a virtual environment first."
        ) from exc

    proxy_generator = ProxyGenerator()
    log_progress("Acquiring Google Scholar proxy...")
    if not proxy_generator.FreeProxies(timeout=FREE_PROXY_TIMEOUT_SECONDS, wait_time=FREE_PROXY_WAIT_SECONDS):
        raise RuntimeError("Unable to acquire a working Scholar proxy from `scholarly`.")

    scholarly.use_proxy(proxy_generator)
    scholarly.set_timeout(SCHOLAR_REQUEST_TIMEOUT_SECONDS)
    return scholarly


def author_matches(author: str, config: CvConfig) -> bool:
    """Return True when an author string matches Marianne's aliases."""

    normalized_author = normalize_text(author)
    if normalized_author in config.normalized_aliases:
        return True

    surname, initials = build_author_signature(author)
    if not surname:
        return False

    return (surname, initials) in config.alias_signatures


def find_author_position(authors: Sequence[str], config: CvConfig) -> int | None:
    """Return the 1-based author position for Marianne."""

    for index, author in enumerate(authors, start=1):
        if author_matches(author, config):
            return index
    return None


def compact_author_name(author: str) -> str:
    """Shorten an author string to surname plus initials."""

    stripped = author.strip()
    if not stripped:
        return ""

    if "," in stripped:
        surname, given_names = stripped.split(",", 1)
    else:
        parts = stripped.split()
        if len(parts) == 1:
            return parts[0]
        surname = parts[-1]
        given_names = " ".join(parts[:-1])

    initials = " ".join(f"{token[0]}." for token in re.findall(r"[A-Za-z]+", given_names))
    surname = surname.strip()
    return f"{surname}, {initials}".strip().rstrip(",")


def format_single_author(author: str, config: CvConfig) -> str:
    """Render one author name and bold Marianne."""

    author_tex = escape_tex(compact_author_name(author))
    if author_matches(author, config):
        return f"\\textbf{{{author_tex}}}"
    return author_tex


def join_authors(authors: Sequence[str]) -> str:
    """Join a formatted author list using CV-style punctuation."""

    if not authors:
        return ""
    if len(authors) == 1:
        return authors[0]
    if len(authors) == 2:
        return f"{authors[0]} and {authors[1]}"
    return f"{', '.join(authors[:-1])}, and {authors[-1]}"


def format_authors(authors: Sequence[str], config: CvConfig) -> str:
    """Render Scholar authors in Marianne's CV style."""

    return join_authors([format_single_author(author, config) for author in authors])


def fetch_scholar_publications(config: CvConfig) -> list[ScholarPublication]:
    """Query Google Scholar and return the publications relevant to the CV."""

    log_progress(f"Loading Scholar profile for {config.display_name}...")
    scholarly_client = create_scholar_client()
    try:
        author = scholarly_client.search_author_id(config.scholar_user_id, filled=True)
    except Exception as exc:
        raise RuntimeError("Google Scholar blocked or failed the author lookup.") from exc

    publications: list[ScholarPublication] = []
    seen_title_slugs: set[str] = set()
    raw_entries = list(author.get("publications", []))
    total_entries = len(raw_entries)
    log_progress(f"Found {total_entries} Scholar entries. Fetching detailed records...")

    for index, entry in enumerate(raw_entries, start=1):
        preview_title = str(entry.get("bib", {}).get("title", "")).strip() or "<unknown title>"
        log_progress(f"[{index}/{total_entries}] Fetching {preview_title}")
        try:
            filled_entry = scholarly_client.fill(entry)
        except Exception as exc:
            title = str(entry.get("bib", {}).get("title", "")).strip() or "<unknown title>"
            raise RuntimeError(
                f"Google Scholar failed while fetching publication metadata for `{title}`."
            ) from exc

        bib = filled_entry.get("bib", {})
        title = str(bib.get("title", "")).strip()
        if not title:
            continue

        title_slug = normalize_title(title)
        if title_slug in seen_title_slugs or title_slug in config.excluded_title_slugs:
            continue

        authors = parse_author_list(bib.get("author", ""))
        year = str(bib.get("pub_year", "")).strip()
        journal = str(bib.get("journal", "")).strip()
        citation_text = str(bib.get("citation", "")).strip()
        pub_url = str(filled_entry.get("pub_url", "")).strip()

        if is_abstract_publication(journal, citation_text, pub_url):
            log_progress(f"[{index}/{total_entries}] Skipping abstract/conference entry.")
            continue

        seen_title_slugs.add(title_slug)
        publications.append(
            ScholarPublication(
                title=title,
                title_slug=title_slug,
                authors=authors,
                journal=journal,
                citation_text=citation_text,
                year=year,
                sort_date=parse_sort_date(year),
                citation_count=int(filled_entry.get("num_citations", 0) or 0),
                author_position=find_author_position(authors, config),
                pub_url=pub_url,
            )
        )
        log_progress(f"[{index}/{total_entries}] Added publication.")

    log_progress(f"Kept {len(publications)} non-abstract publications from Scholar.")
    return publications


def compute_h_index(citation_counts: Sequence[int]) -> int:
    """Compute the h-index from citation counts."""

    sorted_counts = sorted((max(0, int(count)) for count in citation_counts), reverse=True)
    h_index = 0
    for index, count in enumerate(sorted_counts, start=1):
        if count < index:
            break
        h_index = index
    return h_index


def compute_metrics(publications: Sequence[ScholarPublication]) -> Metrics:
    """Compute Scholar-backed metrics from the included publication set."""

    citation_counts = [publication.citation_count for publication in publications]
    return Metrics(
        h_index=compute_h_index(citation_counts),
        total_citations=sum(citation_counts),
        included_papers=len(publications),
    )


def format_scholar_publication(publication: ScholarPublication, config: CvConfig) -> str:
    """Render one Scholar publication in Marianne's CV style."""

    authors_tex = format_authors(publication.authors, config)
    title_tex = escape_tex(publication.title)
    year_tex = f"({publication.year})" if publication.year else ""
    venue_source = publication.journal or publication.citation_text
    venue_tex = escape_tex(venue_source)
    parts = [part for part in [f"{authors_tex}.", f"{title_tex}.", year_tex, f"\\textit{{{venue_tex}}}."] if part]
    return " ".join(parts).strip()


def build_publication_entries(
    scholar_publications: Sequence[ScholarPublication],
    manual_data: ManualData,
    config: CvConfig,
) -> tuple[list[RenderedPublication], list[RenderedPublication]]:
    """Build the rendered publication lists for published and manual entries."""

    published_entries: list[RenderedPublication] = []
    matched_overrides: set[str] = set()

    for publication in scholar_publications:
        override = manual_data.published_overrides.get(publication.title_slug)
        if override:
            matched_overrides.add(publication.title_slug)

        if override and override.text:
            text = override.text
        else:
            text = format_scholar_publication(publication, config)
            if override and override.append_text:
                text = f"{text} {override.append_text}".strip()

        published_entries.append(
            RenderedPublication(
                sort_date=override.sort_date if override and override.sort_date else publication.sort_date,
                text=text,
            )
        )

    unmatched_overrides = sorted(
        override.match_title
        for title_slug, override in manual_data.published_overrides.items()
        if title_slug not in matched_overrides
    )
    if unmatched_overrides:
        joined = ", ".join(f"`{title}`" for title in unmatched_overrides)
        raise RuntimeError(
            "Manual publication overrides did not match any Scholar result. Update the override titles or the "
            f"exclude list: {joined}"
        )

    manual_entries = [RenderedPublication(sort_date=entry.sort_date, text=entry.text) for entry in manual_data.manual_entries]
    published_entries.sort(key=lambda item: (item.sort_date, item.text.casefold()), reverse=True)
    manual_entries.sort(key=lambda item: (item.sort_date, item.text.casefold()), reverse=True)
    return published_entries, manual_entries


def render_publications_tex(
    published_entries: Sequence[RenderedPublication],
    manual_heading: str,
    manual_entries: Sequence[RenderedPublication],
) -> str:
    """Render the publications TeX fragment used by `main.tex`."""

    lines: list[str] = []

    for publication in published_entries:
        lines.append(f"\\item {publication.text}")

    if manual_entries:
        if manual_heading:
            lines.append(f"\\item {manual_heading}")
        for publication in manual_entries:
            lines.append(f"\\item {publication.text}")

    return "\n".join(lines).rstrip() + "\n"


def render_index_html(display_name: str, metrics: Metrics, generated_at: datetime, scholar_url: str) -> str:
    """Render the compiled-site landing page."""

    safe_name = html.escape(display_name)
    generated_label = generated_at.strftime("%Y-%m-%d %H:%M UTC")
    scholar_link = (
        f'<a class="secondary" href="{html.escape(scholar_url)}">Google Scholar</a>'
        if scholar_url
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_name} | CV</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f8f5ef;
      --panel: rgba(255, 255, 255, 0.88);
      --ink: #1f2530;
      --muted: #5f6977;
      --accent: #355070;
      --line: rgba(31, 37, 48, 0.12);
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      color: var(--ink);
      font-family: "Georgia", "Times New Roman", serif;
      background:
        radial-gradient(circle at top left, rgba(53, 80, 112, 0.12), transparent 28%),
        linear-gradient(180deg, #fbfaf7 0%, var(--bg) 100%);
    }}

    main {{
      max-width: 1080px;
      margin: 0 auto;
      padding: 40px 20px 56px;
    }}

    .hero {{
      display: grid;
      gap: 20px;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      align-items: start;
      margin-bottom: 24px;
    }}

    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 24px;
      box-shadow: 0 18px 48px rgba(31, 37, 48, 0.08);
      backdrop-filter: blur(8px);
    }}

    h1 {{
      margin: 0 0 12px;
      color: var(--accent);
      font-size: clamp(2rem, 4vw, 3rem);
      line-height: 1.04;
    }}

    p {{
      margin: 0 0 10px;
      color: var(--muted);
      line-height: 1.6;
    }}

    .links {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 18px;
    }}

    a {{
      color: var(--ink);
      text-decoration: none;
    }}

    .cta, .secondary {{
      display: inline-block;
      padding: 11px 18px;
      border-radius: 999px;
      border: 1px solid var(--line);
    }}

    .cta {{
      background: var(--ink);
      color: #ffffff;
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
        <p>Scholar-backed publications build for Marianne's LaTeX CV.</p>
        <p>Last updated {generated_label}</p>
        <div class="links">
          <a class="cta" href="main.pdf">Download PDF</a>
          {scholar_link}
        </div>
      </div>
      <div class="panel">
        <ul class="metrics">
          <li><strong>CV publications</strong><span>{metrics.included_papers}</span></li>
          <li><strong>Total citations</strong><span>{metrics.total_citations}</span></li>
          <li><strong>Scholar h-index</strong><span>{metrics.h_index}</span></li>
        </ul>
      </div>
    </section>
    <object class="viewer" data="main.pdf" type="application/pdf">
      <p>Your browser could not embed the PDF. Use the download link above.</p>
    </object>
  </main>
</body>
</html>
"""


def load_fixture_publications(path: Path) -> list[ScholarPublication]:
    """Load Scholar publication fixtures for deterministic tests."""

    with path.open("r", encoding="utf-8") as file_handle:
        raw_entries = json.load(file_handle)

    publications: list[ScholarPublication] = []
    for entry in raw_entries:
        title = str(entry["title"]).strip()
        publications.append(
            ScholarPublication(
                title=title,
                title_slug=normalize_title(title),
                authors=tuple(str(author).strip() for author in entry["authors"]),
                journal=str(entry.get("journal", "")).strip(),
                citation_text=str(entry.get("citation_text", "")).strip(),
                year=str(entry.get("year", "")).strip(),
                sort_date=str(entry.get("sort_date", "")).strip() or parse_sort_date(str(entry.get("year", "")).strip()),
                citation_count=int(entry.get("citation_count", 0) or 0),
                author_position=int(entry["author_position"]) if entry.get("author_position") is not None else None,
                pub_url=str(entry.get("pub_url", "")).strip(),
            )
        )
    return publications


def write_text(path: Path, content: str) -> None:
    """Write UTF-8 text to disk, creating parent directories as needed."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Scholar-backed CV generation pipeline."""

    args = parse_args(argv)
    config = load_config(args.config)
    manual_data = load_manual_publications(args.manual)
    scholar_publications = fetch_scholar_publications(config)

    if not scholar_publications and not args.allow_empty:
        raise RuntimeError(
            "The Scholar profile returned zero included publications. Verify the Scholar user id, "
            "or adjust `exclude_titles` in src/cv_config.toml."
        )

    metrics = compute_metrics(scholar_publications)
    generated_at = datetime.now(timezone.utc)
    published_entries, manual_entries = build_publication_entries(scholar_publications, manual_data, config)

    write_text(
        args.generated_dir / "publications.tex",
        render_publications_tex(published_entries, manual_data.manual_heading, manual_entries),
    )
    write_text(
        args.site_dir / "index.html",
        render_index_html(config.display_name, metrics, generated_at, config.scholar_url),
    )
    write_text(args.site_dir / ".nojekyll", "")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
