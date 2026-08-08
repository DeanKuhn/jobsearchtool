# Job Search Triage Pipeline

![Python](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-active-brightgreen)

Scrapes job postings, stores them in Postgres, scores them against your
stack and title-vs-experience heuristics, and gives you a ranked queue to
manually work through. It does **not** auto-apply or auto-generate cover
letters — that part stays yours on purpose.

## What it does

1. `scrape_jobs.py` — pulls postings from Indeed / LinkedIn / Google Jobs via
   [JobSpy](https://github.com/speedyapply/JobSpy) for the searches defined
   in `config.py`, de-dupes by URL, and upserts into `raw_jobs`.
2. `score_jobs.py` — scores anything not yet scored:
   - stack overlap (keyword hits against your tech stack, weighted)
   - junior-title bonus / senior-title penalty
   - years-of-experience regex scan against the description
   - flags postings where the title says "junior" but the description wants
     3+ years of experience
   - flags postings older than 30 days (stale postings)
3. `job_review_queue` (a view in `schema.sql`) — everything still `status =
   'new'`, ranked by score, best matches first.

## Setup

```bash
git clone https://github.com/DeanKuhn/jobsearchtool.git
cd jobsearchtool
python -m venv .venv && source .venv/bin/activate   # or your usual uv workflow
pip install -r requirements.txt
playwright install chromium   # JobSpy uses Playwright under the hood for some sites

cp .env.example .env
# edit .env with your Postgres DATABASE_URL (e.g. from Neon)

psql "$DATABASE_URL" -f schema.sql
```

## Running

```bash
python scrape_jobs.py   # pulls fresh postings
python score_jobs.py    # scores anything new
```

Then check your queue:

```sql
SELECT title, company, location, total_score, experience_mismatch, is_stale, job_url
FROM job_review_queue
LIMIT 25;
```

Mark things as you go:

```sql
INSERT INTO job_status (job_id, status, notes)
VALUES (17, 'applied', 'Sent tailored resume + cover letter')
ON CONFLICT (job_id) DO UPDATE SET status = EXCLUDED.status, notes = EXCLUDED.notes, updated_at = now();
```

## Tuning

Everything you'd want to change lives in `config.py`:
- `SEARCHES` — the (term, location) pairs to query
- `STACK_KEYWORDS` — what counts as a stack match and how much it's worth
- `JUNIOR_TITLE_TERMS` / `SENIOR_TITLE_TERMS` — title heuristics
- `MAX_YEARS_FOR_JUNIOR` — the threshold that trips the mismatch flag
- `STALE_DAYS` — how old is too old

## Things to know before you run this at scale

- **LinkedIn rate-limits aggressively** — usually somewhere around page 10
  on a single IP. Run scraping from an environment/IP separate from any
  account you're actively using for outreach.
- **This filters, it doesn't apply.** The scoring is deliberately
  transparent (keyword counts, not an LLM black box) so you can see exactly
  why something ranked where it did.
- **Applicant counts aren't included.** JobSpy doesn't expose LinkedIn's
  applicant count reliably, so that check still has to happen by hand for
  anything that clears the queue.
- **Legitimacy checks still matter.** A high stack-match score says nothing
  about whether a company's site is live or a recruiter's email is real.
  This tool surfaces candidates for you to vet, not finished decisions.

## Natural extensions

- Swap the keyword scorer in `score_jobs.py` for a dbt model once postings
  are landing reliably (raw → staging → marts).
- Cross-reference `raw_jobs.company` against an outreach log to flag
  postings at companies where you already have a warm contact.

## License

MIT
