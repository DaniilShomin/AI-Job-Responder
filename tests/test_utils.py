import json
from pathlib import Path

import pytest

from app.exceptions import LoadingError
from app.utils import load_json, load_text_file, save_json


def test_load_json_existing(tmp_path: Path):
    filepath = tmp_path / "test.json"
    data = ["https://hh.ru/vacancy/123", "https://hh.ru/vacancy/456"]
    filepath.write_text(json.dumps(data), encoding="utf-8")
    result = load_json(filepath)
    assert result == data


def test_load_json_not_found_returns_empty_list(tmp_path: Path):
    filepath = tmp_path / "missing.json"
    result = load_json(filepath)
    assert result == []


def test_load_json_invalid_json_raises_loading_error(tmp_path: Path):
    filepath = tmp_path / "bad.json"
    filepath.write_text("not json", encoding="utf-8")
    with pytest.raises(LoadingError):
        load_json(filepath)


def test_save_and_load_json_roundtrip(tmp_path: Path):
    filepath = tmp_path / "roundtrip.json"
    data = ["url1", "url2"]
    save_json(filepath, data)
    result = load_json(filepath)
    assert result == data


def test_load_text_file_existing(tmp_path: Path):
    filepath = tmp_path / "text.txt"
    content = "Hello, world!"
    filepath.write_text(content, encoding="utf-8")
    result = load_text_file(filepath)
    assert result == content


def test_load_text_file_not_found_raises(tmp_path: Path):
    filepath = tmp_path / "missing.txt"
    with pytest.raises(LoadingError):
        load_text_file(filepath)
