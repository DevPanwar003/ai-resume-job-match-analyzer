"""One resume, up to five jobs, using the existing V2 matcher and detail view."""
import json
from pathlib import Path
import plotly.graph_objects as go
import streamlit as st
from .analysis import ValidationError
from .role_skills import AUTO, ROLES
from .role_ui import advice_control, role_options, preview_profile
from .comparison import compare_document, comparison_rows
from .match_ui import show_match
from .reports import WARNING, html_report, pdf_report

ROOT = Path(__file__).resolve().parents[1]


def load_data_analyst_example(index):
    """Form callback preserves uploaded bytes and other submitted job fields."""
    st.session_state[f'compare_description_{index}'] = (ROOT / 'samples/fictional_job_description.txt').read_text(encoding='utf-8')


def show_comparison():
    st.title('Compare job opportunities')
    st.warning(WARNING)
    st.caption('One resume, up to five jobs. Same V2 scoring engine. Results remain in session memory; comparison does not write to history.')
    if st.button('Run three-job fictional demo'):
        jobs = json.loads((ROOT / 'samples/fictional_jobs.json').read_text(encoding='utf-8'))
        st.session_state['comparison'] = compare_document('fictional_resume.pdf',
            (ROOT / 'samples/fictional_resume.pdf').read_bytes(), [(job['title'], job['description']) for job in jobs])
        st.session_state.pop('comparison_reports', None)
    count = st.selectbox('Number of jobs', [1, 2, 3, 4, 5], index=1, key='comparison_count')
    sample_target = st.selectbox('Load Data Analyst example into', range(count), format_func=lambda i: f'Job {i + 1}')
    st.caption('Sample loading changes only the selected description; your uploaded resume is retained. Submit to update results.')
    with st.form('comparison_inputs'):
        uploaded = st.file_uploader('Resume for comparison', type=['pdf', 'docx'],
                                    key=f"comparison_upload_{st.session_state.get('comparison_generation', 0)}")
        jobs = []
        roles = []
        for index in range(count):
            st.markdown(f'**Job {index + 1}**')
            title = st.text_input(f'Job {index + 1} title', value=f'Job {index + 1}', max_chars=100, key=f'compare_title_{index}')
            roles.append(st.selectbox(f'Job {index + 1} role', role_options(), key=f'compare_role_{index}'))
            description = st.text_area(f'Job {index + 1} description', max_chars=100_000, key=f'compare_description_{index}')
            jobs.append((title, description))
        preview = st.form_submit_button('Preview role skills')
        submitted = st.form_submit_button('Compare jobs', type='primary')
        st.form_submit_button('Load Data Analyst example', on_click=load_data_analyst_example, args=(sample_target,))
    show_advice = advice_control('compare_advice_widget')
    if preview:
        st.session_state['comparison_preview'] = [(title + '\n' + description, role) for (title, description), role in zip(jobs, roles)]
    for index, (job, role) in enumerate(st.session_state.get('comparison_preview', [])):
        preview_profile(job, role, key=f'compare_preview_{index}')
    if submitted:
        st.session_state.pop('comparison', None)
        st.session_state.pop('comparison_reports', None)
        try:
            if uploaded is None:
                raise ValidationError('Please upload a PDF or DOCX resume for comparison.')
            st.session_state['comparison'] = compare_document(uploaded.name, uploaded.getvalue(), jobs, roles=roles)
        except ValidationError as exc:
            st.error(str(exc))
            if any(not description.strip() for _, description in jobs):
                st.warning('Please provide a complete job description with responsibilities and required skills for each selected job, not just job titles.')
    if 'comparison' not in st.session_state:
        return
    resume, results = st.session_state['comparison']
    st.subheader('Ranked comparison')
    st.caption('Last successful submission or fictional demo. Submit again after editing. Exact ties retain input order. N/A jobs are unranked and shown last. These pair-specific scores are exploratory, not standardized assessments.')
    st.dataframe(comparison_rows(results), hide_index=True, use_container_width=True)
    for item in results:
        if item.match.warning:
            st.warning(f'Job {item.index}: {item.match.warning}')
    st.caption('Similarity compares wording only; it is not skill coverage. Unassessed jobs have no score contributions or recommendations.')
    labels = [f'Job {item.index}' for item in results]
    figure = go.Figure()
    figure.add_bar(name='Match score / 100', x=labels, y=[item.match.score for item in results], marker_color='#0d9488')
    figure.add_bar(name='Skill coverage %', x=labels, y=[None if item.match.coverage is None else item.match.coverage * 100 for item in results], marker_color='#14263d')
    figure.add_bar(name='Similarity %', x=labels, y=[item.match.similarity * 100 for item in results], marker_color='#94a3b8')
    figure.update_layout(title='Job alignment comparison', barmode='group', yaxis_range=[0, 100], height=360)
    st.plotly_chart(figure, use_container_width=True)
    breakdown = go.Figure()
    breakdown.add_bar(name='Skill points (max 70)', x=labels, y=[item.match.skill_points for item in results], marker_color='#0d9488')
    breakdown.add_bar(name='Text points (max 30)', x=labels, y=[None if item.match.warning else item.match.text_points for item in results], marker_color='#14263d')
    breakdown.update_layout(title='Score contributions (N/A totals remain unranked)', barmode='stack', yaxis_range=[0, 100], height=320)
    st.plotly_chart(breakdown, use_container_width=True)
    st.subheader('Download comparison reports')
    include_evidence = st.checkbox('Include resume quotations in reports', value=False)
    st.caption('Reports include job titles, skills and recommendations. Quotations may contain personal information. Review before sharing. PDF uses Western fonts; use HTML for full Unicode.')
    if st.button('Generate local reports'):
        with st.spinner('Generating reports locally...'):
            st.session_state['comparison_reports'] = (include_evidence, html_report(results, include_evidence), pdf_report(results, include_evidence))
    reports = st.session_state.get('comparison_reports')
    if reports is not None and reports[0] == include_evidence:
        st.download_button('Download HTML report', reports[1], file_name='resume-job-comparison.html', mime='text/html')
        st.download_button('Download PDF report', reports[2], file_name='resume-job-comparison.pdf', mime='application/pdf')
    selected = st.selectbox('Inspect a job', range(len(results)), format_func=lambda i: f'{results[i].index}. {results[i].title}')
    item = results[selected]
    show_match(resume.text, item.description, show_advice=show_advice, result=item.match)
    with st.expander('Inspect source text for this comparison'):
        st.code(resume.text, language=None, wrap_lines=True)
        st.code(item.description, language=None, wrap_lines=True)
    if st.button('Clear comparison inputs and reports'):
        generation = st.session_state.get('comparison_generation', 0) + 1
        for key in list(st.session_state):
            if key.startswith(('comparison', 'compare_')):
                del st.session_state[key]
        st.session_state['comparison_generation'] = generation
        st.rerun()
