"""Curated, editable taxonomy. Aliases mean equivalence; related means adjacency.

Do not infer Python from pandas, SQL from SQLite, or proficiency from any mention.
Add canonical skills and their aliases here, and pairs to RELATED_PAIRS below.
"""
import re
import unicodedata

SKILLS = {
    "Java": ("java",), "JavaScript": ("javascript", "js"),
    "HTML": ("html", "html5"), "CSS": ("css", "css3"),
    "React": ("react", "reactjs", "react.js"),
    "Spring": ("spring framework", "spring boot", "spring"),
    "REST APIs": ("rest api", "rest apis", "restful api", "restful apis"),
    "Software testing": ("software testing", "unit testing", "unit tests"),
    "Docker": ("docker",),
    "Database administration": ("database administration", "database backup", "database backups"),
    "Requirements analysis": ("requirements analysis", "requirements gathering", "requirements elicitation"),
    "Python": ("python", "python3", "python 3"),
    "SQL": ("sql", "structured query language"),
    "Excel": ("excel", "microsoft excel", "ms excel"),
    "Power BI": ("power bi", "powerbi"),
    "Tableau": ("tableau",),
    "Statistics": ("statistics", "statistical analysis", "statistical modeling", "statistical modelling", "descriptive statistics"),
    "Data analysis": ("data analysis", "data analytics", "analyzing data", "analysing data"),
    "Data visualization": ("data visualization", "data visualisation", "visualization", "visualisation"),
    "Machine learning": ("machine learning", "ml"),
    "pandas": ("pandas",),
    "NumPy": ("numpy",),
    "scikit-learn": ("scikit-learn", "scikit learn", "sklearn"),
    "TensorFlow": ("tensorflow",),
    "PyTorch": ("pytorch",),
    "Matplotlib": ("matplotlib",),
    "Seaborn": ("seaborn",),
    "Plotly": ("plotly",),
    "SQLite": ("sqlite", "sqlite3"),
    "PostgreSQL": ("postgresql", "postgres"),
    "MySQL": ("mysql",),
    "Data cleaning": ("data cleaning", "data cleansing", "data wrangling"),
    "Data validation": ("data validation", "data quality"),
    "ETL": ("etl", "extract transform load", "extract, transform, load", "extract, transform and load"),
    "Dashboards": ("dashboard", "dashboards", "dashboarding"),
    "Business intelligence": ("business intelligence", "bi reporting"),
    "DAX": ("dax", "data analysis expressions"),
    "Power Query": ("power query",),
    "Pivot tables": ("pivot table", "pivot tables", "pivottable", "pivottables"),
    "A/B testing": ("a/b testing", "a/b tests", "ab testing", "split testing"),
    "Regression": ("regression", "linear regression", "logistic regression"),
    "Git": ("git",),
    "Streamlit": ("streamlit",),
    "Communication": ("communication", "communication skills", "presenting findings", "communicate findings"),
    "Problem-solving": ("problem solving", "problem-solving", "solve problems"),
}

RELATED_PAIRS = (
    ("Python", "pandas"), ("Python", "NumPy"), ("Python", "Streamlit"),
    ("SQL", "SQLite"), ("SQL", "PostgreSQL"), ("SQL", "MySQL"),
    ("Excel", "Pivot tables"), ("Excel", "Power Query"),
    ("Power BI", "DAX"), ("Power BI", "Power Query"), ("Power BI", "Tableau"),
    ("Data visualization", "Power BI"), ("Data visualization", "Tableau"),
    ("Data visualization", "Matplotlib"), ("Data visualization", "Seaborn"),
    ("Data visualization", "Plotly"), ("Statistics", "Regression"),
    ("Statistics", "A/B testing"), ("Statistics", "Machine learning"),
    ("Machine learning", "scikit-learn"), ("Machine learning", "TensorFlow"),
    ("Machine learning", "PyTorch"), ("Data cleaning", "Data validation"),
    ("Data cleaning", "ETL"),
)


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold().translate(
        str.maketrans({"–": "-", "—": "-", "‑": "-", "‐": "-"}))


def alias_pattern(alias: str) -> re.Pattern:
    # Whole-token boundaries avoid SQL inside NoSQL or Excel inside excellent.
    body = r"[\s-]+".join(re.escape(part) for part in re.split(r"[\s-]+", normalize(alias)))
    return re.compile(r"(?<!\w)" + body + r"(?!\w)")


PATTERNS = {name: tuple(alias_pattern(alias) for alias in aliases) for name, aliases in SKILLS.items()}


def extract_skills(text: str) -> tuple[str, ...]:
    """Deduplicated canonical mentions, not verified qualifications. Empty text -> ()."""
    normalized = normalize(text)
    return tuple(sorted((name for name, patterns in PATTERNS.items()
                         if any(pattern.search(normalized) for pattern in patterns)), key=str.casefold))


def are_related(first: str, second: str) -> bool:
    return (first, second) in RELATED_PAIRS or (second, first) in RELATED_PAIRS
