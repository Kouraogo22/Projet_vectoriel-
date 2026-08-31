"""Construit un corpus bilingue importable depuis les téléchargements Hugging Face.

Les fichiers bruts doivent être placés dans data/raw/huggingface_cache par les
commandes documentées dans le manifeste du corpus.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "huggingface_cache"
OUTPUT_DIR = PROJECT_ROOT / "data" / "experimental_corpus" / "huggingface_bilingual"

SOURCES = {
    "ag_news": {
        "dataset": "fancyzhx/ag_news",
        "url": "https://huggingface.co/datasets/fancyzhx/ag_news",
        "file": "data/train-00000-of-00001.parquet",
        "revision": "eb185aade064a813bc0b7f42de02595523103ca4",
        "split": "train",
        "language": "en",
        "license": "unknown (à vérifier auprès des détenteurs des dépêches sources)",
        "local_file": "ag_news_train.parquet",
    },
    "pubmedqa": {
        "dataset": "qiaojin/PubMedQA",
        "url": "https://huggingface.co/datasets/qiaojin/PubMedQA",
        "file": "pqa_labeled/train-00000-of-00001.parquet",
        "revision": "9001f2853fb87cab8d220904e0de81ac6973b318",
        "split": "train",
        "language": "en",
        "license": "MIT",
        "local_file": "pubmedqa_labeled_train.parquet",
    },
    "frenchqa": {
        "dataset": "CATIE-AQ/frenchQA",
        "url": "https://huggingface.co/datasets/CATIE-AQ/frenchQA",
        "file": "data/validation-00000-of-00001.parquet",
        "revision": "39b678ad23eef447fb6eda390b17388ae8457718",
        "split": "validation",
        "language": "fr",
        "license": "CC BY 4.0",
        "local_file": "frenchqa_validation.parquet",
    },
    "french_legal": {
        "dataset": "finaleads/french-corpus-llm-sample",
        "url": "https://huggingface.co/datasets/finaleads/french-corpus-llm-sample",
        "file": "sample.jsonl",
        "revision": "5cc70de432f485775b0506ad38edf1c6cdb9049a",
        "split": "échantillon",
        "language": "fr",
        "license": "Etalab-2.0",
        "local_file": "french_legal_sample.jsonl",
    },
}

AG_NEWS_LABELS = {
    0: "Actualités internationales",
    1: "Sport",
    2: "Économie et entreprises",
    3: "Sciences et technologies",
}


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return value[:60] or "document"


def read_json_records(path: Path) -> list[dict]:
    """Lit les objets JSON successifs, même si un document contient des retours à la ligne."""
    raw = path.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    records, position = [], 0
    while position < len(raw):
        while position < len(raw) and raw[position].isspace():
            position += 1
        if position >= len(raw):
            break
        record, position = decoder.raw_decode(raw, position)
        records.append(record)
    return records


def write_document(relative_path: str, text: str, metadata: dict, manifest: list[dict]) -> None:
    destination = OUTPUT_DIR / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    normalized_text = re.sub(r"\s+", " ", text).strip()
    destination.write_text(normalized_text + "\n", encoding="utf-8")
    manifest.append(
        {
            "file": relative_path,
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            "word_count": len(normalized_text.split()),
            **metadata,
        }
    )


def select_first(rows: Iterable[dict], count: int) -> list[dict]:
    selected = []
    for row in rows:
        if len(selected) == count:
            break
        selected.append(row)
    return selected


def build_ag_news(manifest: list[dict]) -> None:
    frame = pd.read_parquet(RAW_DIR / SOURCES["ag_news"]["local_file"])
    for label, domain in AG_NEWS_LABELS.items():
        examples = (
            frame.loc[frame["label"] == label]
            .head(2)
            .reset_index(names="source_row")
            .to_dict(orient="records")
        )
        for index, row in enumerate(examples, start=1):
            write_document(
                f"en/news/ag_news_{label}_{index}_{slugify(domain)}.txt",
                row["text"],
                {
                    "title": f"AG News — {domain} {index}",
                    "language": "en",
                    "domain": domain,
                    "document_type": "Brève d’actualité",
                    "source": SOURCES["ag_news"],
                    "source_row": int(row["source_row"]),
                    "source_label": int(label),
                },
                manifest,
            )


def build_pubmedqa(manifest: list[dict]) -> None:
    frame = pd.read_parquet(RAW_DIR / SOURCES["pubmedqa"]["local_file"])
    pubmed_rows = frame.iloc[[0, 1, 100, 300]].reset_index(names="source_row")
    for row in pubmed_rows.to_dict(orient="records"):
        context = " ".join(str(item) for item in row["context"]["contexts"])
        meshes = ", ".join(str(item) for item in row["context"]["meshes"][:6])
        text = f"Question : {row['question']}\n\nRésumé : {context}\n\nConclusion : {row['long_answer']}"
        write_document(
            f"en/health/pubmedqa_{row['pubid']}.txt",
            text,
            {
                "title": f"PubMedQA — publication {row['pubid']}",
                "language": "en",
                "domain": "Santé et biomédecine",
                "document_type": "Résumé d’article biomédical",
                "source": SOURCES["pubmedqa"],
                "source_row": int(row["source_row"]),
                "pubmed_id": int(row["pubid"]),
                "mesh_terms": meshes,
            },
            manifest,
        )


def build_frenchqa(manifest: list[dict]) -> None:
    frame = pd.read_parquet(RAW_DIR / SOURCES["frenchqa"]["local_file"])
    for index, row in enumerate(frame.iloc[[0, 200, 500, 800]].to_dict(orient="records"), start=1):
        text = f"Contexte : {row['context']}\n\nQuestion associée : {row['question']}"
        write_document(
            f"fr/news/frenchqa_actualite_{index}.txt",
            text,
            {
                "title": f"FrenchQA — actualité {index}",
                "language": "fr",
                "domain": "Actualités et société",
                "document_type": "Extrait d’actualité avec question associée",
                "source": SOURCES["frenchqa"],
                "source_row": row["id"],
                "upstream_source": row["title"],
            },
            manifest,
        )


def build_french_legal(manifest: list[dict]) -> None:
    records = read_json_records(RAW_DIR / SOURCES["french_legal"]["local_file"])
    selected_sources = ("amf_v2", "bofip", "jade", "kali")
    selected = []
    for source_name in selected_sources:
        candidate = next(
            (
                record
                for record in records
                if record["source"] == source_name and 300 <= record.get("n_words", 0) <= 1400
            ),
            None,
        )
        if candidate:
            selected.append(candidate)
    for row in selected:
        domain = {
            "amf_v2": "Réglementation financière",
            "bofip": "Fiscalité",
            "jade": "Droit administratif",
            "kali": "Droit du travail",
        }[row["source"]]
        write_document(
            f"fr/legal/{row['source']}_{row['id'][:10]}.txt",
            row["text"],
            {
                "title": f"{domain} — {row['id'][:10]}",
                "language": "fr",
                "domain": domain,
                "document_type": "Document juridique ou réglementaire",
                "source": SOURCES["french_legal"],
                "source_row": row["id"],
                "upstream_source": row["source"],
                "upstream_url": row["url"],
            },
            manifest,
        )


def write_manifest(entries: list[dict]) -> None:
    payload = {
        "corpus_name": "huggingface_bilingual",
        "purpose": "Importation via l’interface Streamlit et expérimentation de la recherche sémantique.",
        "document_count": len(entries),
        "languages": {"fr": sum(entry["language"] == "fr" for entry in entries), "en": sum(entry["language"] == "en" for entry in entries)},
        "entries": entries,
    }
    (OUTPUT_DIR / "manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# Manifeste du corpus expérimental bilingue",
        "",
        "Ce dossier contient 20 documents TXT issus de quatre jeux de données publics Hugging Face. "
        "Ils sont destinés à être importés individuellement via l’interface Streamlit, puis à tester l’indexation et la recherche sémantique.",
        "",
        "## Répartition",
        "",
        "| Langue | Domaine | Type de document | Nombre | Source Hugging Face | Licence déclarée |",
        "|---|---|---:|---:|---|---|",
        "| Français | Actualités et société | Extrait d’actualité avec question associée | 4 | [CATIE-AQ/frenchQA](https://huggingface.co/datasets/CATIE-AQ/frenchQA) | CC BY 4.0 |",
        "| Français | Réglementation financière, fiscalité, droit administratif et droit du travail | Document juridique ou réglementaire | 4 | [finaleads/french-corpus-llm-sample](https://huggingface.co/datasets/finaleads/french-corpus-llm-sample) | Etalab-2.0 |",
        "| Anglais | Actualités internationales, sport, économie et sciences/technologies | Brève d’actualité | 8 | [fancyzhx/ag_news](https://huggingface.co/datasets/fancyzhx/ag_news) | Inconnue dans la carte du jeu de données |",
        "| Anglais | Santé et biomédecine | Résumé d’article biomédical | 4 | [qiaojin/PubMedQA](https://huggingface.co/datasets/qiaojin/PubMedQA) | MIT |",
        "",
        "## Importation dans l’interface",
        "",
        "1. Démarrer Qdrant, l’API FastAPI et Streamlit.",
        "2. Dans l’interface, choisir **Ajouter un document**.",
        "3. Sélectionner un fichier TXT dans les sous-dossiers `fr/` ou `en/`.",
        "4. Reprendre le domaine indiqué dans `manifest.json` comme catégorie afin d’activer les filtres de recherche.",
        "",
        "`manifest.json` fournit, pour chaque fichier, le jeu de données, le split, le fichier source, le type de document, la langue, le domaine, l’identifiant de la ligne source et l’empreinte SHA-256.",
        "",
        "## Limite d’usage",
        "",
        "Ce corpus est destiné à l’expérimentation technique du prototype. Il ne doit pas être utilisé pour rendre un conseil juridique, médical ou financier. La licence et les conditions de chaque source doivent être vérifiées avant toute redistribution au-delà de ce cadre.",
        "",
    ]
    (OUTPUT_DIR / "MANIFEST.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for document in OUTPUT_DIR.rglob("*.txt"):
        document.unlink()
    manifest: list[dict] = []
    build_ag_news(manifest)
    build_pubmedqa(manifest)
    build_frenchqa(manifest)
    build_french_legal(manifest)
    write_manifest(manifest)
    print(f"{len(manifest)} documents créés dans {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
