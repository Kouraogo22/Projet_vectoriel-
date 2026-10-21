"""Export actual PNG outputs from the executed notebooks, without reconstructing UI."""
import argparse
import base64
from pathlib import Path
import nbformat

ROOT = Path(__file__).resolve().parents[1]


def first_png_output(path):
    notebook = nbformat.read(path, as_version=4)
    for cell in notebook.cells:
        for output in cell.get('outputs', []):
            data = output.get('data', {})
            if 'image/png' in data:
                return base64.b64decode(data['image/png'])
    raise RuntimeError(f'No executed PNG output: {path}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, default=ROOT.parent.parent/'Rapport/figures')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for source, target in [('exploration.ipynb','notebook-embeddings.png'),
                           ('evaluation.ipynb','notebook-metrics.png')]:
        (args.output_dir/target).write_bytes(first_png_output(ROOT/'notebooks'/source))
    print('Notebook figures exported:', args.output_dir)

if __name__ == '__main__': main()
