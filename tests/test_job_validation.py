from io import BytesIO
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from pypdf import PdfReader
from resume_analyzer.analysis import ValidationError, text_stats
from resume_analyzer.comparison import compare_jobs, comparison_rows
from resume_analyzer.matching import analyze_job_match, analyze_match, tfidf_similarity
from resume_analyzer.parsing import extract_resume
from resume_analyzer.reports import html_report, pdf_report
from resume_analyzer.taxonomy import extract_skills

ROOT = Path(__file__).resolve().parents[1]
TITLE = 'Data Analyst, Business Analyst, and Junior Data Scientist.'
RESUME = 'Built Python SQL reports and checked source records for the team.'
JOB = 'Responsibilities: use Python and SQL to prepare weekly reports, inspect source records, document assumptions and explain results clearly to the operations team.'


@pytest.mark.parametrize('page,submit', [('Analyze', 'Extract & inspect'), ('Compare jobs', 'Compare jobs')])
def test_empty_description_ui_requests_complete_description(page, submit, monkeypatch):
    import streamlit as st
    uploaded = BytesIO((ROOT / 'samples/fictional_resume.pdf').read_bytes())
    uploaded.name = 'fictional.pdf'
    monkeypatch.setattr(st, 'file_uploader', lambda *args, **kwargs: uploaded)
    app = AppTest.from_file(str(ROOT / 'app.py')).run()
    app.radio[0].set_value(page).run()
    app.text_area[0].input(' \n\t')
    next(b for b in app.button if b.label == submit).click().run()
    assert not app.exception
    assert any('description is empty' in error.value for error in app.error)
    assert any('complete job description' in warning.value for warning in app.warning)
    assert len(app.metric) == 0  # Rejected input must not display a fabricated score.
    assert len(app.dataframe) == 0


def test_alias_case_and_boundaries_in_same_input():
    assert set(extract_skills('pYtHoN; PoWeRbI / SQL. NoSQL excellent pythonista dashboardish')) == {'Python', 'Power BI', 'SQL'}


@pytest.mark.parametrize('text,skills', [
    ('PYTHON, sql; MS EXCEL / PowerBI (Tableau)', {'Python', 'SQL', 'Excel', 'Power BI', 'Tableau'}),
    ('DATA ANALYTICS, Statistical Analysis; DATA VISUALISATION', {'Data analysis', 'Statistics', 'Data visualization'}),
    ('PANDAS, numpy; Machine-Learning!', {'pandas', 'NumPy', 'Machine learning'}),
    ('ETL; extract, transform, load; DASHBOARDING; Business Intelligence', {'ETL', 'Dashboards', 'Business intelligence'}),
    ('Communication Skills; presenting findings; problem-solving / solve problems', {'Communication', 'Problem-solving'}),
    ('Power\nBI and data‑analysis', {'Power BI', 'Data analysis'}),
])
def test_expanded_aliases(text, skills):
    assert set(extract_skills(text)) == skills


@pytest.mark.parametrize('text', ['NoSQL excellent', 'pythonista sqlserver', 'dashboardish', 'miscommunication', 'problematic', 'biography', TITLE])
def test_no_substrings_or_inferred_title_skills(text):
    assert extract_skills(text) == ()


@pytest.mark.parametrize('job', [TITLE, 'Python Data Analyst', 'Python SQL Excel', 'Python ' * 30,
    'Data Analyst Business Analyst Junior Data Scientist Senior Data Analyst Business Analyst Junior Data Scientist Senior Data Analyst Business Analyst Junior Data Scientist'])
def test_insufficient_evidence_withholds_score_and_gaps(job):
    result = analyze_job_match(RESUME, job)
    assert result.score is None and result.coverage is None
    assert 'complete job description' in result.warning
    assert result.matched == result.missing == result.related == ()
    assert result.similarity == tfidf_similarity(RESUME, job)


@pytest.mark.parametrize('job', ['', ' \n', None, '!!!'])
def test_empty_or_invalid_job_rejected(job):
    with pytest.raises(ValidationError):
        analyze_job_match(RESUME, job)


def test_valid_description_uses_unchanged_formula():
    result = analyze_job_match(RESUME, JOB)
    assert result == analyze_match(RESUME, JOB)
    assert result.coverage == 1
    assert result.score == pytest.approx(70 + 30 * result.similarity)


def test_no_skills_in_either_input_not_misleading_zero():
    job = 'Responsibilities: prepare weekly schedules for the team, arrange meeting rooms, maintain office supplies, support visitors and document routine requests carefully each morning.'
    result = analyze_job_match(RESUME, job)
    assert result.score is None and result.coverage is None
    assert 'No taxonomy skills' in result.warning
    result = analyze_job_match('Friendly colleague with reliable attendance.', JOB)
    assert result.score is None and result.missing == ()
    # Recognized but disjoint skills are a real zero coverage, not unavailable.
    assert analyze_job_match('Tableau', JOB).coverage == 0


def test_mixed_comparison_and_reports_withhold_recommendations():
    results = compare_jobs(RESUME, [('Title only', TITLE), ('Valid role', JOB)])
    assert [item.index for item in results] == [2, 1]
    invalid = results[-1]
    assert invalid.suggestions == ()
    assert comparison_rows(results)[-1]['Missing skills'] == 'Not assessed'
    for output in [html_report((invalid,), True).decode(), ' '.join(p.extract_text() for p in PdfReader(BytesIO(pdf_report((invalid,), True))).pages)]:
        assert 'complete job description' in output
        assert 'withheld' in output
        assert 'Suggestion 1:' not in output
        assert 'Evidence 1:' not in output


def test_title_only_single_job_ui_and_sample_preserves_upload(monkeypatch):
    import streamlit as st
    uploaded = BytesIO((ROOT / 'samples/fictional_resume.pdf').read_bytes())
    uploaded.name = 'fictional.pdf'
    monkeypatch.setattr(st, 'file_uploader', lambda *args, **kwargs: uploaded)
    app = AppTest.from_file(str(ROOT / 'app.py')).run()
    app.text_area[0].input(TITLE)
    next(b for b in app.button if b.label == 'Extract & inspect').click().run()
    assert not app.exception
    assert next(m for m in app.metric if m.label == 'Match score / 100').value == 'N/A'
    assert next(m for m in app.metric if m.label == 'Skill coverage').value == 'N/A'
    assert any('complete job description' in w.value for w in app.warning)
    assert not any('This line mentions' in m.value for m in app.markdown)
    assert not app.get('plotly_chart')
    next(b for b in app.button if b.label == 'Load Data Analyst example').click().run()
    assert 'Responsibilities:' in app.text_area[0].value
    next(b for b in app.button if b.label == 'Extract & inspect').click().run()
    assert not app.exception
    assert next(m for m in app.metric if m.label == 'Match score / 100').value != 'N/A'
    assert app.code[0].value == extract_resume(uploaded.name, uploaded.getvalue()).text


def test_comparison_sample_load_keeps_resume_and_warns_per_job(monkeypatch):
    import streamlit as st
    uploaded = BytesIO((ROOT / 'samples/fictional_resume.pdf').read_bytes())
    uploaded.name = 'fictional.pdf'
    monkeypatch.setattr(st, 'file_uploader', lambda *args, **kwargs: uploaded)
    app = AppTest.from_file(str(ROOT / 'app.py')).run()
    app.radio[0].set_value('Compare jobs').run()
    app.text_area[1].input(TITLE)
    next(b for b in app.button if b.label == 'Load Data Analyst example').click().run()
    assert app.text_area[1].value == TITLE
    next(b for b in app.button if b.label == 'Compare jobs').click().run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 2
    assert app.dataframe[0].value.iloc[-1]['Rank'] == 'N/A'
    assert any('Job 2: Insufficient' in w.value for w in app.warning)
