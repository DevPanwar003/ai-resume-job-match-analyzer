"""Streamlit presentation layer."""
from pathlib import Path
import sqlite3
import streamlit as st

from .analysis import ValidationError, text_stats, validate_text
from .parsing import extract_resume
from .persistence import HistoryStore
from .match_ui import show_match
from .comparison_ui import show_comparison
from .role_skills import AUTO, ROLES
from .role_ui import advice_control, role_options, preview_profile, manage_roles
from .matching import analyze_job_match

ROOT = Path(__file__).resolve().parents[1]


def load_data_analyst_example():
    """Form callback: update only the JD after the browser submits all form inputs."""
    st.session_state["job"] = (ROOT / "samples/fictional_job_description.txt").read_text(encoding="utf-8")


def main():
    st.set_page_config(page_title="AI Resume & Job Match Analyzer | V3", page_icon="📄", layout="wide")
    st.markdown("""<style>
        .block-container {max-width:1150px;padding-top:2rem;}
        h1,h2,h3 {color:#14263D;}
        [data-testid="stMetric"] {background:white;border:1px solid #DCE5EE;
          border-top:3px solid #0D9488;border-radius:10px;padding:16px;}
        .hero {background:#14263D;padding:28px 32px;border-radius:16px;margin-bottom:24px;}
        .hero h1 {color:white;font-size:2rem;margin:8px 0;}
        .hero p {color:#D4E4EF;margin:0;}
        .eyebrow {color:#5EEAD4;font-size:12px;font-weight:700;letter-spacing:2px;}
        </style>""", unsafe_allow_html=True)
    with st.sidebar:
        st.markdown("### Resume Lab")
        st.caption("PORTFOLIO PROJECT · VERSION 3")
        page = st.radio("Workspace", ["Analyze", "Compare jobs", "Local history"])
        st.divider()
        st.markdown("**Local by design**")
        st.caption("Documents are processed in memory on this PC. No external résumé services or paid APIs.")
        st.caption("V3: compare up to five jobs and export local reports, using the verified V2 matching engine. No hiring predictions.")
    if page == "Compare jobs":
        show_comparison()
        return
    if page == "Local history":
        show_history()
        return
    st.markdown("""<div class="hero"><span class="eyebrow">LOCAL WORKSPACE / V3</span>
        <h1>AI Resume &amp; Job Match Analyzer</h1>
        <p>Understand skill alignment, inspect the evidence, and refine your résumé with confidence.</p></div>""", unsafe_allow_html=True)
    st.info("Version 3: transparent local matching, multi-job comparison and reports. Scores do not predict hiring success.")
    with st.expander("Try fictional sample documents"):
        st.caption("All names, experience and organizations in these samples are fictional.")
        for name in ("fictional_resume.pdf", "fictional_resume.docx", "fictional_job_description.txt"):
            st.download_button(f"Download {name}", (ROOT / "samples" / name).read_bytes(), file_name=name)
        if st.button("Use fictional job description"):
            st.session_state["job"] = (ROOT / "samples/fictional_job_description.txt").read_text(encoding="utf-8")
        if st.button("Run fictional demo"):
            demo_job = validate_text((ROOT / "samples/fictional_job_description.txt").read_text(encoding="utf-8"), "Job description")
            demo_resume = extract_resume("fictional_resume.pdf", (ROOT / "samples/fictional_resume.pdf").read_bytes())
            st.session_state.pop("result_match", None)
            st.session_state["result_role"] = AUTO
            st.session_state["job"] = demo_job
            st.session_state["result"] = (demo_resume, text_stats(demo_resume.text), text_stats(demo_job), demo_job)
            st.info("Showing fictional sample results. The demo does not save history. Upload your résumé and submit to replace these results.")
    st.caption("Load the fictional full job description without changing your uploaded résumé. Submit again to update results.")
    with st.form("inputs"):
        left, right = st.columns([1, 1.25], gap="large")
        with left:
            st.subheader("01 / Your résumé")
            uploaded = st.file_uploader("Upload a résumé", type=["pdf", "docx"],
                                        key=f"upload_{st.session_state.get('generation', 0)}")
            st.caption("PDF or DOCX · up to 5 MB · PDF up to 50 pages. Text-based documents only.")
        with right:
            st.subheader("02 / The opportunity")
            role = st.selectbox("Job role", role_options(), key="role_selection")
            role_title = st.text_input("Job title (optional)", max_chars=100, key="custom_job_title")
            job = st.text_area("Job description", key="job", height=220, max_chars=100_000,
                               placeholder="Paste the role, responsibilities and requirements here…")
        save = st.checkbox("Save numeric statistics to local history", value=False,
                           help="Source text and filenames are never stored in history.")
        preview = st.form_submit_button("Preview role skills")
        submitted = st.form_submit_button("Extract & inspect", type="primary")
        st.form_submit_button("Load Data Analyst example", on_click=load_data_analyst_example)
    show_advice = advice_control('analyze_advice_widget')
    if preview:
        st.session_state['profile_preview'] = ((role_title + '\n' if role_title.strip() else '') + job, role)
    if 'profile_preview' in st.session_state:
        preview_profile(*st.session_state['profile_preview'], key='single_preview')
    manage_roles()
    if submitted:
        st.session_state.pop("result", None)
        try:
            validated_job = validate_text(job or (role if role != AUTO else role_title), "Job description")
            if role_title.strip() and job.strip():
                validated_job = role_title.strip() + "\n" + validated_job
            if uploaded is None:
                raise ValidationError("Please upload a PDF or DOCX résumé before continuing.")
            with st.spinner("Reading your document locally…"):
                resume = extract_resume(uploaded.name, uploaded.getvalue())
                stats, job_stats = text_stats(resume.text), text_stats(validated_job)
            st.session_state["result_match"] = analyze_job_match(resume.text, validated_job, role=role)
            st.session_state["result_role"] = role
            st.session_state["result"] = (resume, stats, job_stats, validated_job)
            if save:
                try:
                    HistoryStore().save(resume, stats, job_stats)
                    st.success("Numeric summary saved locally. Résumé and job-description text were not saved.")
                except (sqlite3.Error, OSError):
                    st.warning("Analysis succeeded, but history could not be saved. Check permissions for the data folder.")
        except ValidationError as exc:
            st.error(str(exc))
            if not job.strip():
                st.warning("Please provide a complete job description with responsibilities and required skills, not just a job title.")
    if "result" in st.session_state:
        resume, stats, job_stats, validated_job = st.session_state["result"]
        st.divider()
        st.subheader("Analysis overview")
        st.caption("Results reflect the last successful submission. Submit again after changing inputs.")
        for column, label, value in zip(st.columns(4),
                                       ["Résumé words", "Job description words", "Document type", "File size"],
                                       [stats.words, job_stats.words, resume.file_type, f"{resume.size_bytes / 1024:.1f} KB"]):
            column.metric(label, value)
        match, detail, extracted = st.tabs(["Job match", "Document statistics", "Extracted text"])
        with match:
            show_match(resume.text, validated_job, role=st.session_state.get("result_role", AUTO), show_advice=show_advice, result=st.session_state.get("result_match"))
        with detail:
            st.table([dict(Document="Résumé", **stats.to_dict()),
                      dict(Document="Job description", **job_stats.to_dict())])
            st.caption(f"PDF pages: {resume.pages}" if resume.pages is not None else "DOCX page count is unavailable without a layout engine.")
            st.caption("Characters include spaces; lines count nonempty extracted lines. Unique words ignore case. These are descriptive counts, not suitability judgments.")
        with extracted:
            st.markdown("**Résumé text**")
            st.code(resume.text, language=None, wrap_lines=True)
            st.markdown("**Submitted job description**")
            st.code(validated_job, language=None, wrap_lines=True)
            st.caption("Reading order may differ in multi-column PDFs. DOCX extraction includes body paragraphs and tables; headers, footers and text boxes are not included.")
        if st.button("Clear session inputs and results"):
            generation = st.session_state.get("generation", 0) + 1
            for key in list(st.session_state):
                del st.session_state[key]
            st.session_state["generation"] = generation
            st.rerun()


def show_history():
    st.title("Local history")
    st.caption("Latest 100 saved summaries · timestamps in UTC · no names, filenames or source text")
    try:
        store = HistoryStore()
        rows = store.recent()
        if rows:
            st.dataframe(rows, hide_index=True, use_container_width=True)
            confirm = st.checkbox("I want to delete all saved summaries")
            if st.button("Delete history", disabled=not confirm):
                store.clear()
                st.rerun()
        else:
            st.info("No saved analyses yet. Enable the save option when analyzing a document.")
    except (sqlite3.Error, OSError):
        st.error("Local history is unavailable. Check that the project data folder is writable.")
