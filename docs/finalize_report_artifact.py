from pathlib import Path

from docx import Document
from docx.oxml.ns import qn


REPORT = Path(__file__).with_name("バクラク事業部技術_実験報告書_完成版.docx")


def main() -> None:
    document = Document(REPORT)
    toc_pages = {
        "要旨": "3",
        "1.0 背景・課題設定": "4",
        "2.0 目的・仮説・評価観点": "5",
        "3.0 対象範囲・前提条件": "6",
        "4.0 実施方法／三戦略": "7",
        "5.0 実装・最終アーキテクチャ": "8",
        "6.0 評価方法・結果": "10",
        "7.0 考察": "14",
        "8.0 結論・次の課題": "16",
        "参考文献": "17",
        "付録": "18",
    }
    for paragraph in document.paragraphs:
        if not paragraph.style.name.lower().startswith("toc"):
            continue
        heading = paragraph.text.split("\t", 1)[0]
        if heading not in toc_pages:
            continue
        text_nodes = paragraph._element.xpath(".//w:t")
        text_nodes[-1].text = toc_pages[heading]
    appendix_e = next(p for p in document.paragraphs if p.text.startswith("付録E"))
    appendix_e.paragraph_format.page_break_before = True
    trailing = document.paragraphs[-1]
    following = trailing._element.getnext()
    if not trailing.text and following is not None and following.tag == qn("w:sectPr"):
        trailing._element.getparent().remove(trailing._element)
    document.save(REPORT)
    print(REPORT)


if __name__ == "__main__":
    main()
