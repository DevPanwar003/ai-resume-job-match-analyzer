"""Opt-in local profiles only: no resume text or job-description bodies are saved."""
from contextlib import closing
from pathlib import Path
import json
import sqlite3
from .analysis import ValidationError, validate_text
from .taxonomy import SKILLS, normalize

DEFAULT_DB = Path(__file__).resolve().parents[1] / 'data' / 'custom_roles.sqlite3'


class CustomRoleStore:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else DEFAULT_DB

    def load(self):
        from .role_skills import Role, Requirement
        if not self.path.exists():
            return {}
        with closing(sqlite3.connect(f'{self.path.as_uri()}?mode=ro', uri=True)) as db:
            return {title: Role((normalize(title),), tuple(Requirement(**r) for r in json.loads(payload)))
                    for title, payload in db.execute('SELECT title, requirements FROM custom_roles ORDER BY title')}

    def save(self, title, requirements, *, replace=False):
        from .role_skills import detect_role
        title = validate_text(title, 'Role title').strip()
        if len(title) > 100 or '\n' in title or detect_role(title):
            raise ValidationError('Use a custom title of at most 100 characters that does not replace a built-in role or alias.')
        requirements = tuple(requirements)
        if (not requirements or len({r.skill for r in requirements}) != len(requirements)
                or any(r.skill not in SKILLS or r.weight not in (0, 1, 2) for r in requirements)):
            raise ValidationError('Choose unique recognized skills and valid importance levels.')
        payload = json.dumps([dict(skill=r.skill, category=r.category, weight=r.weight) for r in requirements])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS custom_roles (key TEXT PRIMARY KEY, title TEXT NOT NULL, requirements TEXT NOT NULL)')
            key = ' '.join(normalize(title).split())
            if replace:
                if not db.execute('UPDATE custom_roles SET requirements=? WHERE key=?', (payload, key)).rowcount:
                    raise ValidationError('This custom role no longer exists. Save it as a new role.')
            else:
                try:
                    db.execute('INSERT INTO custom_roles VALUES (?, ?, ?)', (key, title, payload))
                except sqlite3.IntegrityError as exc:
                    raise ValidationError('A role with this title already exists. Use Edit saved roles to update it.') from exc

    def delete(self, title):
        if self.path.exists():
            with closing(sqlite3.connect(self.path)) as db, db:
                db.execute('DELETE FROM custom_roles WHERE key=?', (' '.join(normalize(title).split()),))
