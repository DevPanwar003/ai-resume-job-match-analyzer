"""Presentation only; roadmap data remains local and is not persisted."""
import streamlit as st
from .roadmap import build_roadmap


def show_roadmap(resume, job):
    st.subheader('Your Skill Improvement Roadmap')
    st.caption('Local, predefined learning suggestions. Not detected does not mean you lack a skill; resume mentions do not verify proficiency. No job-readiness or employment guarantee.')
    roadmap = build_roadmap(resume, job)
    st.write('Skills detected in the resume: ' + (', '.join(roadmap.detected) or 'None detected'))
    if roadmap.message:
        st.info(roadmap.message)
        return
    st.write('Job-listed skills not detected: ' + ', '.join(step.skill for step in roadmap.steps))
    st.caption('Order: explicit essential requirements first, then unspecified, then preferred; a missing job-listed prerequisite is moved ahead of its dependent skill. Importance labels use explicit headings/clauses and should be checked against the original job text. Prerequisites are learning guidance, not inferred job requirements.')
    for priority, step in enumerate(roadmap.steps, 1):
        with st.expander(f'Priority {priority}: {step.skill} | {step.importance}'):
            st.write(step.reason)
            st.write('Suggested prerequisites: ' + (', '.join(step.prerequisites) or 'No specific prerequisite in this guidance.'))
            st.write('Related skills detected that may help: ' + (', '.join(step.related) or 'None detected; no existing ability is assumed.'))
            st.write('Practical exercise: ' + step.exercise)
            st.write(f'Approximate suggested learning time: {step.hours} hours for an introductory exercise, not mastery. Adjust for your starting knowledge and available time.')
            st.write('Measurable completion goal: ' + step.goal)
    st.markdown('**Suggested next 4 weeks**')
    st.caption('A flexible starting plan for the first one or two priorities, not a promise to close every gap in four weeks. Extend any week as needed; proceed only after checking prerequisites and exercise results.')
    for week in roadmap.weeks:
        st.write(week)
