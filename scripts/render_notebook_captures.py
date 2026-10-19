"""Génère les figures du mémoire à partir des sorties exécutées des notebooks."""
from __future__ import annotations

import base64
import io
import textwrap
from pathlib import Path

import nbformat
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "notebooks"
FIGURES = ROOT.parent.parent / "Rapport" / "figures"
RESULTS = ROOT / "evaluation" / "results"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
MONO = "/System/Library/Fonts/Supplemental/Andale Mono.ttf"


def font(size: int, bold: bool = False, mono: bool = False):
    path = MONO if mono else (FONT_BOLD if bold else FONT)
    return ImageFont.truetype(path, size)


def first_png_output(notebook_path: Path) -> bytes:
    notebook = nbformat.read(notebook_path, as_version=4)
    for cell in notebook.cells:
        for output in cell.get("outputs", []):
            data = output.get("data", {})
            if "image/png" in data:
                content = data["image/png"]
                return base64.b64decode(content)
    raise RuntimeError(f"Aucune sortie image dans {notebook_path.name}")


def draw_wrapped(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], width: int, size: int, *, bold: bool = False, color="#202124", spacing: int = 8) -> int:
    current_font = font(size, bold=bold)
    words = text.split()
    lines: list[str] = []
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if draw.textlength(candidate, font=current_font) <= width:
            line = candidate
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    draw.multiline_text(xy, "\n".join(lines), font=current_font, fill=color, spacing=spacing)
    return xy[1] + len(lines) * (size + spacing)


def render_full_notebook(summary: pd.DataFrame, chart: Image.Image) -> None:
    width, height = 2200, 3000
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    x, y = 80, 58
    draw.text((x, y), "Évaluation comparative : TF-IDF, Qdrant vectoriel et recherche hybride", font=font(34, bold=True), fill="#202124")
    y += 58
    y = draw_wrapped(
        draw,
        "Sortie exécutée du notebook notebooks/evaluation.ipynb. Le protocole compare les trois méthodes sur 900 documents répartis dans neuf catégories et 90 requêtes contrôlées. Chaque méthode est exécutée sans filtre, puis avec filtre de catégorie.",
        (x, y),
        width - 2 * x,
        18,
    ) + 25

    def code_cell(number: int, source: str, output: str | None = None) -> None:
        nonlocal y
        draw.text((x - 44, y + 18), f"In [{number}]:", font=font(14, mono=True), fill="#8a8a8a")
        lines = source.splitlines()
        block_height = 28 + len(lines) * 25
        draw.rounded_rectangle((x, y, width - x, y + block_height), radius=4, fill="#f5f5f5", outline="#e5e5e5")
        draw.multiline_text((x + 20, y + 14), source, font=font(16, mono=True), fill="#186a18", spacing=5)
        y += block_height + 16
        if output:
            draw.text((x - 44, y + 8), f"Out[{number}]:", font=font(14, mono=True), fill="#8a8a8a")
            y = draw_wrapped(draw, output, (x, y), width - 2 * x, 16, color="#333333") + 18

    code_cell(
        1,
        "from evaluation.evaluate_balanced_collection import main\nmain()",
        "Résultats de l'évaluation selon le protocole. Les fichiers CSV de synthèse et de détail sont enregistrés dans evaluation/results.",
    )
    code_cell(
        2,
        "summary = pd.read_csv(RESULTS / 'protocol_comparison_summary_metrics.csv')\nsummary_at_10 = summary[['Méthode', 'Scénario', 'Precision@10', 'Recall@10', 'MRR@10', 'nDCG@10', 'Temps (ms)']]",
    )

    columns = ["Méthode", "Scénario", "Precision@10", "Recall@10", "MRR@10", "nDCG@10", "Temps (ms)"]
    widths = [275, 390, 190, 170, 150, 170, 180]
    top = y
    row_height = 47
    draw.rectangle((x, top, width - x, top + row_height), fill="#f2f2f2")
    cursor = x + 12
    for name, col_width in zip(columns, widths):
        draw.text((cursor, top + 13), name, font=font(14, bold=True), fill="#303030")
        cursor += col_width
    for row_index, (_, row) in enumerate(summary[columns].iterrows(), 1):
        top += row_height
        fill = "#ffffff" if row_index % 2 else "#fafafa"
        draw.rectangle((x, top, width - x, top + row_height), fill=fill)
        values = [
            str(row["Méthode"]),
            "Avec filtre" if "Avec" in row["Scénario"] else "Sans filtre",
            f"{row['Precision@10']:.4f}",
            f"{row['Recall@10']:.4f}",
            f"{row['MRR@10']:.4f}",
            f"{row['nDCG@10']:.4f}",
            f"{row['Temps (ms)']:.4f}",
        ]
        cursor = x + 12
        for value, col_width in zip(values, widths):
            draw.text((cursor, top + 14), value, font=font(13), fill="#252525")
            cursor += col_width
    y = top + row_height + 34

    code_cell(
        3,
        "plot_data = summary[summary['Scénario'] == 'Sans filtre']\nplot_data.set_index('Méthode')[['Recall@10', 'MRR@10', 'nDCG@10']].plot.bar()",
    )
    chart = chart.convert("RGB")
    max_width = width - 2 * x
    ratio = min(max_width / chart.width, 760 / chart.height)
    chart = chart.resize((int(chart.width * ratio), int(chart.height * ratio)))
    canvas.paste(chart, ((width - chart.width) // 2, y))
    y += chart.height + 28
    draw.line((x, y, width - x, y), fill="#dddddd", width=2)
    y += 24
    draw.text((x, y), "Interprétation et limite", font=font(22, bold=True), fill="#202124")
    y += 38
    draw_wrapped(
        draw,
        "Les 90 requêtes sont tirées de la première phrase de dix documents pertinents par catégorie. Il s'agit d'un protocole contrôlé et reproductible ; il ne remplace pas un jeu de requêtes indépendantes formulées par des utilisateurs.",
        (x, y),
        width - 2 * x,
        17,
    )
    canvas.crop((0, 0, width, 1780)).save(
        FIGURES / "notebook-comparison-complete.png", dpi=(180, 180)
    )


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    exploration_chart = first_png_output(NOTEBOOKS / "exploration.ipynb")
    evaluation_chart = first_png_output(NOTEBOOKS / "evaluation.ipynb")
    (FIGURES / "notebook-embeddings.png").write_bytes(exploration_chart)
    (FIGURES / "notebook-metrics.png").write_bytes(evaluation_chart)
    summary = pd.read_csv(RESULTS / "protocol_comparison_summary_metrics.csv")
    render_full_notebook(summary, Image.open(io.BytesIO(evaluation_chart)))
    print("Captures mises à jour dans", FIGURES)


if __name__ == "__main__":
    main()
