"""Local Plotly charts and transparent matching presentation."""
import plotly.graph_objects as go
import streamlit as st

from .matching import analyze_job_match
from .suggestions import bullet_suggestions
from .roadmap_ui import show_roadmap


def show_match(resume: str, job: str, role=None, show_advice=True, result=None):
    result = result if result is not None else analyze_job_match(resume, job, role=role)
    if result.role:
        st.markdown(f"**Selected role: {result.role}**")
        st.caption("Local profile guidance; a full description replaces generic requirements. Unknown roles use a temporary description-derived profile. Catalog weights (essential 2, preferred 1) guide roadmap order only. Coverage remains unweighted. TF-IDF uses the effective profile text for title-only inputs.")
        for weight, label in ((2, "Essential"), (1, "Preferred"), (0, "Importance unspecified")):
            st.write(label + ": " + (", ".join(r.skill for r in result.requirements if r.weight == weight) or "None specified"))
        job = result.effective_job
        with st.expander("Effective job input used for scoring"):
            st.text(job)
    st.subheader("Job match analysis")
    st.caption("A text-alignment heuristic, not a prediction of hiring success or proof of proficiency.")
    cols = st.columns(3)
    cols[0].metric("Match score / 100", "N/A" if result.score is None else f"{result.score:.1f}")
    cols[1].metric("Skill coverage", "N/A" if result.coverage is None else f"{result.coverage:.1%}")
    cols[2].metric("TF-IDF cosine similarity", f"{result.similarity:.1%}")
    st.caption("TF-IDF measures shared wording only. It is separate from skill coverage and cannot establish suitability, especially for short inputs.")
    if result.warning:
        st.warning(result.warning)
        if show_advice:
            st.info("Skill gaps and evidence-based bullet suggestions are withheld until sufficient recognized evidence is available. Load the Data Analyst example or paste the full job description, then submit again.")
        if show_advice:
            show_roadmap(resume, job)
        return
    if result.score is not None:
        st.write(f"Score breakdown: {result.skill_points:.2f} skill-coverage points + "
                 f"{result.text_points:.2f} text-similarity points = {result.score:.2f} / 100.")
        st.caption("70% skill coverage + 30% TF-IDF cosine similarity; related skills add no coverage credit.")
    if result.coverage is None:
        st.warning("No taxonomy skills were recognized in the job description. Coverage and overall score are unavailable; text similarity is shown separately.")
    left, right = st.columns(2)
    with left:
        figure = go.Figure(go.Bar(x=["Matched", "Missing"], y=[len(result.matched), len(result.missing)],
                                 marker_color=["#0D9488", "#64748B"]))
        figure.update_layout(title="Job skill coverage", yaxis_title="Unique skills", yaxis=dict(dtick=1), height=300)
        st.plotly_chart(figure, use_container_width=True)
    with right:
        figure = go.Figure(go.Bar(x=["Skill coverage (max 70)", "Text similarity (max 30)"],
                                 y=[result.skill_points, result.text_points], marker_color=["#0D9488", "#14263D"]))
        figure.update_layout(title="Weighted score contributions", yaxis_title="Points", yaxis_range=[0, 70], height=300)
        st.plotly_chart(figure, use_container_width=True)
    for column, title, skills in zip(st.columns(3), ["Matched skills", "Missing skills", "Related skills"],
                                    [result.matched, result.missing,
                                     tuple(f"{present} → {required}" for required, present in result.related)]):
        with column:
            st.markdown(f"**{title}**")
            st.text("\n".join(skills) if skills else "None detected")
    st.caption("Missing means not mentioned, not unqualified. Related shows résumé skill → missing job skill; related skills earn no coverage credit and remain missing.")
    with st.expander("All extracted skills and score calculation"):
        st.text("Résumé: " + (", ".join(result.resume_skills) or "None detected"))
        st.text("Job description: " + (", ".join(result.job_skills) or "None detected"))
        st.write(f"Coverage = {len(result.matched)} matched / {len(result.job_skills)} unique job skills.")
        st.write("Score = 70 × coverage + 30 × TF-IDF cosine similarity. Display values are rounded; calculation uses full precision.")
        st.write("TF-IDF uses these two documents, lowercase word tokens, an explicit English stopword list, sublinear term frequency (1 + ln count), smoothed IDF (1 + ln(3 / (1 + document frequency))) and L2 cosine normalization.")
        st.warning("Mention matching cannot verify proficiency, negation, years of experience or required versus optional skills. For example, 'no Python experience' still contains a Python mention. Ambiguous terms (such as Excel or ML) can be false positives. The taxonomy is incomplete and English-oriented. Repetition and wording can affect text similarity. Weights are design choices, not a validated hiring model.")
    if not show_advice:
        return
    st.subheader("Evidence-based bullet suggestions")
    st.caption("Editing prompts grounded in your existing lines, not verified achievements or completed rewrites. Add only facts you can substantiate; do not add missing skills unless you actually have them.")
    suggestions = bullet_suggestions(resume, job)
    for suggestion in suggestions:
        with st.container(border=True):
            st.text(suggestion.evidence)
            st.write(suggestion.advice)
    if not suggestions:
        st.info("No suitable action-led or bullet lines were detected. Describe an actual task, your own action, and a verifiable result; no experience has been inferred.")
    show_roadmap(resume, job)
