from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[2]
VERSION_FILE = REPO_ROOT / "VERSION.txt"

def get_git_version() -> str:
    try:
        desc = subprocess.check_output(
            ["git", "describe", "--always", "--dirty", "--tags"],
            cwd=REPO_ROOT,
            text=True
        ).strip()
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=REPO_ROOT,
            text=True
        ).strip()
        return f"{desc} [{branch}]"
    except Exception:
        return "unknown"

def get_version() -> str:
    if VERSION_FILE.exists():
        text = VERSION_FILE.read_text(encoding="utf-8").strip()
        if text:
            return text
    return get_git_version()

if __name__ == "__main__":
    print(get_version())
