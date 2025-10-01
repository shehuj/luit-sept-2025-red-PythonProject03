#!/usr/bin/env python3
import sys
import json
from pathlib import Path

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
    repo_root = script_path.parent.parent  # base directory where files should reside

    required = [
        "README.md",
        ".gitignore",
        "requirements.txt"
        # add others you need
    ]

    result = check_files(repo_root, required)

    # Print JSON to stdout
    print(json.dumps(result))

    # Exit code
    if not result["all_present"]:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()