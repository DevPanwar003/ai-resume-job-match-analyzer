"""In-memory exports. No disk writes, remote assets, or second scoring formula."""
from html import escape
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from .comparison import JobMatch

WARNING = "The score is an analytical aid and does not predict hiring success. It does not verify qualifications or ATS outcomes."
METHODOLOGY = (
    "Score = 70 x skill coverage + 30 x TF-IDF cosine similarity (both components range from 0 to 1). "
    "Coverage is the number of unique matched job skills divided by unique recognized job skills. "
    "Aliases and duplicates count once; related skills earn no coverage credit. "
    "TF-IDF is computed independently for each resume/job pair using normalized word tokens, an explicit English stopword list, "
    "TF = 1 + ln(count), IDF = 1 + ln(3 / (1 + document frequency)), and L2 cosine normalization. "
    "When enabled, a recognized title uses an illustrative local role profile; full descriptions replace generic requirements. "
    "Catalog importance weights guide learning priority only; coverage remains unweighted. Title-only TF-IDF uses generated profile text. "
    "Unrecognized title-only or insufficient descriptions (under 20 words, under 10 distinct words, or no task/requirement context), "
    "or no recognized skills in either document, mean N/A coverage and score with no gaps or recommendations assessed. "
    "TF-IDF is wording similarity only, not skill coverage. Empty vectors have zero similarity. "
    "Ranking uses unrounded scores descending, ties retain input order, and N/A jobs are last and unranked. "
    "Pair-specific scores are exploratory and not standardized across jobs. Weights are design choices. "
    "Mentions do not establish proficiency; negation, required versus optional skills, and experience are not understood. "
    "The taxonomy is incomplete; wording and extraction errors can change results."
)


def report_sections(results: tuple[JobMatch, ...], include_evidence: bool = False):
    if not results:
        raise ValueError("A report requires at least one comparison result.")
    for rank, item in enumerate(results, 1):
        match = item.match
        rank_label = str(rank) if match.score is not None else "N/A"
        score = "N/A" if match.score is None else f"{match.score:.2f}/100"
        coverage = "N/A" if match.coverage is None else f"{match.coverage:.2%}"
        if match.warning:
            yield f"Rank N/A | Job {item.index}: {item.title}", [
                match.warning, f"TF-IDF similarity (shared wording only, not skill coverage): {match.similarity:.2%}.",
                "Matched skills, missing skills and related skills: not assessed.",
                "Recommendations: withheld until sufficient recognized evidence is available."]
            continue
        lines = [f"Match score: {score}. Skill coverage: {coverage}. TF-IDF similarity: {match.similarity:.2%}.",
                 f"Skill points: {'N/A' if match.skill_points is None else f'{match.skill_points:.2f}'}/70; text points: {match.text_points:.2f}/30.",
                 "Matched skills: " + (", ".join(match.matched) or "None detected"),
                 "Missing skills: " + (", ".join(match.missing) or "None detected"),
                 "Related skills (resume -> missing job skill; not exact matches): " +
                 ("; ".join(f"{present} -> {required}" for required, present in match.related) or "None detected"),
                 "Recommendations: add only facts you can substantiate. Missing mentions are not proof of missing abilities."]
        if match.role:
            lines.append("Selected catalog role: " + match.role + ". Guidance only, not verified employer requirements.")
            for weight, label in ((2, "Essential"), (1, "Preferred"), (0, "Importance unspecified")):
                lines.append(label + ": " + (", ".join(r.skill for r in match.requirements if r.weight == weight) or "None specified"))
        for number, suggestion in enumerate(item.suggestions, 1):
            if include_evidence:
                lines.append(f"Evidence {number}: {suggestion.evidence}")
            lines.append(f"Suggestion {number}: {suggestion.advice}")
        if not item.suggestions:
            lines.append("No suitable bullet lines detected. Describe an actual task, your own action and a verifiable result; no experience has been inferred.")
        yield f"Rank {rank_label} | Job {item.index}: {item.title}", lines


def html_report(results: tuple[JobMatch, ...], include_evidence: bool = False) -> bytes:
    sections = "".join("<section><h2>" + escape(title) + "</h2>" +
                       "".join("<p>" + escape(line) + "</p>" for line in lines) + "</section>"
                       for title, lines in report_sections(results, include_evidence))
    document = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
    <title>Resume Lab - V3 comparison report</title><style>
    body{{font:16px/1.6 system-ui,sans-serif;color:#14263d;background:#f6f8fc;max-width:960px;margin:40px auto;padding:24px}}
    h1{{background:#14263d;color:white;padding:24px;border-radius:12px}}h2{{color:#087f75}}
    section{{background:white;border-top:3px solid #0d9488;margin:24px 0;padding:24px;break-inside:auto}}
    p{{overflow-wrap:anywhere}}.warning{{border-left:5px solid #0d9488;padding:16px;background:#e8eef5}}
    @media print{{body{{margin:0;background:white}}section{{break-before:page}}}}
    </style></head><body><h1>Resume Lab | Version 3 comparison</h1>
    <p class="warning">{escape(WARNING)}</p><h2>Score methodology and limitations</h2>
    <p>{escape(METHODOLOGY)}</p><p>Generated locally. Source documents are omitted. Evidence excerpts: {'included - review before sharing' if include_evidence else 'excluded'}.
    Job titles and skill summaries may still be sensitive.</p>{sections}</body></html>"""
    return document.encode("utf-8")


def pdf_report(results: tuple[JobMatch, ...], include_evidence: bool = False) -> bytes:
    output = BytesIO()
    styles = getSampleStyleSheet()
    styles['Normal'].fontSize = 10
    styles['Normal'].leading = 15
    styles['Normal'].alignment = TA_LEFT
    styles['Normal'].splitLongWords = True
    styles['Heading1'].textColor = colors.HexColor('#14263d')
    styles['Heading2'].textColor = colors.HexColor('#087f75')
    # Built-in PDF fonts support Western text; unsupported glyphs are explicit '?'.
    def p(text, style='Normal'):
        safe = text.encode('cp1252', errors='replace').decode('cp1252')
        return Paragraph(escape(safe), styles[style])
    story = [p('Resume Lab | Version 3 comparison', 'Heading1'), p(WARNING), Spacer(1, 16),
             p('Score methodology and limitations', 'Heading2'), p(METHODOLOGY), Spacer(1, 16),
             p('Generated locally. Source documents omitted. Evidence excerpts: ' +
               ('included; review before sharing.' if include_evidence else 'excluded.') +
               ' Job titles and skill summaries may still be sensitive. Unsupported PDF glyphs appear as ?. HTML preserves Unicode.')]
    for title, lines in report_sections(results, include_evidence):
        story.extend([PageBreak(), p(title, 'Heading2')])
        for line in lines:
            story.extend([p(line), Spacer(1, 9)])
    def footer(canvas, doc):
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.drawString(42, 25, 'Resume Lab | Local analysis | Not a hiring prediction')
        canvas.drawRightString(550, 25, f'Page {doc.page}')
    SimpleDocTemplate(output, leftMargin=42, rightMargin=42, topMargin=42, bottomMargin=48,
                      title='Resume Lab V3 comparison', author='Resume Lab').build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
