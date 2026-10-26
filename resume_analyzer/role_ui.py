"""Review and explicit persistence controls; all profile extraction stays local."""
import sqlite3
import streamlit as st
from .analysis import ValidationError
from .custom_roles import CustomRoleStore
from .role_skills import AUTO, ROLES, Requirement, resolve_role
from .taxonomy import SKILLS


def advice_control(key):
    # Keep the preference separate from widget keys, which Streamlit removes on navigation.
    def remember():
        st.session_state['advice_enabled'] = st.session_state[key]
    st.checkbox('Show skill improvement advice', value=st.session_state.get('advice_enabled', False),
                key=key, on_change=remember)
    return st.session_state.get('advice_enabled', False)


def role_options():
    try:
        return [AUTO, *ROLES, *CustomRoleStore().load()]
    except (sqlite3.Error, OSError, ValueError):
        st.warning('Saved custom roles could not be read. Check permissions for the custom role store.')
        return [AUTO, *ROLES]


def preview_profile(job, selection, key):
    try:
        name, _, requirements = resolve_role(job, selection)
        if not name:
            st.warning('Provide a complete job description with recognized skills, or select a supported role. No profile inferred.')
            return
        st.markdown(f'**Review role/profile: {name}**')
        st.caption('Local taxonomy extraction, not learned expertise. Labels follow explicit wording; unspecified importance is not inferred. Negation and context can be misread. Review before analysis or saving.')
        for weight, label in ((2, 'Essential'), (1, 'Preferred'), (0, 'Importance unspecified')):
            st.write(label + ': ' + (', '.join(r.skill for r in requirements if r.weight == weight) or 'None specified'))
        title = st.text_input('Custom role name to save', value=name, max_chars=100, key=f'{key}_save_title')
        st.caption('Saving stores this title and skill labels only in data/custom_roles.sqlite3. Avoid personal information in the title. Built-in roles cannot be overwritten.')
        if st.button('Save this role locally', key=f'{key}_save'):
            CustomRoleStore().save(title, requirements)
            st.success('Custom role saved. It is available in the role selector on the next interaction.')
    except (ValidationError, ValueError, sqlite3.Error, OSError) as exc:
        st.error(str(exc))


def manage_roles():
    with st.expander('Edit saved roles'):
        try:
            store = CustomRoleStore()
            roles = store.load()
            if not roles:
                st.caption('No custom roles saved. Preview a description to save its skill profile.')
                return
            title = st.selectbox('Saved custom role', list(roles), key='custom_edit_title')
            requirements = roles[title].requirements
            selected = []
            for weight, label in ((2, 'Essential'), (1, 'Preferred'), (0, 'Importance unspecified')):
                skills = st.multiselect(label, sorted(SKILLS), default=[r.skill for r in requirements if r.weight == weight],
                                        key=f'custom_edit_{title}_{weight}')
                selected.extend(Requirement(skill, 'Custom', weight) for skill in skills)
            if st.button('Save profile edits'):
                store.save(title, selected, replace=True)
                st.success('Profile updated. Existing analysis snapshots are unchanged; submit again to use the edited profile.')
            confirm = st.checkbox('Confirm deletion of this custom role', key=f'custom_delete_{title}')
            if st.button('Delete custom role', disabled=not confirm):
                store.delete(title)
                st.rerun()
        except (ValidationError, ValueError, sqlite3.Error, OSError) as exc:
            st.error(str(exc))
