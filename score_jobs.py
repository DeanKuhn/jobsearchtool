"""
Score unscored postings in raw_jobs and write results to job_scores.

Usage:
    python score_jobs.py

This is deliberately simple and transparent -- keyword overlap against your
stack, a title-based junior/senior signal, a regex scan for "X years"
requirements, and a staleness flag. No LLM call, no black box. You can see
exactly why something scored the way it did, which matters more than a
fancier model here.
"""

import os
import re
import sys
from datetime import date, timedelta

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv # type:ignore

from config import (
    STACK_KEYWORDS,
    JUNIOR_TITLE_TERMS,
    SENIOR_TITLE_TERMS,
    TITLE_BONUS,
    SENIORITY_PENALTY,
    MAX_YEARS_FOR_JUNIOR,
    STALE_DAYS,
)

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("DATABASE_URL not set. Add it to your environment or a .env file.")

YEARS_PATTERN = re.compile(r"(\d+)\s*\+?\s*(?:-|to)?\s*\d*\s*year", re.IGNORECASE)

FETCH_UNSCORED_SQL = """
SELECT r.id, r.title, r.description, r.date_posted
FROM raw_jobs r
LEFT JOIN job_scores s ON s.job_id = r.id
WHERE s.job_id IS NULL
"""

UPSERT_SCORE_SQL = """
INSERT INTO job_scores (
    job_id, stack_score, title_bonus, seniority_penalty,
    years_required, experience_mismatch, is_stale, total_score
)
VALUES %s
ON CONFLICT (job_id) DO UPDATE SET
    stack_score = EXCLUDED.stack_score,
    title_bonus = EXCLUDED.title_bonus,
    seniority_penalty = EXCLUDED.seniority_penalty,
    years_required = EXCLUDED.years_required,
    experience_mismatch = EXCLUDED.experience_mismatch,
    is_stale = EXCLUDED.is_stale,
    total_score = EXCLUDED.total_score,
    scored_at = now()
"""


def score_stack(text: str) -> int:
    text = text.lower()
    return sum(pts for kw, pts in STACK_KEYWORDS.items() if kw in text)


def title_signal(title: str) -> tuple:
    t = (title or "").lower()
    bonus = TITLE_BONUS if any(term in t for term in JUNIOR_TITLE_TERMS) else 0
    penalty = SENIORITY_PENALTY if any(term in t for term in SENIOR_TITLE_TERMS) else 0
    return bonus, penalty


def years_required(text: str) -> int:
    matches = [int(m) for m in YEARS_PATTERN.findall(text or "")]
    return max(matches) if matches else 0


def score_row(job_id, title, description, date_posted):
    description = description or ""
    stack = score_stack(description)
    t_bonus, s_penalty = title_signal(title)
    years = years_required(description)

    is_junior_title = t_bonus > 0
    mismatch = is_junior_title and years > MAX_YEARS_FOR_JUNIOR

    is_stale = False
    if date_posted:
        is_stale = (date.today() - date_posted) > timedelta(days=STALE_DAYS)

    total = stack + t_bonus + s_penalty
    if mismatch:
        total -= 10  # extra penalty: title says junior, description says otherwise

    return (job_id, stack, t_bonus, s_penalty, years, mismatch, is_stale, total)


def run():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(FETCH_UNSCORED_SQL)
            rows = cur.fetchall()

        if not rows:
            print("Nothing new to score.")
            return

        scored = [score_row(*row) for row in rows]

        with conn:
            with conn.cursor() as cur:
                execute_values(cur, UPSERT_SCORE_SQL, scored)

        print(f"Scored {len(scored)} postings.")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
