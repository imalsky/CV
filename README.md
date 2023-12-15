## Process
Every 24 hours (midnight UTC), the `add_review_nums` workflow is run. This scrapes JOSS for the number of reviews I've conducted, writes this number to the main tex file, and commits the changes.

Additionally, `scrape_ads` is run, which pulls my publications & their citations from [NASA ADS](https://ui.adsabs.harvard.edu/). These are aggregated, formatted, and written to a tex file.

Finally, a new tag is created for this repository.

Also...adds CV metadata for SEO snippet purposes.
