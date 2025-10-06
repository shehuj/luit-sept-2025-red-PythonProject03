#!/usr/bin/env python3
import sys
import json
from pathlib import Path

import yaml  # requires PyYAML

def load_required_from_yaml(config_path: Path) -> list[str] | None:
    """
    Loads the required files list from a YAML config file.
    Expects YAML structure like:
      required_files:
        - README.md
        - lambda_function.py
    Returns the list of required files, or None if file missing or malformed.
    """
    if not config_path.exists():
        return None
    try:
        content = yaml.safe_load(config_path.read_text())
        if not isinstance(content, dict):
            return None
        files = content.get("required_files")
        if not isinstance(files, list):
            return None
        # Ensure all entries are strings
        cleaned = [f for f in files if isinstance(f, str)]
        if len(cleaned) != len(files):
            return None
        return cleaned
    except Exception as e:
        print(f"Warning: could not parse {config_path}: {e}", file=sys.stderr)
        return None

def check_files(base_dir: Path, required_files: list[str]) -> dict:
    present = []
    missing = []
    for filename in required_files:
        target = base_dir / filename
        if target.exists():
            present.append(filename)
        else:
            missing.append(filename)
    return {
        "required": required_files,
        "present": present,
        "missing": missing,
        "all_present": (len(missing) == 0),
    }

def main():
    script_path = Path(__file__).resolve()
    repo_root = script_path.parent.parent  # adjust if script is not in scripts folder

    # Try to load override list from .required-files.yml / .required-files.yaml
    cfg1 = repo_root / ".required-files.yml"
    cfg2 = repo_root / ".required-files.yaml"
    required = load_required_from_yaml(cfg1)
    if required is None:
        required = load_required_from_yaml(cfg2)
    if required is None:
        # fallback default list
        required = [
            "README.md",
            ".gitignore",
            "requirements.txt",
            "lambda_function_foundational.py",
            "lambda_function_advance.py",
            # add others you need
        ]

    result = check_files(repo_root, required)

    # Print JSON to stdout
    print(json.dumps(result))

    # Exit with nonzero if missing any
    if not result["all_present"]:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()