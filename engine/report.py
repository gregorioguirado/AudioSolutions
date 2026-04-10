from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import cm
from translator import TranslationResult


class ReportGenerationError(Exception):
    pass


_ACRONYMS = {"EQ", "HPF", "LPF", "VCA", "DSP", "MCA", "LCA", "RTA", "RMS", "PFL"}


def _format_parameter_name(s: str) -> str:
    """Format a parameter name string for display.

    Replaces underscores with spaces and title-cases each word,
    except known audio acronyms which are rendered in full uppercase.
    """
    words = s.replace("_", " ").split()
    return " ".join(w.upper() if w.upper() in _ACRONYMS else w.title() for w in words)


CONSOLE_DISPLAY_NAMES = {
    "yamaha_cl": "Yamaha CL/QL",
    "digico_sd": "DiGiCo SD/Quantum",
}


def generate_report(
    result: TranslationResult,
    source_console: str,
    target_console: str,
) -> bytes:
    """Generate a PDF translation report and return it as bytes."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle("title", parent=styles["Heading1"], fontSize=18)
    story.append(Paragraph("Show File Translation Report", title_style))
    story.append(Spacer(1, 0.5*cm))

    # Summary line
    src_name = CONSOLE_DISPLAY_NAMES.get(source_console, source_console)
    tgt_name = CONSOLE_DISPLAY_NAMES.get(target_console, target_console)
    story.append(Paragraph(
        f"<b>Translation:</b> {src_name} -&gt; {tgt_name}",
        styles["Normal"]
    ))
    story.append(Paragraph(
        f"<b>Channels translated:</b> {result.channel_count}",
        styles["Normal"]
    ))
    story.append(Spacer(1, 0.5*cm))

    # WARNING banner
    story.append(Paragraph(
        "WARNING: Always verify this file on the target console before the show. "
        "Load it, check the patch list, and spot-check EQ and dynamics on key channels.",
        ParagraphStyle("warn", parent=styles["Normal"],
                       backColor=colors.lightyellow,
                       borderPadding=6)
    ))
    story.append(Spacer(1, 0.5*cm))

    def section(title: str, items: list[str]) -> None:
        story.append(Paragraph(title, styles["Heading2"]))
        if not items:
            story.append(Paragraph("None", styles["Normal"]))
        else:
            for item in items:
                story.append(Paragraph(f"- {_format_parameter_name(item)}", styles["Normal"]))
        story.append(Spacer(1, 0.3*cm))

    section("Successfully Translated", result.translated_parameters)
    section("Approximated (verify on desk)", result.approximated_parameters)
    section("Dropped (not available on target)", result.dropped_parameters)

    try:
        doc.build(story)
    except Exception as e:
        raise ReportGenerationError(f"Failed to build PDF report: {e}") from e
    return buf.getvalue()
