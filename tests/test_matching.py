import math
import pytest

from resume_analyzer.analysis import ValidationError
from resume_analyzer.matching import analyze_match, tfidf_similarity
from resume_analyzer.suggestions import bullet_suggestions
from resume_analyzer.taxonomy import SKILLS, RELATED_PAIRS, extract_skills


def test_taxonomy_integrity():
    assert all(a in SKILLS and b in SKILLS and a != b for a, b in RELATED_PAIRS)
    aliases = [alias for aliases in SKILLS.values() for alias in aliases]
    assert len(aliases) == len(set(aliases))


def test_required_skills_and_aliases():
    result = extract_skills("PYTHON3; structured query language; MS Excel; PowerBI; Tableau; statistical analysis; data visualisation; ML")
    assert set(result) == {"Python", "SQL", "Excel", "Power BI", "Tableau", "Statistics", "Data visualization", "Machine learning"}


def test_duplicate_skills_have_one_vote():
    result = analyze_match("Python python PYTHON3", "Python SQL sql structured query language")
    assert result.resume_skills == ("Python",)
    assert result.job_skills == ("Python", "SQL")
    assert result.coverage == 0.5


def test_token_boundaries():
    assert extract_skills("NoSQL excellent tableauish pythonesque gitlab") == ()


def test_hyphens_whitespace_and_unicode():
    assert extract_skills("Ｐｙｔｈｏｎ Power\nBI machine-learning data‑visualisation") == (
        "Data visualization", "Machine learning", "Power BI", "Python")


def test_full_match_score():
    result = analyze_match("Python SQL", "Python SQL")
    assert result.coverage == 1
    assert result.similarity == pytest.approx(1)
    assert result.score == pytest.approx(100)


def test_missing_and_related_not_equivalent():
    result = analyze_match("Tableau Python", "Power BI Python SQL")
    assert result.matched == ("Python",)
    assert result.missing == ("Power BI", "SQL")
    assert result.related == (("Power BI", "Tableau"),)
    assert result.coverage == pytest.approx(1 / 3)
    assert result.score == pytest.approx(result.skill_points + result.text_points)


def test_related_does_not_imply_parent_skill():
    result = analyze_match("pandas SQLite", "Python SQL")
    assert result.matched == ()
    assert result.coverage == 0
    assert result.related == (("Python", "pandas"), ("SQL", "SQLite"))


def test_no_overlap():
    result = analyze_match("Tableau", "Python")
    assert result.score == 0
    assert result.missing == ("Python",)


def test_no_job_skills_score_unavailable():
    result = analyze_match("Helpful analyst", "Helpful analyst")
    assert result.score is None and result.coverage is None
    assert result.similarity == pytest.approx(1)


def test_no_resume_skills():
    result = analyze_match("Helpful analyst", "SQL")
    assert result.resume_skills == ()
    assert result.missing == ("SQL",)
    assert result.score == 0


@pytest.mark.parametrize("resume,job", [("", "SQL"), ("Python", ""), (" \n", "SQL"),
    ("Python", "!!!"), (None, "SQL"), ("Python", None)])
def test_match_rejects_invalid_inputs(resume, job):
    with pytest.raises(ValidationError):
        analyze_match(resume, job)


def test_oversized_input():
    with pytest.raises(ValidationError, match="100,000"):
        analyze_match("x" * 100_001, "Python")


def test_tfidf_against_hand_calculation():
    # Shared 'python' has IDF=1, SQL appears once and has IDF=1+ln(3/2).
    expected = 1 / math.sqrt(1 + (1 + math.log(1.5)) ** 2)
    assert tfidf_similarity("python sql", "python") == pytest.approx(expected)
    # Sublinear TF discounts repetitions; it does not erase their influence.
    weight = 1 + math.log(2)
    expected_repeated = weight / math.sqrt(weight ** 2 + (1 + math.log(1.5)) ** 2)
    assert tfidf_similarity("python python sql", "python") == pytest.approx(expected_repeated)


@pytest.mark.parametrize("first,second", [("", ""), ("the and a", "and the"), ("!!!", "SQL"), ("a", "b")])
def test_empty_tfidf_vectors(first, second):
    assert tfidf_similarity(first, second) == 0


def test_similarity_symmetry_and_score_bounds():
    for first, second in [("Python sql pandas", "SQL Python"), ("ML", "machine learning"), ("123", "123"), ("café", "CAFÉ")]:
        result = analyze_match(first, second)
        assert 0 <= result.similarity <= 1
        assert result.score is None or 0 <= result.score <= 100
        assert tfidf_similarity(first, second) == pytest.approx(tfidf_similarity(second, first))


def test_negation_is_documented_mention_limitation():
    assert extract_skills("No Python experience") == ("Python",)


def test_skill_extraction_empty():
    assert extract_skills("") == ()


def test_suggestions_preserve_evidence_and_do_not_invent():
    resume = "Alex Example\nWorked on Python reports for a team.\nBuilt SQL queries for 25 sample records."
    suggestions = bullet_suggestions(resume, "Python SQL Tableau")
    assert len(suggestions) == 2
    assert all(item.evidence in resume.splitlines() for item in suggestions)
    assert "verified evidence" in suggestions[0].advice
    assert "Python" in suggestions[0].advice
    assert "Verify" in suggestions[1].advice
    assert all("Tableau" not in item.advice for item in suggestions)


def test_no_bullets_no_invented_suggestions():
    assert bullet_suggestions("Skills: Python, SQL", "Python") == ()


def test_suggestions_are_bounded():
    assert len(bullet_suggestions("\n".join(["Built a SQL reporting project."] * 10), "SQL")) == 5
