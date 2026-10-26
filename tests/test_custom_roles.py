from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from resume_analyzer.analysis import ValidationError
from resume_analyzer.custom_roles import CustomRoleStore
from resume_analyzer.role_skills import AUTO, Requirement, resolve_role
from resume_analyzer.matching import analyze_job_match, analyze_match
from resume_analyzer.comparison import compare_jobs

JOB = ('Responsibilities: prepare weekly reports, inspect source records, document assumptions and explain results clearly to the operations team while checking totals carefully.\n'
       'Essential skills: SQL.\nPreferred skills: Tableau.')


@pytest.fixture
def store(tmp_path, monkeypatch):
    import resume_analyzer.custom_roles as module
    monkeypatch.setattr(module, 'DEFAULT_DB', tmp_path / 'profiles.sqlite3')
    return CustomRoleStore()


def test_unknown_profile_extraction_and_unchanged_scoring(store):
    job = 'Operations Insight Specialist\n' + JOB
    name, effective, requirements = resolve_role(job)
    assert name == 'Operations Insight Specialist'
    assert effective == job
    assert {r.skill: r.weight for r in requirements} == {'SQL': 2, 'Tableau': 1}
    result = analyze_job_match('SQL', job, role=AUTO)
    assert result.score == analyze_match('SQL', job).score
    assert result.coverage == .5 and result.missing == ('Tableau',)
    assert not store.path.exists()  # Resolution/preview must never save.


@pytest.mark.parametrize('job', ['Operations Specialist', 'SQL specialist', 'Responsibilities: inspect records and prepare reports for the team each morning while carefully documenting assumptions and checking totals before presenting results.'])
def test_insufficient_profile_not_fabricated(store, job):
    name, _, requirements = resolve_role(job)
    assert name is None and requirements == ()
    result = analyze_job_match('SQL', job, role=AUTO)
    assert result.score is None and result.missing == ()


def test_custom_crud_duplicates_refinement_and_builtin_protection(store):
    requirements = resolve_role('Operations Specialist\n' + JOB)[2]
    store.save('Operations Specialist', requirements)
    assert CustomRoleStore(store.path).load()['Operations Specialist'].requirements == requirements
    with pytest.raises(ValidationError, match='already exists'):
        store.save(' OPERATIONS   SPECIALIST ', requirements)
    for alias in ('Data Analyst', 'SWE'):
        with pytest.raises(ValidationError, match='built-in'):
            store.save(alias, requirements)
    result = analyze_job_match('SQL', 'operations specialist', role=AUTO)
    assert result.role == 'Operations Specialist' and result.coverage == .5
    refined = analyze_job_match('SQL', JOB, role='Operations Specialist')
    assert refined.score == analyze_match('SQL', JOB).score
    store.save('Operations Specialist', (Requirement('Python', 'Programming', 0),), replace=True)
    assert analyze_job_match('Python', 'Operations Specialist', role=AUTO).coverage == 1
    assert result.coverage == .5  # Previous immutable snapshot is unchanged.
    assert compare_jobs('Python', [('Operations Specialist', '')], roles=[AUTO])[0].match.coverage == 1
    store.delete('OPERATIONS SPECIALIST')
    assert store.load() == {}
    assert analyze_job_match('SQL', 'Operations Specialist', role=AUTO).score is None


def test_invalid_edits_and_parameterized_titles(store):
    with pytest.raises(ValidationError):
        store.save('Custom', ())
    requirements = (Requirement('SQL', 'Databases', 2),)
    title = "Analyst'); DROP TABLE custom_roles;--"
    store.save(title, requirements)
    assert title in store.load()
    with pytest.raises(ValidationError):
        store.save(title, requirements * 2, replace=True)
    assert store.load()[title].requirements == requirements
    store.delete(title)
    assert store.load() == {}


def checkbox(app):
    return next(c for c in app.checkbox if c.label == 'Show skill improvement advice')


def test_advice_default_toggle_navigation_and_no_generation(store, monkeypatch):
    import resume_analyzer.roadmap_ui as roadmap_ui
    calls = []
    original = roadmap_ui.build_roadmap
    def spy(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)
    monkeypatch.setattr(roadmap_ui, 'build_roadmap', spy)
    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / 'app.py'), default_timeout=15).run()
    assert not checkbox(app).value
    next(b for b in app.button if b.label == 'Run fictional demo').click().run()
    metrics = [(m.label, m.value) for m in app.metric]
    assert not calls
    assert not any(s.value in ('Your Skill Improvement Roadmap', 'Evidence-based bullet suggestions') for s in app.subheader)
    checkbox(app).check().run()
    assert calls and any(s.value == 'Your Skill Improvement Roadmap' for s in app.subheader)
    assert [(m.label, m.value) for m in app.metric] == metrics
    app.radio[0].set_value('Compare jobs').run()
    assert checkbox(app).value
    next(b for b in app.button if b.label == 'Run three-job fictional demo').click().run()
    assert any(s.value == 'Your Skill Improvement Roadmap' for s in app.subheader)
    checkbox(app).uncheck().run()
    assert not any(s.value == 'Your Skill Improvement Roadmap' for s in app.subheader)
    app.radio[0].set_value('Analyze').run()
    assert not checkbox(app).value
    assert [(m.label, m.value) for m in app.metric] == metrics
    assert not app.exception


def test_preview_save_is_explicit_and_editor_available(store):
    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / 'app.py'), default_timeout=15).run()
    next(t for t in app.text_input if t.label == 'Job title (optional)').input('Operations Specialist')
    app.text_area[0].input(JOB)
    next(b for b in app.button if b.label == 'Preview role skills').click().run()
    assert not app.exception and not app.metric
    assert any('Review role/profile: Operations Specialist' in m.value for m in app.markdown)
    assert not store.path.exists()
    next(b for b in app.button if b.label == 'Save this role locally').click().run()
    assert 'Operations Specialist' in store.load()
    app.run()
    assert 'Operations Specialist' in next(s for s in app.selectbox if s.label == 'Job role').options
    next(c for c in app.checkbox if c.label == 'Confirm deletion of this custom role').check().run()
    next(b for b in app.button if b.label == 'Delete custom role').click().run()
    assert not app.exception and not store.load()
