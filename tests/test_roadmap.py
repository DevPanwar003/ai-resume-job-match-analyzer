from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from resume_analyzer.roadmap import build_roadmap, requirement_levels, GUIDANCE, PREREQUISITES
from resume_analyzer.taxonomy import SKILLS

JOB = '''Responsibilities: build reliable weekly reports, validate source records, explain assumptions and present results clearly to the operations team.
Essential skills: SQL; pandas.
Preferred skills: Python; Tableau.'''


def test_missing_existing_related_and_dependency_order():
    roadmap = build_roadmap('Power BI and SQL', JOB)
    assert roadmap.detected == ('Power BI', 'SQL')
    assert [s.skill for s in roadmap.steps] == ['Python', 'pandas', 'Tableau']
    assert roadmap.steps[0].importance == 'Preferred'
    assert 'foundation' in roadmap.steps[0].reason
    assert roadmap.steps[1].importance == 'Essential'
    assert roadmap.steps[1].prerequisites == ('Python',)
    assert roadmap.steps[2].related == ('Power BI',)
    assert len(roadmap.weeks) == 4
    assert all(step.exercise and step.goal and step.hours for step in roadmap.steps)


def test_essential_before_preferred_without_dependencies():
    levels = requirement_levels('Required: SQL.\nPreferred: Tableau.\nResponsibilities: use Excel.')
    assert levels == {'SQL': 'Essential', 'Tableau': 'Preferred', 'Excel': 'Not specified'}
    roadmap = build_roadmap('Python', JOB)
    assert [s.skill for s in roadmap.steps] == ['pandas', 'SQL', 'Tableau']
    assert build_roadmap('Python', JOB) == roadmap


@pytest.mark.parametrize('resume,job', [('', JOB), ('Python', ''), ('Python', 'Data Analyst'),
    ('Python', 'Responsibilities: maintain office supplies, prepare meeting rooms and help visitors locate their appointments while keeping routine records for the office team each morning.')])
def test_unavailable_inputs_do_not_generate_plan(resume, job):
    roadmap = build_roadmap(resume, job)
    assert roadmap.message
    assert roadmap.steps == roadmap.weeks == ()


def test_no_gap_does_not_invent_recommendations():
    roadmap = build_roadmap('SQL pandas Python Tableau', JOB)
    assert not roadmap.steps and not roadmap.weeks
    assert 'do not verify proficiency' in roadmap.message


def test_guidance_covers_taxonomy_and_dependencies_are_acyclic():
    assert set(GUIDANCE) == set(SKILLS)
    def visit(skill, path):
        assert skill not in path
        for parent in PREREQUISITES.get(skill, ()):
            assert parent in SKILLS
            visit(parent, path + [skill])
    for skill in SKILLS:
        visit(skill, [])


def test_roadmap_rendered_in_existing_analysis():
    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / 'app.py'), default_timeout=15).run()
    next(c for c in app.checkbox if c.label == 'Show skill improvement advice').check().run()
    next(b for b in app.button if b.label == 'Run fictional demo').click().run()
    assert not app.exception
    assert any(s.value == 'Your Skill Improvement Roadmap' for s in app.subheader)
    assert any('Approximate suggested learning time' in m.value for m in app.markdown)
    assert sum('Week ' in m.value for m in app.markdown) == 4
