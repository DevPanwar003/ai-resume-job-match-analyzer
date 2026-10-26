from pathlib import Path
from io import BytesIO
import math
import pytest
from streamlit.testing.v1 import AppTest
from resume_analyzer.analysis import text_stats
from resume_analyzer.parsing import extract_resume

ROOT = Path(__file__).resolve().parents[1]


def test_homepage_and_validation():
    app = AppTest.from_file(str(ROOT / "app.py")).run()
    assert not app.exception
    assert any("Scores do not predict hiring success" in info.value for info in app.info)
    next(b for b in app.button if b.label == "Extract & inspect").click().run()
    assert "Job description is empty" in app.error[0].value
    app.text_area[0].input("Python analyst role")
    next(b for b in app.button if b.label == "Extract & inspect").click().run()
    assert "Please upload" in app.error[0].value
    assert not app.exception


def test_result_rendering():
    app = AppTest.from_file(str(ROOT / "app.py")).run()
    resume = extract_resume("sample.pdf", (ROOT / "samples/fictional_resume.pdf").read_bytes())
    job = (ROOT / "samples/fictional_job_description.txt").read_text(encoding="utf-8")
    app.session_state["result"] = (resume, text_stats(resume.text), text_stats(job), job)
    app.run()
    assert not app.exception
    assert len(app.metric) == 7
    assert len(app.get("plotly_chart")) == 2
    assert "Alex Example" in app.code[0].value


def test_unknown_job_skills_render_unavailable():
    app = AppTest.from_file(str(ROOT / "app.py")).run()
    resume = extract_resume("sample.pdf", (ROOT / "samples/fictional_resume.pdf").read_bytes())
    job = "Responsibilities: prepare weekly schedules for the team, arrange meeting rooms, maintain office supplies, support visitors and document routine requests carefully each morning."
    app.session_state["result"] = (resume, text_stats(resume.text), text_stats(job), job)
    app.run()
    assert not app.exception
    assert next(metric for metric in app.metric if metric.label == "Match score / 100").value == "N/A"
    assert any("No taxonomy skills" in warning.value for warning in app.warning)


def test_history_navigation_preserves_saved_rows(tmp_path, monkeypatch):
    from resume_analyzer.persistence import HistoryStore
    import resume_analyzer.ui as ui
    store = HistoryStore(tmp_path / "history.sqlite3")
    resume = extract_resume("sample.pdf", (ROOT / "samples/fictional_resume.pdf").read_bytes())
    store.save(resume, text_stats(resume.text), text_stats("SQL"))
    monkeypatch.setattr(ui, "HistoryStore", lambda: store)
    app = AppTest.from_file(str(ROOT / "app.py")).run()
    app.radio[0].set_value("Local history").run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 1
    assert len(store.recent()) == 1


def test_version_two_branding_and_real_demo():
    from resume_analyzer.matching import analyze_match
    from resume_analyzer.taxonomy import extract_skills
    app = AppTest.from_file(str(ROOT / "app.py")).run()
    assert any("PORTFOLIO PROJECT · VERSION 3" == item.value for item in app.caption)
    assert not any("not implemented" in item.value for item in app.caption)
    next(c for c in app.checkbox if c.label == 'Show skill improvement advice').check().run()
    next(b for b in app.button if b.label == "Run fictional demo").click().run()
    assert not app.exception
    job = (ROOT / "samples/fictional_job_description.txt").read_text(encoding="utf-8").strip()
    assert app.text_area[0].value == job
    assert {"SQL", "Python", "Excel", "Power BI", "Statistics", "Data cleaning", "Data visualization"} <= set(extract_skills(job))
    resume = extract_resume("sample.pdf", (ROOT / "samples/fictional_resume.pdf").read_bytes())
    expected = analyze_match(resume.text, job)
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Match score / 100"] == f"{expected.score:.1f}"
    assert metrics["Skill coverage"] == f"{expected.coverage:.1%}"
    assert metrics["TF-IDF cosine similarity"] == f"{expected.similarity:.1%}"
    assert len(app.get("plotly_chart")) == 2
    assert app.code[0].value == resume.text
    assert any("Built a fictional sales dashboard" in item.value for item in app.text)


def test_upload_submission_calculates_and_displays_exact_score(monkeypatch):
    """Exercise form -> real DOCX extraction -> matching -> rendered metrics, not injected results."""
    from docx import Document
    import streamlit as st
    document = Document()
    document.add_paragraph("Python Tableau")
    uploaded = BytesIO()
    document.save(uploaded)
    uploaded.name = "fictional.docx"
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: uploaded)
    app = AppTest.from_file(str(ROOT / "app.py")).run()
    app.text_area[0].input("Requirements: Python Power BI SQL. Responsibilities: prepare reliable weekly reports, inspect source records, document assumptions, explain results, support colleagues carefully accurately.")
    next(b for b in app.button if b.label == "Extract & inspect").click().run()
    assert not app.exception
    # Shared Python IDF=1; the JD has 20 other distinct non-stopwords.
    idf = 1 + math.log(1.5)
    similarity = 1 / (math.sqrt(1 + idf ** 2) * math.sqrt(1 + 20 * idf ** 2))
    expected_score = 70 / 3 + 30 * similarity
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Match score / 100"] == f"{expected_score:.1f}"
    assert metrics["Skill coverage"] == "33.3%"
    assert metrics["TF-IDF cosine similarity"] == f"{similarity:.1%}"
    texts = [item.value for item in app.text]
    assert "Python" in texts
    assert "Power BI\nSQL" in texts
    assert "Tableau → Power BI" in texts
    assert app.code[0].value == "Python Tableau"
    assert any("Score breakdown:" in item.value for item in app.markdown)
    assert len(app.get("plotly_chart")) == 2
