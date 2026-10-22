"""
Scrape job postings via JobSpy and load them into Postgres.

Usage:
    python scrape_jobs.py

Requires DATABASE_URL in your environment or a .env file, e.g.:
    DATABASE_URL=postgresql://user:pass@host/dbname?sslmode=require
"""

import os
import sys
import time

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv # type:ignore
from jobspy import scrape_jobs # type:ignore

from config import SEARCHES, SITES, RESULTS_WANTED_PER_SEARCH, HOURS_OLD

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("DATABASE_URL not set. Add it to your environment or a .env file.")

UPSERT_SQL = """
INSERT INTO raw_jobs (
    job_url, site, title, company, location, is_remote, job_type,
    date_posted, min_amount, max_amount, salary_interval, description,
    search_term, search_location
)
VALUES %s
ON CONFLICT (job_url) DO UPDATE SET
    last_seen_at = now()
"""


def clean_row(row: pd.Series, search_term: str, search_location: str) -> tuple:
    def val(col):
        v = row.get(col)
        if pd.isna(v):
            return None
        return v

    date_posted = val("date_posted")
    if date_posted is not None:
        date_posted = pd.to_datetime(date_posted, errors="coerce")
        date_posted = None if pd.isna(date_posted) else date_posted.date()

    return (
        val("job_url"),
        val("site"),
        val("title"),
        val("company"),
        val("location"),
        bool(val("is_remote")) if val("is_remote") is not None else None,
        val("job_type"),
        date_posted,
        val("min_amount"),
        val("max_amount"),
        val("interval"),
        val("description"),
        search_term,
        search_location,
    )


def run():
    all_rows = []

    for search_term, location in SEARCHES:
        print(f"Scraping: '{search_term}' in '{location}'...")
        try:
            df = scrape_jobs(
                site_name=SITES,
                search_term=search_term,
                location=location,
                results_wanted=RESULTS_WANTED_PER_SEARCH,
                hours_old=HOURS_OLD,
                country_indeed="USA",
                description_format="markdown",
                # Glassdoor and LinkedIn only return descriptions with this on
                fetch_description=True,
            )
        except Exception as e:
            print(f"  Failed ({e}); skipping this search.")
            continue

        if df is None or df.empty:
            print("  No results.")
            continue

        print(f"  Got {len(df)} postings.")
        for _, row in df.iterrows():
            all_rows.append(clean_row(row, search_term, location))

        # be polite between queries, especially against LinkedIn
        time.sleep(5)

    if not all_rows:
        print("Nothing scraped this run.")
        return

    # de-dupe within this run by job_url before writing
    seen = {}
    for row in all_rows:
        seen[row[0]] = row  # job_url is index 0
    rows = list(seen.values())

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                execute_values(cur, UPSERT_SQL, rows)
        print(f"Upserted {len(rows)} unique postings into raw_jobs.")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
