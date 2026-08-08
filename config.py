"""
Search and scoring configuration. Edit this file, not the pipeline scripts,
when you want to change what gets scraped or how it gets scored.
"""

# --- What to search for -----------------------------------------------------
# Each (search_term, location) pair becomes one JobSpy query.
# Keep queries specific -- broad terms like "data" pull too much noise.
SEARCHES = [
    ("junior data engineer", "Milwaukee, WI"),
    ("analytics engineer", "Milwaukee, WI"),
    ("data analyst", "Milwaukee, WI"),
    ("junior data engineer", "Remote"),
    ("analytics engineer", "Remote"),
]

SITES = ["indeed", "linkedin", "google", "glassdoor"]
RESULTS_WANTED_PER_SEARCH = 40
HOURS_OLD = 24 * 14  # only pull postings from the last 14 days

# --- Scoring ------------------------------------------------------------
# Keyword -> point value. Matched case-insensitively against the job description.
STACK_KEYWORDS = {
    "python": 3,
    "sql": 3,
    "postgres": 2,
    "snowflake": 3,
    "dbt": 3,
    "power bi": 3,
    "powerbi": 3,
    "airflow": 2,
    "pyspark": 2,
    "databricks": 2,
    "aws": 2,
    "docker": 1,
    "fastapi": 1,
    "etl": 2,
    "elt": 2,
    "data warehouse": 2,
    "data pipeline": 2,
    "analytics engineer": 3,
    "data engineer": 2,
    "git": 1,
    "ci/cd": 1,
}

# Title signals
JUNIOR_TITLE_TERMS = ["junior", "entry level", "entry-level", "associate", "grad", "new grad", "i "]
SENIOR_TITLE_TERMS = ["senior", "sr.", "staff", "principal", "lead ", "manager", "director", "architect"]

TITLE_BONUS = 5
SENIORITY_PENALTY = -10

# A posting requiring more than this many years of experience is flagged as a
# mismatch against a "junior" title -- your own rule of thumb from past applications.
MAX_YEARS_FOR_JUNIOR = 2

STALE_DAYS = 30