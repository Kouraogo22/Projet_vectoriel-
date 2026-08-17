from src.extraction import extract_text

def test_extract_text_from_txt(tmp_path):
    document = tmp_path / "document.txt"
    document.write_text("Bonjour monde", encoding="utf-8")
    assert extract_text(document) == "Bonjour monde"
