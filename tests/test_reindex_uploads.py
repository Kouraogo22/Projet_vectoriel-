from pathlib import Path

from scripts.reindex_uploads import legacy_id_for, metadata_for


def test_reconstructed_filename_recovers_legacy_metadata():
    path = Path("document_12_document_12.txt")
    legacy = {"document_12": {"title": "Titre lisible", "category": "Sciences"}}

    assert legacy_id_for(path) == "document_12"
    assert metadata_for(path, legacy, {}) == (
        "Titre lisible",
        "Sciences",
        "reconstructed",
        path.name,
    )


def test_original_upload_prefix_is_hidden_from_user():
    path = Path("04b7ea9ce75148de922623f2fcd45c36_rapport.pdf")

    title, _, storage_kind, original_filename = metadata_for(path)

    assert title == "rapport"
    assert storage_kind == "original"
    assert original_filename == "rapport.pdf"
