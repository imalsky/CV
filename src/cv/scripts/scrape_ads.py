"""
Heavily inspired by dfm/cv/update-astro-pubs
"""

import importlib.util
import inspect
import json
import os
import time
from operator import itemgetter
import ads
import requests
import cv

# Set the ADS API key from the environment variable
ads.config.token = os.environ.get('BASE_ENV')

if not ads.config.token:
    raise ValueError("ADS API key is not set. Check BASE_ENV environment variable.")
else:
    print("ADS API key is set.")

cv_root = inspect.getfile(cv).split("cv")[0]
data_path = os.path.join(cv_root, "data")

cv_path = inspect.getfile(cv).split("__init")[0]

# Get the directory of the current script
here = os.path.dirname(os.path.realpath(__file__))

spec = importlib.util.spec_from_file_location(
    "utf8totex", os.path.join(here, "utf8totex.py")
)
utf8totex = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utf8totex)

def get_papers(author):
    """
    Gets all the papers for a given author from NASA/ADS.

    Inputs
    ------
        :author: (str) name of author. Lastname, firstname middle

    Outputs
    -------
        :dicts: (list of dictionaries) the sorted dictionaries corresponding to the author's publications.
    """
    papers = list(
        ads.SearchQuery(
            author=author,
            fl=[
                "id",
                "title",
                "author",
                "doi",
                "year",
                "pubdate",
                "pub",
                "volume",
                "page",
                "identifier",
                "doctype",
                "citation_count",
                "bibcode",
            ],
            max_pages=100,
        )
    )

    dicts = []
    for paper in papers:
        aid = [
            ":".join(t.split(":")[1:])
            for t in paper.identifier
            if t.startswith("arXiv:")
        ]
        for t in paper.identifier:
            if len(t.split(".")) != 2:
                continue
            try:
                list(map(int, t.split(".")))
            except ValueError:
                pass
            else:
                aid.append(t)
        try:
            page = int(paper.page[0])
        except (ValueError, TypeError):
            page = None
            if paper.page is not None and paper.page[0].startswith("arXiv:"):
                aid.append(":".join(paper.page[0].split(":")[1:]))
        dicts.append(
            dict(
                doctype=paper.doctype,
                authors=list(map(utf8totex.utf8totex, paper.author)),
                year=paper.year,
                pubdate=paper.pubdate,
                doi=paper.doi[0] if paper.doi is not None else None,
                title=utf8totex.utf8totex(paper.title[0]),
                pub=paper.pub,
                volume=paper.volume,
                page=page,
                arxiv=aid[0] if len(aid) else None,
                citations=(
                    paper.citation_count if paper.citation_count is not None else 0
                ),
                url="https://ui.adsabs.harvard.edu/abs/" + paper.bibcode,
            )
        )
    return sorted(dicts, key=itemgetter("pubdate"), reverse=True)


if __name__ == "__main__":
    # tries once more if there's a timeout error
    try:
        paper_dict = get_papers("Malsky, Isaac")
    except requests.Timeout as err:
        print("Timeout error")
        print(err)
        time.sleep(60)
        paper_dict = get_papers("Malsky, Isaac")
    with open(os.path.join(data_path, "ads_scrape.json"), "w") as f:
        json.dump(paper_dict, f, sort_keys=True, indent=2, separators=(",", ": "))