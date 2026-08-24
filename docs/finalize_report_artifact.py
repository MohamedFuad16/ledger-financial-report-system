from pathlib import Path

from docx import Document
from docx.oxml.ns import qn


REPORT = Path(__file__).with_name("バクラク事業部技術_実験報告書_完成版.docx")


def main() -> None:
    document = Document(REPORT)
    trailing = document.paragraphs[-1]
    following = trailing._element.getnext()
    if not trailing.text and following is not None and following.tag == qn("w:sectPr"):
        trailing._element.getparent().remove(trailing._element)
    document.save(REPORT)
    print(REPORT)


if __name__ == "__main__":
    main()
