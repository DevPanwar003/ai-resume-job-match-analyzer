"""Evidence-linked editing prompts, never fabricated résumé claims."""
from dataclasses import dataclass
import re

from .taxonomy import extract_skills


@dataclass(frozen=True)
class Suggestion:
    evidence: str
    advice: str


def bullet_suggestions(resume: str, job: str) -> tuple[Suggestion, ...]:
    job_skills = set(extract_skills(job))
    suggestions = []
    for line in resume.splitlines():
        line = line.strip()
        body = re.sub(r"^(?:[-*•]|\d+[.)])\s*", "", line)
        # Only bullet-like or action-led lines, not contact details/skill lists.
        if len(body.split()) < 4 or not (
            line != body or re.match(r"(?i)^(built|developed|created|wrote|analyzed|analysed|managed|worked|helped|supported|led|automated|improved|collaborated|responsible)\b", body)
        ):
            continue
        advice = []
        relevant = sorted(job_skills & set(extract_skills(body)))
        if relevant:
            advice.append("This line mentions job-listed skills: " + ", ".join(relevant) + ". Explain how you used them in this specific task.")
        if re.match(r"(?i)^(worked|helped|responsible|supported)\b", body):
            advice.append("Clarify your own action and contribution; use an action verb only if it accurately describes your role.")
        if not re.search(r"\d", body):
            advice.append("If you have verified evidence, add scope or an outcome (such as records checked or time saved). Otherwise describe the observable result without inventing a number.")
        else:
            advice.append("Verify that any numbers describe an actual outcome or scope, and explain how they were measured.")
        suggestions.append(Suggestion(line, " ".join(advice)))
        if len(suggestions) == 5:
            break
    return tuple(suggestions)
