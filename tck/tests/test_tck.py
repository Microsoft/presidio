"""TCK integration test — extract YAML from tests, validate against Presidio."""

import subprocess
import sys
from pathlib import Path

TCK_DIR = Path(__file__).resolve().parent.parent


def test_extract_and_validate():
    """Extract TCK YAML and validate all cases pass against live recognizers."""
    result = subprocess.run(
        [sys.executable, str(TCK_DIR / "extract_tck.py")],
        capture_output=True,
        text=True,
        cwd=str(TCK_DIR),
    )
    assert result.returncode == 0, (
        f"extract_tck.py failed:\n{result.stdout}\n{result.stderr}"
    )

    result = subprocess.run(
        [sys.executable, str(TCK_DIR / "validate_tck.py")],
        capture_output=True,
        text=True,
        cwd=str(TCK_DIR),
    )
    assert result.returncode == 0, (
        f"validate_tck.py failed:\n{result.stdout}\n{result.stderr}"
    )
