from pathlib import Path
from io import BytesIO
import pytest
from streamlit.testing.v1 import AppTest
from resume_analyzer.role_skills import AUTO, ROLES, detect_role, resolve_role
from resume_analyzer.matching import analyze_job_match, analyze_match
from resume_analyzer.roadmap import build_roadmap
from resume_analyzer.taxonomy import SKILLS, extract_skills
from resume_analyzer.comparison import compare_jobs
from resume_analyzer.reports import html_report


@pytest.mark.parametrize('title,expected', [('Data Analyst job', 'Data Analyst'), ('SWE', 'Software Engineer'), ('front-end developer', 'Frontend Developer'), ('Senior ML Engineer', 'Machine Learning Engineer'), ('Job title: DBA', 'Database Administrator')])
def test_title_aliases(title, expected):
    assert detect_role(title) == expected


def test_catalog_integrity_and_all_profiles_score():
    for name, role in ROLES.items():
        assert len({r.skill for r in role.requirements}) == len(role.requirements)
        assert all(r.skill in SKILLS and r.weight in (1, 2) and r.category for r in role.requirements)
        result = analyze_job_match('Python SQL Java HTML Git', name, role=AUTO)
        assert result.score is not None and result.role == name
        raw = analyze_match('Python SQL Java HTML Git', result.effective_job)
        assert result.score == raw.score
        assert result.coverage == len(result.matched) / len(result.job_skills)
        assert result.score == pytest.approx(result.skill_points + result.text_points)
        assert build_roadmap('Python SQL Java HTML Git', name, role=AUTO).steps


def test_unknown_and_ambiguous_roles_do_not_score():
    for text in ('Wizard job', 'Data Analyst, Business Analyst', 'Python Data Analyst'):
        result = analyze_job_match('Python SQL', text, role=AUTO)
        assert result.score is None and result.coverage is None
        assert 'supported role' in result.warning
        assert not result.missing


def test_full_description_refines_and_override_wins():
    job = ('Responsibilities: use SQL to prepare weekly reports, inspect source records, document assumptions and explain results clearly to the operations team.\n'
           'Essential skills: SQL.\nPreferred skills: Tableau.')
    result = analyze_job_match('SQL', job, role='Data Analyst')
    assert result.job_skills == ('SQL', 'Tableau')
    assert result.score == analyze_match('SQL', job).score
    assert {r.skill: r.weight for r in result.requirements} == {'SQL': 2, 'Tableau': 1}
    assert analyze_job_match('Java', 'Data Analyst job', role='Java Developer').role == 'Java Developer'
    roadmap = build_roadmap('SQL', job, role='Data Analyst')
    assert [(s.skill, s.importance) for s in roadmap.steps] == [('Tableau', 'Preferred')]
    assert analyze_job_match('SQL', 'Data Analyst\n' + job, role=AUTO).role == 'Data Analyst'
    compared = compare_jobs('SQL', [('Data Analyst', job)], roles=[AUTO])[0]
    assert compared.match == result


def test_comparison_consistent_with_details_and_reports():
    results = compare_jobs('Python SQL', [('Data Analyst', ''), ('Java Developer', '')], roles=[AUTO, AUTO])
    for item in results:
        detail = analyze_job_match('Python SQL', item.description, role=item.match.role)
        assert detail == item.match
    report = html_report(results).decode()
    assert 'Selected catalog role: Data Analyst' in report
    assert 'Essential:' in report


def test_new_skill_boundaries():
    assert set(extract_skills('JAVA JavaScript HTML5 CSS3 RESTful APIs Spring Boot')) == {'Java', 'JavaScript', 'HTML', 'CSS', 'REST APIs', 'Spring'}
    assert extract_skills('JavaScript') == ('JavaScript',)
    assert extract_skills('javanese dockerish reacting') == ()


def test_title_ui_and_submitted_override_snapshot(monkeypatch):
    import streamlit as st
    root = Path(__file__).resolve().parents[1]
    uploaded = BytesIO((root / 'samples/fictional_resume.pdf').read_bytes())
    uploaded.name = 'fictional.pdf'
    monkeypatch.setattr(st, 'file_uploader', lambda *a, **k: uploaded)
    app = AppTest.from_file(str(root / 'app.py'), default_timeout=15).run()
    next(c for c in app.checkbox if c.label == 'Show skill improvement advice').check().run()
    app.text_area[0].input('Data Analyst job')
    next(b for b in app.button if b.label == 'Extract & inspect').click().run()
    assert not app.exception
    assert next(m for m in app.metric if m.label == 'Match score / 100').value != 'N/A'
    assert any('Selected role: Data Analyst' in m.value for m in app.markdown)
    assert any(s.value == 'Your Skill Improvement Roadmap' for s in app.subheader)
    next(s for s in app.selectbox if s.label == 'Job role').set_value('Java Developer')
    next(b for b in app.button if b.label == 'Extract & inspect').click().run()
    assert not app.exception
    assert any('Selected role: Java Developer' in m.value for m in app.markdown)
