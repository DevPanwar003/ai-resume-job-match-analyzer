"""Batch orchestration only: the V2 engine remains the sole scoring implementation."""
from dataclasses import dataclass, replace
from .analysis import ValidationError, validate_text
from .role_skills import AUTO, detect_role
from .matching import MatchResult, analyze_job_match
from .parsing import ParsedResume, extract_resume
from .suggestions import Suggestion, bullet_suggestions


@dataclass(frozen=True)
class JobMatch:
    index: int
    title: str
    description: str
    match: MatchResult
    suggestions: tuple[Suggestion, ...]


def compare_jobs(resume: str, jobs: list[tuple[str, str]], roles=None) -> tuple[JobMatch, ...]:
    resume = validate_text(resume, "Résumé text")
    if not 1 <= len(jobs) <= 5:
        raise ValidationError("Provide between one and five job descriptions.")
    if roles is not None and len(roles) != len(jobs):
        raise ValidationError("Provide one role selection per job.")
    results = []
    for index, (title, description) in enumerate(jobs, 1):
        title = validate_text(title, f"Job {index} title")
        if len(title) > 100:
            raise ValidationError(f"Job {index} title exceeds 100 characters.")
        selection = roles[index - 1] if roles is not None else None
        if selection is not None:
            if selection == AUTO:
                from .custom_roles import CustomRoleStore
                from .taxonomy import normalize
                custom = CustomRoleStore().load()
                selected_custom = next((name for name in custom if normalize(name) == normalize(title)), None)
                selection = detect_role(title) or selected_custom or AUTO
        if selection is not None and not description.strip():
            if selection != AUTO or detect_role(title):
                description = title if selection == AUTO else selection
        description = validate_text(description, f"Job {index} description")
        match = analyze_job_match(resume, description, role=selection)
        if selection == AUTO and match.role == 'Description-derived profile':
            match = replace(match, role=title)
        results.append(JobMatch(index, title, description, match,
                                () if match.warning else bullet_suggestions(resume, match.effective_job or description)))
    # Stable sorting: input order breaks exact ties; N/A is below every numeric score.
    return tuple(sorted(results, key=lambda item: (
        item.match.score is None, -(item.match.score or 0), item.index)))


def compare_document(filename: str, content: bytes, jobs: list[tuple[str, str]], roles=None) -> tuple[ParsedResume, tuple[JobMatch, ...]]:
    resume = extract_resume(filename, content)
    return resume, compare_jobs(resume.text, jobs, roles=roles)


def comparison_rows(results: tuple[JobMatch, ...]) -> list[dict]:
    return [{"Rank": str(rank) if item.match.score is not None else "N/A",
             "Job": f"{item.index}. {item.title}",
             "Match score / 100": None if item.match.score is None else round(item.match.score, 2),
             "Skill coverage %": None if item.match.coverage is None else round(100 * item.match.coverage, 2),
             "Similarity %": round(100 * item.match.similarity, 2),
             "Status": item.match.warning or "Assessed",
             "Matched skills": "Not assessed" if item.match.warning else (", ".join(item.match.matched) or "None detected"),
             "Missing skills": "Not assessed" if item.match.warning else (", ".join(item.match.missing) or "None detected")}
            for rank, item in enumerate(results, 1)]
