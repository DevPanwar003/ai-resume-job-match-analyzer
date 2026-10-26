"""Deterministic learning guidance; never changes matching scores or infers ability."""
from dataclasses import dataclass
import re
from .analysis import ValidationError
from .matching import analyze_job_match
from .taxonomy import extract_skills, normalize

# Suggested learning dependencies, not additional job requirements.
PREREQUISITES = {
    'pandas': ('Python',), 'NumPy': ('Python',),
    'Machine learning': ('Python', 'Statistics'),
    'scikit-learn': ('Python', 'Machine learning'),
    'TensorFlow': ('Python', 'Machine learning'), 'PyTorch': ('Python', 'Machine learning'),
    'Matplotlib': ('Python',), 'Seaborn': ('Python',), 'Plotly': ('Python',),
    'Streamlit': ('Python',), 'Regression': ('Statistics',), 'A/B testing': ('Statistics',),
    'DAX': ('Power BI',), 'Pivot tables': ('Excel',),
    'ETL': ('SQL', 'Data cleaning'),
}

# Every taxonomy skill has a predefined exercise, approximate effort and goal.
GUIDANCE = {}
for names, exercise, hours, goal in (
    (('Python', 'pandas', 'NumPy'), 'Clean and summarize a fictional CSV using {skill}; keep a reproducible script.', '8-16', 'Process 100 rows and verify five output values against hand calculations.'),
    (('SQL', 'SQLite', 'PostgreSQL', 'MySQL'), 'Query two fictional sales tables using {skill}, including joins and aggregation.', '8-16', 'Write five queries and validate their row counts and totals.'),
    (('Excel', 'Pivot tables', 'Power Query'), 'Use {skill} to build a refreshable summary from a fictional sales workbook.', '6-12', 'Create three summaries and reconcile each total with the source.'),
    (('Power BI', 'Tableau', 'Dashboards', 'Business intelligence', 'DAX'), 'Build a small reporting dashboard using {skill} for a fictional operations team.', '10-20', 'Show three defined metrics, two filters and five documented validation checks.'),
    (('Statistics', 'Regression', 'A/B testing'), 'Use {skill} to investigate a synthetic dataset and explain uncertainty.', '10-20', 'Submit a reproducible analysis with three checks, assumptions and two limitations.'),
    (('Data visualization', 'Matplotlib', 'Seaborn', 'Plotly'), 'Use {skill} to communicate three findings from a fictional dataset.', '6-12', 'Produce three labeled charts and explain the choice and one limitation of each.'),
    (('Machine learning', 'scikit-learn', 'TensorFlow', 'PyTorch'), 'Build a small baseline prediction experiment using {skill} on synthetic data.', '16-30', 'Separate train/test data, compare against a baseline, and document two failure cases.'),
    (('Data analysis', 'Data cleaning', 'Data validation', 'ETL'), 'Practice {skill} on a fictional dataset with deliberately inserted quality problems.', '8-16', 'Identify five issues, document handling rules and add five repeatable checks.'),
    (('Java', 'JavaScript', 'HTML', 'CSS', 'React', 'Spring', 'REST APIs', 'Software testing', 'Docker'), 'Build a small local task tracker using {skill}; document design choices and test behavior.', '10-20', 'Demonstrate three use cases and five repeatable checks, including invalid input.'),
    (('Database administration',), 'Back up and restore a fictional local database; document recovery steps.', '10-20', 'Restore a backup and verify five record counts or totals.'),
    (('Requirements analysis',), 'Write requirements for a fictional reporting tool and trace them to acceptance checks.', '6-12', 'Document five requirements with measurable acceptance criteria and two unresolved questions.'),
    (('Git',), 'Track a small analysis project with Git and document how to reproduce it.', '4-8', 'Create three meaningful commits, a branch and a reproducible README.'),
    (('Streamlit',), 'Build a local Streamlit explorer for a fictional dataset.', '8-16', 'Add two filters, a chart and validation for an empty dataset.'),
    (('Communication', 'Problem-solving'), 'Use {skill} to explain an analysis problem and a justified solution for a fictional stakeholder.', '4-8', 'Write a one-page brief with a question, three evidence-backed findings and two limitations.'),
):
    for name in names:
        GUIDANCE[name] = (exercise.format(skill=name), hours, goal)


def requirement_levels(job):
    """Conservative explicit headings/clauses; unlabelled mentions stay unspecified."""
    levels = {}
    section = 'Not specified'
    heading = re.compile(r'^(requirements|required skills|required|essential skills|essential|must[- ]have|preferred skills|preferred|nice[- ]to[- ]have|desirable|responsibilities|about the role)\s*(?::|$)')
    for line in normalize(job).splitlines():
        line = line.strip().lstrip('-*• ').strip()
        match = heading.match(line)
        if match:
            label = match.group(1)
            section = ('Preferred' if re.search(r'preferred|nice|desirable', label) else
                       'Essential' if re.search(r'required|requirements|essential|must', label) else 'Not specified')
            line = line[match.end():]
        for clause in re.split(r'[.;]|,\s*', line):
            preferred = bool(re.search(r'\b(preferred|desirable|optional|bonus)\b|nice[- ]to[- ]have', clause))
            essential = bool(re.search(r'\b(required|essential|must)\b', clause))
            level = section
            if re.search(r'\bnot\s+(required|essential)\b', clause) or (essential and preferred):
                level = 'Not specified'
            elif preferred:
                level = 'Preferred'
            elif essential:
                level = 'Essential'
            for skill in extract_skills(clause):
                if skill not in levels or {'Essential': 0, 'Not specified': 1, 'Preferred': 2}[level] < {'Essential': 0, 'Not specified': 1, 'Preferred': 2}[levels[skill]]:
                    levels[skill] = level
    return levels


@dataclass(frozen=True)
class LearningStep:
    skill: str
    importance: str
    reason: str
    prerequisites: tuple[str, ...]
    related: tuple[str, ...]
    exercise: str
    hours: str
    goal: str


@dataclass(frozen=True)
class Roadmap:
    detected: tuple[str, ...]
    steps: tuple[LearningStep, ...]
    weeks: tuple[str, ...]
    message: str | None = None


def build_roadmap(resume: str, job: str, role=None) -> Roadmap:
    if role is not None:
        from .role_skills import resolve_role
        _, job, _ = resolve_role(job, role)
    try:
        result = analyze_job_match(resume, job)
    except ValidationError as exc:
        return Roadmap((), (), (), f'Provide a readable resume and complete job description. {exc}')
    if result.warning:
        return Roadmap(result.resume_skills, (), (), result.warning)
    if not result.missing:
        return Roadmap(result.resume_skills, (), (), 'All recognized job skills were detected in the resume. No gap plan is generated; mentions do not verify proficiency.')
    levels = requirement_levels(job)
    missing = set(result.missing)
    ordered = []
    def visit(skill):
        if skill in ordered:
            return
        for prerequisite in PREREQUISITES.get(skill, ()):
            if prerequisite in missing:
                visit(prerequisite)
        ordered.append(skill)
    for skill in sorted(missing, key=lambda s: ({'Essential': 0, 'Not specified': 1, 'Preferred': 2}[levels.get(s, 'Not specified')], s.casefold())):
        visit(skill)
    steps = []
    for skill in ordered:
        importance = levels.get(skill, 'Not specified')
        reason = (f'The job explicitly marks {skill} as {importance.lower()}.' if importance != 'Not specified'
                  else f'The job mentions {skill}; essential versus preferred importance is not explicit.')
        dependents = [s for s in missing if skill in PREREQUISITES.get(s, ())]
        if dependents:
            reason += ' Suggested foundation for these job-listed gaps: ' + ', '.join(sorted(dependents)) + '.'
        exercise, hours, goal = GUIDANCE[skill]
        steps.append(LearningStep(skill, importance, reason, PREREQUISITES.get(skill, ()),
                                  tuple(present for required, present in result.related if required == skill), exercise, hours, goal))
    # Limit the first month to at most two priorities. Exercises can span multiple weeks.
    first = steps[0]
    second = steps[1] if len(steps) > 1 else first
    weeks = (
        f'Week 1: Review prerequisites for {first.skill}; assess your current knowledge and start its exercise.',
        f'Week 2: Continue {first.skill}. Checkpoint: {first.goal}',
        (f'Week 3: If the first checkpoint is met, start {second.skill}; otherwise continue {first.skill}. Review prerequisites before proceeding.'
         if len(steps) > 1 else f'Week 3: Extend the {first.skill} exercise with a new dataset; revisit any unmet checkpoint.'),
        f'Week 4: Continue the current exercise and document evidence. Next checkpoint: {second.goal} Replan the remaining ordered gaps.',
    )
    return Roadmap(result.resume_skills, tuple(steps), weeks)
