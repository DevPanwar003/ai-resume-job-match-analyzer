# AI Resume & Job Match Analyzer — Version 3

A local Streamlit portfolio project for PDF/DOCX extraction, document statistics,
skill mention matching, TF-IDF similarity and evidence-based résumé editing prompts.
**Scores describe text alignment, not hiring success, proficiency or candidate quality.**
No API keys, paid services, LLMs or external résumé uploads are used.

## V3 features and realistic comparison demo

- Compare one PDF/DOCX resume against one to five job descriptions using the unchanged V2 engine.
- Ranked table with score, coverage, similarity, matched skills and missing skills.
- Interactive grouped and stacked Plotly charts plus the existing detailed job analysis.
- Local PDF and standalone HTML downloads with methodology, limitations, related skills and recommendations.
- Existing single-job workflow, fictional samples and opt-in SQLite history remain available.

Choose **Compare jobs** in the sidebar, then **Run three-job fictional demo**.
The real sample PDF is compared with reporting analyst, business intelligence and
machine learning roles from `samples/fictional_jobs.json`. Every role and identity
is fictional. Inspect the ranked table, choose a job for detailed feedback, and
click **Generate local reports** to enable both downloads.

For your own comparison, select one to five jobs, upload one resume, fill every
visible title and description, and click **Compare jobs**. Empty descriptions are
errors, not silently skipped. Results and reports reflect the last submitted
snapshot; submit again after editing. Exact score ties retain input order, even
if displayed rounding makes different scores look equal. N/A jobs appear last
without ranks. Adding another job never changes an existing pair's score.

![V3 comparison dashboard](docs/screenshots/v3-comparison.png)

![V3 local report downloads](docs/screenshots/v3-reports.png)

Reports omit full source documents and resume quotations by default. An explicit
checkbox includes the original bullet evidence. Job titles and skill summaries
can still be sensitive: review before sharing. Reports are generated in memory,
not written into the database or automatically saved by the application. HTML
contains no scripts or remote assets; all dynamic text is escaped. PDF uses
built-in Western fonts and replaces unsupported glyphs with `?`; use HTML for
full Unicode. Reports contain text summaries, not interactive charts.

Comparison is session-only and does not create history rows. Single-job numeric
history is unchanged, with no schema migration. Clear comparison inputs/reports
or stop the server to discard its session state. Downloads you save are outside
the app's control and remain until you delete them.

## Windows setup (PowerShell / VS Code)

Install Python 3.11 or 3.12 with the Windows Python launcher. Open this project
folder in VS Code, then run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:TEMP = "C:\pytest-temp"
$env:TMP = "C:\pytest-temp"
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp="C:\pytest-temp\resume-v2"
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8502
```

Open http://127.0.0.1:8502 in your browser. Stop with Ctrl+C. For an existing setup,
reuse the virtual environment and run the dependency install command before starting V3.
The test command requires write access to `C:\pytest-temp`; pytest owns and clears
the `resume-v2` temporary subfolder, so do not store personal files there.
If using Python 3.11, replace `py -3.12` with `py -3.11`. If only `python` is on
PATH, use `python -m venv .venv`. If neither exists, install Python and reopen the
terminal. Select `.venv\Scripts\python.exe` as VS Code's Python interpreter.
These commands do not require activation or PowerShell execution-policy changes.
Always run from the project root so Streamlit loads its local configuration.

For a directory-safe launch, run `& "<project-folder>\run.ps1"` from PowerShell.
The launcher uses its own folder, the existing `.venv`, an absolute `app.py` path,
and port 8502. It refuses to start if that port is occupied. If PowerShell blocks
scripts, use the explicit `cd` and Python command above; no policy change is needed.
After upgrading source modules, stop the old Streamlit process with Ctrl+C and
restart from this directory. A healthy HTTP endpoint only proves the server is
alive, not that its loaded Python modules are current. Verify the sidebar says
**VERSION 3**, then run the fictional demo and confirm the Job match tab contains
scores, skills and charts. Reload the browser after restarting. Unsaved session
inputs must be entered again after a server restart; SQLite history is preserved.

Dependencies: Streamlit (UI), pypdf (PDF extraction), python-docx (Word extraction),
Plotly (local charts), ReportLab (local PDF reports), pytest (tests). SQLite and the lightweight TF-IDF implementation
use Python's standard library; scikit-learn is not required. Internet is needed for initial dependency
installation; normal analysis works offline. No OCR, model downloads or paid APIs.

## Try it

1. Upload `samples/fictional_resume.pdf` or `samples/fictional_resume.docx`.
2. Paste `samples/fictional_job_description.txt`, or click **Use fictional job description**.
3. Optionally enable saving numeric statistics; click **Extract & inspect**.
4. Inspect **Job match**, **Document statistics** and **Extracted text** tabs.
5. Expand the score calculation for all skill mentions and limitations. Review suggestions
   against their original résumé lines. Use **Local history** for saved document summaries.

For a one-click end-to-end check, expand **Try fictional sample documents** and click
**Run fictional demo**. It parses the sample PDF through the actual extractor and
matches it against the full sample job description without saving history. The
description includes SQL, Python, Excel, Power BI, statistics, data cleaning and
visualization. Upload and submit your own résumé to replace the demo results.

All sample identities, organizations, experience and job details are fictional.
The TXT résumé is an editable sample source, not a supported upload format.
To rebuild sample documents: `.\.venv\Scripts\python.exe scripts\generate_samples.py`.

## Architecture

```text
app.py                         Entry point
resume_analyzer/
  ui.py                        Homepage, analysis display and history UI
  parsing.py                   In-memory PDF/DOCX extraction and file validation
  analysis.py                  Pure text validation and descriptive statistics
  taxonomy.py                  Canonical skills, aliases and explicit related pairs
  matching.py                  Skill coverage and two-document TF-IDF engine
  suggestions.py               Evidence-linked bullet editing prompts
  match_ui.py                  Match breakdown, Plotly charts and suggestions
  persistence.py               SQLite repository; parameterized values
  comparison.py                Batch validation/ranking; calls existing matching.py
  comparison_ui.py             Multi-job inputs, charts, drill-down and downloads
  reports.py                   Escaped standalone HTML and paginated in-memory PDF
samples/                       Clearly labeled fictional PDF, DOCX and TXT fixtures
scripts/generate_samples.py    Reproducible fixtures, no additional dependencies
tests/test_core.py             Parsing, validation, statistics and persistence tests
tests/test_ui.py               Streamlit rendering and form validation tests
tests/test_matching.py         Taxonomy, scoring, edge cases and evidence tests
tests/test_comparison.py       Batch, report, privacy and comparison UI regressions
samples/fictional_jobs.json    Three realistic fictional job descriptions
docs/screenshots/             Verified V3 interface screenshots
.streamlit/config.toml         Navy/teal theme, loopback binding, telemetry disabled
data/history.sqlite3           Created lazily; excluded from version control
```

Flow: UI → input validation → in-memory extraction → statistics → optional SQLite
summary. The parser and analysis functions have no Streamlit dependency. The
history repository opens/closes connections per operation and binds all SQL values
with placeholders. Schema V1 stores timestamp, format, bytes, PDF pages and word/
character counts. V2 preserves that schema and existing records; match results and
suggestions stay in session memory and are not added to history. No database migration
or data deletion is performed. Future schema changes should introduce explicit migrations.

## Matching specification (V2)

### Input sufficiency validation (V3 fix)

The shared `analyze_job_match` entry point validates user-facing single-job and
comparison requests, then delegates to the existing `analyze_match` calculation.
The latter remains a low-level mention/formula function for small mathematical
fixtures; it is not a job-description completeness check. There is only one
scoring formula, with the original **70% coverage / 30% TF-IDF** weights.

Descriptions need at least 20 word tokens, 10 distinct tokens, and an explicit
task/requirement cue (such as responsibilities, experience, build, maintain or
skills). This conservative English heuristic is not a semantic classifier and
can reject unusually concise descriptions. A list such as “Data Analyst,
Business Analyst, and Junior Data Scientist” supplies titles, not skills.
Titles are never expanded into assumed qualifications. Resume length does not
make a short job input adequate; there is no resume-to-job length ratio rule.

Insufficient descriptions, no recognized job skills, or no recognized resume
skills produce **N/A** coverage and match score. Skill gaps and suggestions are
withheld in the UI, ranked comparison and both reports. TF-IDF remains visible
as shared wording only, not skill coverage or suitability. Recognized but
disjoint skill sets can still legitimately have zero coverage. Empty inputs
continue to raise helpful validation errors.

The taxonomy additionally recognizes data analysis/analytics, dashboards,
business intelligence, communication and problem-solving, with explicit aliases,
case-insensitive whole-token boundaries and normalized Unicode hyphens. Alias
coverage may change which skills are counted; it does not change score weights.

Use **Load Data Analyst example** inside either input form to load the existing
realistic fictional Data Analyst description without replacing the uploaded
resume. In comparison mode choose the target job first. The form callback updates
only that description and preserves the other submitted inputs. Submit analysis
again to replace the previous result snapshot. Editing suggestions remain prompts
grounded in quoted source lines, never verified achievements or invented rewrites.

`taxonomy.py` is the single source of truth for canonical names, aliases and related
pairs. It includes Python, SQL, Excel, Power BI, Tableau, statistics, data visualization,
machine learning, libraries, databases, data preparation and reporting skills.
To extend it, add a canonical key with explicit aliases in `SKILLS`, optionally add
pairs in `RELATED_PAIRS`, and add extraction/scoring tests. Do not treat related
tools as aliases: pandas is related to Python but does not prove a Python mention.

Extraction normalizes Unicode (NFKC), letter case, whitespace and hyphen variants,
and uses whole-token boundaries. Aliases collapse to one canonical skill per document.
Matched = résumé ∩ job skills; missing = job skills not mentioned in the résumé.
Related entries connect a missing job skill to a detected résumé skill through an
explicit, symmetric taxonomy pair. They remain missing and earn no coverage credit.
All detected skills are shown, including résumé-only skills.

### Score and charts

For nonempty validated inputs with at least one recognized job skill:

```text
coverage = unique matched skills / unique job skills
score = 100 × (0.70 × coverage + 0.30 × TF-IDF cosine similarity)
```

The 70/30 weights are transparent design choices, not learned or calibrated hiring
weights. Every unique job skill has equal weight; required and preferred skills are
not distinguished. Duplicates and aliases cannot increase skill coverage.

TF-IDF is fitted to just the résumé and job description (N=2). Tokens are normalized
Unicode word tokens of at least two characters; punctuation splits tokens. A small
explicit English stopword set is in `matching.py`. There is no stemming or alias
canonicalization in the TF-IDF component. For each term:

```text
TF = 1 + ln(term count) when present, else 0
IDF = 1 + ln((1 + N) / (1 + document frequency))
vector weight = TF × IDF
cosine = dot product / (L2 norm of résumé × L2 norm of job)
```

This uses the documented smoothed IDF and sublinear TF conventions described in
[scikit-learn's TF-IDF reference](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfTransformer.html),
implemented locally with standard-library counters and math. Empty vectors return
zero similarity. Empty/whitespace/punctuation-only match inputs are rejected.
When no job skills are recognized, coverage and total score are **N/A**, not zero;
text similarity is still displayed independently. The skill chart counts matched
and missing skills; the contribution chart shows up to 70 coverage points and 30
similarity points. Display rounding does not affect calculations.

### Suggestions and limitations

Suggestions quote up to five existing bullet-like or action-led lines and ask for
clearer contribution, verified scope/outcomes, or explanation of already-mentioned
job skills. They do not write fabricated achievements, numbers or qualifications.
No suitable lines means no personalized suggestions. A number alone is not proof
of impact; users are asked to verify its meaning. Missing skills should only be
added if actually possessed and supported by evidence.

- Skills are **mentions**, not verified abilities. Negation is not understood:
  “no Python experience” still mentions Python. Inspect the extracted text.
- Ambiguous aliases such as Excel or ML can create false positives. The curated
  English-oriented taxonomy is incomplete; absence is not proof of a skill gap.
- TF-IDF is lexical, not semantic. Equivalent wording can differ, and repeated
  keywords can influence similarity despite sublinear TF. Repetition does not
  improve skill coverage. Pair-specific IDF means scores are not standardized
  across different jobs and should not be used to rank applicants.
  V3 ranks opportunities for one resume as an exploratory aid only; this is not
  a calibrated comparison of job suitability or a candidate selection system.
- Extraction order/errors, document length, optional skills and unrelated mentions
  can change results. Neither years of experience nor expertise is assessed.
- This is a résumé editing aid. **It does not predict hiring success or ATS outcomes.**

## Privacy and boundaries

- App binds to `127.0.0.1`. Uploaded bytes and source text stay in local process/
  browser session memory; the application does not transmit them to external services.
- History is opt-in and stores numeric summaries only, never filenames, names,
  résumé text or job-description text. SQLite is local and unencrypted.
- No user document caching, raw-content logging or automatic source-file writes.
  Clear session inputs/results after use; close the browser and stop the server
  to release process memory. This is not a guarantee of forensic memory erasure.
- Uploaded content is rendered as plain text, never interpolated into HTML.
- Delete history in the UI, or stop the app and delete `data/history.sqlite3`.
- Streamlit usage telemetry is disabled. Configuration reference:
  https://docs.streamlit.io/develop/api-reference/configuration/config.toml

## Validation and limitations

Accepts PDF/DOCX up to 5 MiB; PDF up to 50 pages. DOCX declared uncompressed
content is capped at 25 MiB. Job and extracted résumé text have a 100,000-character
limit and must contain letters or numbers. Empty, damaged, wrong-format and
encrypted files receive actionable messages. Scans require OCR outside this app.
Complex PDFs may have imperfect reading order; DOCX includes body paragraphs and
tables but not headers, footers or text boxes. DOCX page counts are unavailable.
The size limits reduce resource use; parsing is not isolated in a sandbox and
the app is intended for trusted local documents, not a public upload service.

Word counts use Unicode word tokens and preserve internal hyphens/apostrophes;
unique words ignore case. Character counts include whitespace after trimming the
outer whitespace; line counts include only nonempty lines. These metrics do not
measure job suitability. Displayed results belong to the last successful submission.

Tests cover both formats, corrupted and empty files, unsupported types, limits,
password PDFs, blank documents, Unicode statistics, table text, history privacy,
and basic UI behavior. No résumé is uploaded during automated tests.

V2 tests additionally cover taxonomy aliases, duplicates, boundaries, missing and
related skills, hand-calculated TF-IDF values, weighted scores, no-skill and empty
inputs, score bounds, evidence provenance, charts and unchanged history behavior.
Semantic models and generated rewrites remain outside this version's scope.

## Verified initial V3 checks (before validation/taxonomy update)

The full suite passed **80 tests in 5.31 seconds** on Python 3.12 using the
TEMP/TMP command above. All 57 pre-existing collected test IDs remain present;
23 cases were added. The existing branding assertion was updated from V2 to V3,
with all scoring, extraction and privacy assertions retained. Dependency checks
passed. Browser verification on port 8502 exercised the three-job demo, ranked
results, charts and generation of both report downloads. All four pages of the
fictional PDF were rendered and visually inspected.

The initial fictional demo scored 79.51, 19.99 and 9.86 for reporting, business
intelligence and machine learning respectively. These are reproducibility examples,
not recommendations about real jobs or predictions of hiring success.

## Validation/taxonomy fix verification

The updated suite passed **107 tests in 6.00 seconds** with the existing virtual
environment and Windows TEMP/TMP workaround. All 80 pre-fix test IDs remain; 27
cases were added. Existing UI/report fixtures now use full descriptions where
they test a calculated score; low-level formula tests retain their original
keyword inputs and assertions. No tests were removed. The SQLite file hash was
unchanged. Live browser verification confirmed that the reported eight-word
title list produces N/A score/coverage, separate lexical similarity, an explicit
warning and no inferred skill gaps or recommendations. Loading the Data Analyst
example retained the uploaded fictional PDF. Taxonomy expansion can change demo
scores by recognizing more explicit mentions; the 70/30 formula is unchanged.

## Job Title Intelligence

Choose **Auto-detect from title** or override **Job role** in either analysis form.
Enter a whole title such as `Data Analyst job` or `Software Engineer`; comparisons
also accept a supported title with an empty description. An explicit role selection
can be used without a description. Ambiguous lists and unknown titles still require
a complete description or a supported selection. Auto-detection uses the first line,
with optional `Job title:` and junior/senior prefixes, and case-insensitive aliases.

Supported roles: Data Analyst, Business Analyst, Data Scientist, Software Engineer,
Python Developer, Java Developer, Web Developer, Frontend Developer, Backend Developer,
Full Stack Developer, Machine Learning Engineer, Database Administrator.

`resume_analyzer/role_skills.py` holds editable profiles, aliases, categories and
importance weights (essential 2, preferred 1). These weights order roadmap guidance;
they do not change the existing unique-skill coverage or 70% coverage / 30% TF-IDF
formula. Title-only similarity compares the resume with generated catalog text,
shown in the analysis, rather than the few title words. Profiles are illustrative,
not verified employer requirements. A meaningful full description takes precedence:
its recognized skills replace generic requirements, with explicit essential/preferred
labels retained and other mentions marked unspecified. Put the title on its own first
line or select a role when providing a full description.

The matcher and roadmap retain strict description validation when called without the
optional `role` argument; the UI enables catalog resolution explicitly. Existing
comparison/report/history behavior is retained. Guidance does not verify proficiency,
and scores do not predict hiring success. Generic profiles may omit relevant skills.

### Temporary and saved custom profiles

Unknown titles with a complete description now get a temporary, locally extracted
profile. Use **Preview role skills** before submitting to review essential,
preferred and unspecified mentions. Provide an optional title in Analyze; the
comparison form already has title fields. The existing description quality gate
requires at least 20 words, 10 distinct words, task/requirement context and at least
one taxonomy skill. A profile is a deterministic summary, not machine learning:
unlisted skills, negation, ambiguous terms and complex requirement wording may be
missed. Full descriptions replace generic built-in or saved skill requirements.

**Save this role locally** is explicit opt-in. Only the reviewed custom title and
canonical skills/importance are stored in `data/custom_roles.sqlite3`; neither
resume text nor job-description bodies are saved. Avoid personal information in
role titles. The built-in catalog and numeric history database are separate.
Case-insensitive duplicate titles are rejected; use **Edit saved roles** to update
skill selections/importance or explicitly confirm deletion. Saved roles become
available in both selectors and in future sessions. Existing analysis snapshots
remain unchanged when a saved profile is edited or removed.

**Show skill improvement advice** defaults to unchecked. It controls roadmap and
bullet advice in both analysis views, without changing scores or clearing results.
The preference survives navigation within the session. Enable it to see practice
tasks, approximate learning times and the suggested four-week plan. Existing report
exports remain independently generated summaries, including their recommendations.
