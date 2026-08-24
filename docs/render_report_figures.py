from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path


ASSET_DIR = Path(__file__).resolve().parent / "report_assets"
FIGURES = (
    "figure_01_problem_decomposition",
    "figure_02_hypothesis_evolution",
    "figure_03_final_architecture",
    "figure_04_benchmark_efficiency",
    "figure_05_benchmark_quality",
)


def extract_svg(html: str) -> str:
    style = re.search(r"<style>(.*?)</style>", html, re.S)
    svg = re.search(r"(<svg\b.*?</svg>)", html, re.S)
    if style is None or svg is None:
        raise ValueError("図のHTMLからSVGを抽出できません")
    content = svg.group(1).replace(
        "<svg ",
        '<svg xmlns="http://www.w3.org/2000/svg" ',
        1,
    )
    opening_end = content.index(">") + 1
    return content[:opening_end] + "<style>" + style.group(1) + "</style>" + content[opening_end:]


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="bakuraku-figures-") as tmp:
        tmp_dir = Path(tmp)
        for stem in FIGURES:
            html_path = ASSET_DIR / f"{stem}.html"
            svg_path = tmp_dir / f"{stem}.svg"
            png_path = ASSET_DIR / f"{stem}.png"
            svg_path.write_text(extract_svg(html_path.read_text(encoding="utf-8")), encoding="utf-8")
            subprocess.run(
                ["rsvg-convert", "-w", "2400", "-h", "1350", "-o", str(png_path), str(svg_path)],
                check=True,
            )
            print(png_path)


if __name__ == "__main__":
    main()
