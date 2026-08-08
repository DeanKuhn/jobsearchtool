-- Job search pipeline schema
-- Run once against your Neon (or any Postgres) database:
--   psql $DATABASE_URL -f schema.sql

CREATE TABLE IF NOT EXISTS raw_jobs (
    id                  SERIAL PRIMARY KEY,
    job_url             TEXT UNIQUE NOT NULL,
    site                TEXT,               -- linkedin, indeed, glassdoor, google, zip_recruiter
    title               TEXT,
    company             TEXT,
    location            TEXT,
    is_remote           BOOLEAN,
    job_type            TEXT,               -- fulltime, parttime, internship, contract
    date_posted         DATE,
    min_amount          NUMERIC,
    max_amount          NUMERIC,
    salary_interval      TEXT,
    description         TEXT,
    search_term         TEXT,               -- which query pulled this in
    search_location      TEXT,
    first_scraped_at    TIMESTAMPTZ DEFAULT now(),
    last_seen_at        TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS job_scores (
    job_id                  INTEGER PRIMARY KEY REFERENCES raw_jobs(id) ON DELETE CASCADE,
    stack_score             INTEGER,        -- keyword overlap with your tech stack
    title_bonus              INTEGER,        -- junior/entry/associate signal
    seniority_penalty        INTEGER,        -- senior/staff/lead/principal signal
    years_required           INTEGER,        -- max years-of-experience figure found in description, if any
    experience_mismatch      BOOLEAN,        -- "junior" title but 3+ years required
    is_stale                BOOLEAN,        -- posted 30+ days ago
    total_score              INTEGER,
    scored_at                TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS job_status (
    job_id      INTEGER PRIMARY KEY REFERENCES raw_jobs(id) ON DELETE CASCADE,
    status      TEXT DEFAULT 'new',   -- new, reviewing, applied, skipped, rejected, interview
    notes       TEXT,
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- Convenience view: everything you'd actually want to triage, best matches first
CREATE OR REPLACE VIEW job_review_queue AS
SELECT
    r.id,
    r.title,
    r.company,
    r.location,
    r.is_remote,
    r.date_posted,
    r.site,
    r.job_url,
    s.total_score,
    s.experience_mismatch,
    s.is_stale,
    COALESCE(st.status, 'new') AS status
FROM raw_jobs r
JOIN job_scores s ON s.job_id = r.id
LEFT JOIN job_status st ON st.job_id = r.id
WHERE COALESCE(st.status, 'new') = 'new'
ORDER BY s.total_score DESC, r.date_posted DESC;
