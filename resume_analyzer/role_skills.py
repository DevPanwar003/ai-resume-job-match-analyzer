"""Local illustrative role profiles, not employer requirements or market statistics."""
from dataclasses import dataclass
import re
from .taxonomy import normalize, alias_pattern, extract_skills

AUTO = 'Auto-detect from title'


@dataclass(frozen=True)
class Requirement:
    skill: str
    category: str
    weight: int  # 2 essential, 1 preferred; guidance priority, never score credit.


@dataclass(frozen=True)
class Role:
    aliases: tuple[str, ...]
    requirements: tuple[Requirement, ...]


CATEGORIES = {
    'Programming': ('Python', 'Java', 'JavaScript', 'HTML', 'CSS'),
    'Engineering': ('Git', 'Software testing', 'REST APIs', 'React', 'Spring', 'Docker'),
    'Databases': ('SQL', 'PostgreSQL', 'Database administration'),
    'Analytics': ('Excel', 'Power BI', 'Tableau', 'Statistics', 'Data analysis', 'Data visualization', 'Data cleaning', 'ETL'),
    'Modeling': ('Machine learning', 'pandas', 'NumPy', 'scikit-learn'),
    'Collaboration': ('Communication', 'Problem-solving', 'Requirements analysis'),
}


def profile(aliases, essential, preferred):
    return Role(tuple(aliases), tuple(Requirement(skill, next(category for category, skills in CATEGORIES.items() if skill in skills), weight)
                                     for weight, skills in ((2, essential), (1, preferred)) for skill in skills))


ROLES = {
    'Data Analyst': profile(('data analyst', 'data analytics analyst'), ('SQL', 'Excel', 'Data analysis', 'Data cleaning', 'Data visualization'), ('Python', 'Power BI', 'Statistics')),
    'Business Analyst': profile(('business analyst', 'business analysis analyst'), ('Requirements analysis', 'Excel', 'Communication', 'Data analysis'), ('SQL', 'Power BI', 'Statistics')),
    'Data Scientist': profile(('data scientist',), ('Python', 'Statistics', 'Machine learning', 'SQL', 'pandas'), ('NumPy', 'scikit-learn', 'Data visualization')),
    'Software Engineer': profile(('software engineer', 'software developer', 'swe'), ('Git', 'Software testing', 'Problem-solving', 'REST APIs'), ('Python', 'Java', 'SQL')),
    'Python Developer': profile(('python developer', 'python engineer'), ('Python', 'Git', 'Software testing', 'REST APIs'), ('SQL', 'Docker')),
    'Java Developer': profile(('java developer', 'java engineer'), ('Java', 'Git', 'Software testing', 'Spring'), ('SQL', 'REST APIs', 'Docker')),
    'Web Developer': profile(('web developer', 'web engineer'), ('HTML', 'CSS', 'JavaScript', 'Git'), ('REST APIs', 'React', 'Software testing')),
    'Frontend Developer': profile(('frontend developer', 'front end developer', 'frontend engineer'), ('HTML', 'CSS', 'JavaScript', 'React'), ('Git', 'Software testing', 'REST APIs')),
    'Backend Developer': profile(('backend developer', 'back end developer', 'backend engineer'), ('REST APIs', 'SQL', 'Software testing', 'Git'), ('Python', 'Java', 'Docker')),
    'Full Stack Developer': profile(('full stack developer', 'fullstack developer', 'full stack engineer'), ('HTML', 'CSS', 'JavaScript', 'REST APIs', 'SQL', 'Git'), ('React', 'Python', 'Docker')),
    'Machine Learning Engineer': profile(('machine learning engineer', 'ml engineer'), ('Python', 'Machine learning', 'scikit-learn', 'Software testing'), ('Docker', 'SQL', 'Statistics')),
    'Database Administrator': profile(('database administrator', 'dba'), ('SQL', 'Database administration', 'PostgreSQL'), ('Python', 'ETL', 'Problem-solving')),
}


def detect_role(text):
    """Match a whole title line only, never infer a role from a skill or a list of roles."""
    line = normalize(text).strip().splitlines()[0] if text.strip() else ''
    line = re.sub(r'^(?:job title|role|title)\s*:\s*', '', line)
    line = re.sub(r'^(?:junior|senior|entry level)\s+', '', line)
    line = re.sub(r'\s+(?:job|role|position)$', '', line.rstrip('.! '))
    return next((name for name, role in ROLES.items() if any(alias_pattern(alias).fullmatch(line) for alias in role.aliases)), None)


def resolve_role(job, selection=AUTO):
    """Explicit full descriptions refine by replacing generic requirements with their mentions."""
    from .matching import job_description_warning
    from .roadmap import requirement_levels
    from .custom_roles import CustomRoleStore
    custom = CustomRoleStore().load()
    catalog = {**custom, **ROLES}
    if selection != AUTO and selection not in catalog:
        raise ValueError('Unsupported role selection')
    name = detect_role(job) if selection == AUTO else selection
    if name is None and job.strip():
        first = ' '.join(normalize(job.strip().splitlines()[0]).split())
        name = next((title for title in custom if ' '.join(normalize(title).split()) == first), None)
    requirements = catalog[name].requirements if name else ()
    if job_description_warning(job) is None:
        # Employer text takes precedence; do not add generic skills absent from a full JD.
        levels = requirement_levels(job)
        requirements = tuple(Requirement(skill, next((c for c, skills in CATEGORIES.items() if skill in skills), 'Other'),
                                         2 if levels.get(skill) == 'Essential' else 1 if levels.get(skill) == 'Preferred' else 0)
                             for skill in extract_skills(job))
        if name is None:
            first = job.strip().splitlines()[0]
            name = first if len(first) <= 100 and len(first.split()) <= 10 and len(job.splitlines()) > 1 else 'Description-derived profile'
        return name, job, requirements
    if name is None:
        return None, job, ()
    essential = ', '.join(r.skill for r in requirements if r.weight == 2)
    preferred = ', '.join(r.skill for r in requirements if r.weight == 1)
    unspecified = ', '.join(r.skill for r in requirements if r.weight == 0)
    effective = ('Responsibilities: apply the listed skills to complete practical tasks, validate results, document decisions and explain your work clearly to the team.\n'
                 f'Essential skills: {essential}.\nPreferred skills: {preferred}.\nResponsibilities: {unspecified}.')
    return name, effective, requirements
