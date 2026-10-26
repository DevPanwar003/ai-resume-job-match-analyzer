"""Rebuild fictional PDF/DOCX fixtures using only project dependencies."""
from pathlib import Path
from docx import Document
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

ROOT = Path(__file__).resolve().parents[1]


def main():
    text = (ROOT / "samples/fictional_resume.txt").read_text(encoding="utf-8")
    document = Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    document.save(ROOT / "samples/fictional_resume.docx")
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"):
        DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
    commands = ["BT /F1 10 Tf 40 750 Td 15 TL"]
    for line in text.splitlines():
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.append(f"({escaped}) Tj T*")
    commands.append("ET")
    stream = DecodedStreamObject()
    stream.set_data("\n".join(commands).encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.write(ROOT / "samples/fictional_resume.pdf")


if __name__ == "__main__":
    main()
