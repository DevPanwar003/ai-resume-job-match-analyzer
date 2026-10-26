"""Deterministic local skill coverage and two-document TF-IDF cosine similarity."""
from collections import Counter
from dataclasses import dataclass, replace
import math
import re

from .analysis import validate_text
from .taxonomy import are_related, extract_skills, normalize

SKILL_WEIGHT = 0.70
TEXT_WEIGHT = 0.30
# Deliberately small and explicit English stopword list; no downloads.
STOPWORDS = frozenset("a an and are as at be by for from in is it of on or that the this to was were with you your we our".split())


def tfidf_similarity(first: str, second: str) -> float:
    """Smoothed IDF, sublinear TF, L2 cosine. Empty vectors have similarity zero."""
    counts = [Counter(token for token in re.findall(r"\b\w+\b", normalize(text))
                      if len(token) > 1 and token not in STOPWORDS) for text in (first, second)]
    vocabulary = sorted(set(counts[0]) | set(counts[1]))
    idf = {term: 1 + math.log(3 / (1 + sum(term in count for count in counts))) for term in vocabulary}
    vectors = [{term: (1 + math.log(count[term])) * idf[term] for term in count} for count in counts]
    norms = [math.sqrt(sum(value * value for value in vector.values())) for vector in vectors]
    if not all(norms):
        return 0.0
    dot = sum(vectors[0].get(term, 0) * vectors[1].get(term, 0) for term in vocabulary)
    return min(1.0, max(0.0, dot / (norms[0] * norms[1])))


@dataclass(frozen=True)
class MatchResult:
    resume_skills: tuple[str, ...]
    job_skills: tuple[str, ...]
    matched: tuple[str, ...]
    missing: tuple[str, ...]
    related: tuple[tuple[str, str], ...]  # (missing JD skill, related résumé skill)
    coverage: float | None
    similarity: float
    score: float | None
    warning: str | None = None
    role: str | None = None
    effective_job: str | None = None
    requirements: tuple = ()

    @property
    def skill_points(self) -> float | None:
        return None if self.coverage is None else 100 * SKILL_WEIGHT * self.coverage

    @property
    def text_points(self) -> float:
        return 100 * TEXT_WEIGHT * self.similarity


def analyze_match(resume: str, job: str) -> MatchResult:
    """Low-level mention/formula calculation. UI callers use analyze_job_match.

    Kept independently testable with tiny keyword examples; not a JD adequacy check.
    """
    resume, job = validate_text(resume, "Résumé text"), validate_text(job, "Job description")
    resume_skills, job_skills = extract_skills(resume), extract_skills(job)
    matched = tuple(skill for skill in job_skills if skill in resume_skills)
    missing = tuple(skill for skill in job_skills if skill not in resume_skills)
    related = tuple((required, present) for required in missing for present in resume_skills
                    if are_related(required, present))
    coverage = len(matched) / len(job_skills) if job_skills else None
    similarity = tfidf_similarity(resume, job)
    score = None if coverage is None else 100 * (SKILL_WEIGHT * coverage + TEXT_WEIGHT * similarity)
    return MatchResult(resume_skills, job_skills, matched, missing, related, coverage, similarity, score)


MIN_JOB_WORDS = 20
MIN_DISTINCT_JOB_WORDS = 10
JOB_CONTEXT = re.compile(
    r"\b(responsibilities|requirements|required|require|experience|knowledge|skills|"
    r"build|develop|maintain|analyze|analyse|analyzing|analysing|prepare|create|"
    r"write|use|apply|perform|support|manage|design|deliver|evaluate|clean|"
    r"document|validate|present|monitor|work|ability|familiarity)\b")


def job_description_warning(job: str) -> str | None:
    """Conservative, documented English input heuristic, not a semantic JD classifier."""
    normalized = normalize(job)
    words = re.findall(r"\b\w+\b", normalized)
    if (len(words) < MIN_JOB_WORDS or len(set(words)) < MIN_DISTINCT_JOB_WORDS
            or not JOB_CONTEXT.search(normalized)):
        return ("Insufficient job-description evidence: a complete job description is needed, not just a title or a list of roles/keywords. "
                "Include responsibilities and required skills (at least 20 words with 10 distinct words and task or requirement context). "
                "Match Score and Skill Coverage are N/A; skill gaps and recommendations are not assessed.")
    if not extract_skills(job):
        return ("No taxonomy skills were recognized in this job description. Paste explicit required skills if available; "
                "the taxonomy may not cover this role. Match Score and Skill Coverage are N/A; no skill gaps or recommendations are inferred.")
    return None


def analyze_job_match(resume: str, job: str, role=None) -> MatchResult:
    """Shared user-facing validation gate around the unchanged 70/30 calculation."""
    selected, requirements = None, ()
    if role is not None:
        from .role_skills import resolve_role
        selected, job, requirements = resolve_role(job, role)
    result = analyze_match(resume, job)
    if selected:
        result = replace(result, role=selected, effective_job=job, requirements=requirements)
    warning = job_description_warning(job)
    if warning is None and not result.resume_skills:
        warning = ("No taxonomy skills were recognized in the resume. Check the extracted text and taxonomy coverage. "
                   "Match Score and Skill Coverage are N/A rather than treating unrecognized evidence as a zero match.")
    if warning and role is not None and not selected:
        warning += " Select a supported role or enter a complete job description."
    if warning:
        return replace(result, matched=(), missing=(), related=(), coverage=None, score=None, warning=warning)
    return result
