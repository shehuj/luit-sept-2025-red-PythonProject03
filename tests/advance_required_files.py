import json
import tempfile
from pathlib import Path
import yaml
import pytest
import sys


from tests.check_required_files import check_files, load_required_from_yaml

def test_load_required_from_yaml_valid(tmp_path):
    yaml_path = tmp_path / ".required-files.yml"
    yaml.safe_dump({"required_files": ["README.md", "main.py"]}, open(yaml_path, "w"))
    result = load_required_from_yaml(yaml_path)
    assert result == ["README.md", "main.py"]

def test_load_required_from_yaml_missing(tmp_path):
    yaml_path = tmp_path / "nonexistent.yml"
    result = load_required_from_yaml(yaml_path)
    assert result is None

def test_load_required_from_yaml_malformed(tmp_path):
    yaml_path = tmp_path / ".required-files.yml"
    yaml.safe_dump({"wrong_key": ["foo"]}, open(yaml_path, "w"))
    result = load_required_from_yaml(yaml_path)
    assert result is None

def test_check_files(tmp_path):
    files = ["a.txt", "b.txt", "c.txt"]
    # Create only some of them
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.txt").write_text("b")

    result = check_files(tmp_path, files)
    assert result["present"] == ["a.txt", "b.txt"]
    assert result["missing"] == ["c.txt"]
    assert result["all_present"] is False

def test_check_files_all_present(tmp_path):
    files = ["x.txt"]
    (tmp_path / "x.txt").write_text("ok")

    result = check_files(tmp_path, files)
    assert result["all_present"]
    assert not result["missing"]