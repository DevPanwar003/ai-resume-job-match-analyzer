from io import BytesIO
from pathlib import Path
import json
import pytest
from pypdf import PdfReader
from streamlit.testing.v1 import AppTest
from resume_analyzer.analysis import ValidationError
from resume_analyzer.comparison import compare_jobs, compare_document, comparison_rows
from resume_analyzer.matching import analyze_match, analyze_job_match
from resume_analyzer.reports import html_report, pdf_report, WARNING

ROOT = Path(__file__).resolve().parents[1]


def description_for(skills):
    return f'Responsibilities: use {skills} to prepare reliable weekly reports for the team, check source records carefully, document assumptions and explain results clearly.'


@pytest.mark.parametrize('count', [1, 2, 3, 4, 5])
def test_multiple_jobs_use_identical_engine(count):
    jobs = [(f'Role {i}', description_for(description)) for i, description in enumerate(['SQL', 'Python', 'Excel SQL', 'Power BI', 'Helpful colleague'][:count])]
    results = compare_jobs('Built Python SQL reports for a team.', jobs)
    assert len(results) == count
    for result in results:
        assert result.match == analyze_job_match('Built Python SQL reports for a team.', result.description)
        if result.match.warning is None:
            assert result.match == analyze_match('Built Python SQL reports for a team.', result.description)
    scores = [item.match.score for item in results if item.match.score is not None]
    assert scores == sorted(scores, reverse=True)


def test_ranking_ties_na_and_duplicate_titles():
    results = compare_jobs('Python', [('Same', description_for(skills)) for skills in ['unknown words', 'SQL', 'Python', 'Python']])
    assert [item.index for item in results] == [3, 4, 2, 1]
    assert comparison_rows(results)[-1]['Rank'] == 'N/A'
    assert comparison_rows(results)[-1]['Match score / 100'] is None


@pytest.mark.parametrize('jobs', [[], [('Role', 'Python')] * 6, [('Role', '')], [('Role', ' \n')], [('Role', '!!!')], [('', 'SQL')], [('x' * 101, 'SQL')]], ids=['zero', 'six', 'empty', 'whitespace', 'punctuation', 'empty-title', 'long-title'])
def test_invalid_jobs(jobs):
    with pytest.raises(ValidationError):
        compare_jobs('Python', jobs)


@pytest.mark.parametrize('name,content', [('bad.pdf', b'not pdf'), ('blank.docx', b''), ('resume.txt', b'Python')])
def test_invalid_document_in_comparison(name, content):
    with pytest.raises(ValidationError):
        compare_document(name, content, [('Role', 'Python')])


def test_reports_agree_with_scores_and_preserve_privacy():
    results = compare_jobs('Built Python reports for PRIVATECLIENT.', [('Role', description_for('Python SQL'))])
    html = html_report(results).decode()
    pdf = pdf_report(results)
    reader = PdfReader(BytesIO(pdf))
    text = ' '.join('\n'.join(page.extract_text() for page in reader.pages).split())
    for output in (html, text):
        assert WARNING in output
        assert f'{results[0].match.score:.2f}/100' in output
        assert 'Matched skills: Python' in output
        assert 'Missing skills: SQL' in output
        assert 'Recommendations:' in output
        assert 'TF-IDF' in output
        assert 'PRIVATECLIENT' not in output
    assert len(reader.pages) == 2
    assert 'PRIVATECLIENT' in html_report(results, True).decode()
    assert 'PRIVATECLIENT' in ''.join(page.extract_text() for page in PdfReader(BytesIO(pdf_report(results, True))).pages)


def test_html_escapes_untrusted_text_and_has_no_remote_assets():
    results = compare_jobs('Built Python reports <script>alert(1)</script>.', [('<img src=x onerror=alert(1)>', description_for('Python'))])
    html = html_report(results, True).decode()
    assert '<script>' not in html and '<img' not in html
    assert '&lt;script&gt;' in html and '&lt;img' in html
    assert "default-src 'none'" in html
    assert 'https://' not in html
    assert pdf_report(results, True).startswith(b'%PDF-')


def test_reports_na_and_long_evidence():
    results = compare_jobs('Built Python reports ' + 'details ' * 600, [('Unicode café 漢字', 'helpful colleague'), ('Valid role', description_for('Python'))])
    assert 'N/A' in html_report(results).decode()
    assert '漢字' in html_report(results).decode()
    reader = PdfReader(BytesIO(pdf_report(results, True)))
    assert len(reader.pages) >= 3
    assert 'N/A' in ''.join(page.extract_text() for page in reader.pages)


@pytest.mark.parametrize('renderer', [html_report, pdf_report])
def test_empty_reports_rejected(renderer):
    with pytest.raises(ValueError):
        renderer(())


def test_comparison_demo_ui_and_downloads():
    app = AppTest.from_file(str(ROOT / 'app.py')).run()
    app.radio[0].set_value('Compare jobs').run()
    next(b for b in app.button if b.label == 'Run three-job fictional demo').click().run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 3
    assert len(app.get('plotly_chart')) == 4
    assert any(WARNING == item.value for item in app.warning)
    next(b for b in app.button if b.label == 'Generate local reports').click().run()
    assert not app.exception
    assert len(app.get('download_button')) == 2
    reports = app.session_state['comparison_reports']
    assert reports[1].startswith(b'<!doctype html>')
    assert reports[2].startswith(b'%PDF-')
    # Changing privacy choice hides downloads until reports are regenerated.
    next(c for c in app.checkbox if c.label == 'Include resume quotations in reports').check().run()
    assert len(app.get('download_button')) == 0


def test_comparison_form_submission_and_invalidates_stale_results(monkeypatch):
    import streamlit as st
    uploaded = BytesIO((ROOT / 'samples/fictional_resume.docx').read_bytes())
    uploaded.name = 'fictional.docx'
    monkeypatch.setattr(st, 'file_uploader', lambda *args, **kwargs: uploaded)
    app = AppTest.from_file(str(ROOT / 'app.py')).run()
    app.radio[0].set_value('Compare jobs').run()
    app.text_area[0].input(description_for('Python SQL'))
    app.text_area[1].input(description_for('Excel Power BI'))
    next(b for b in app.button if b.label == 'Compare jobs').click().run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 2
    app.text_area[1].input('')
    next(b for b in app.button if b.label == 'Compare jobs').click().run()
    assert 'Job 2 description is empty' in app.error[0].value
    assert len(app.dataframe) == 0
    assert len(app.get('download_button')) == 0
