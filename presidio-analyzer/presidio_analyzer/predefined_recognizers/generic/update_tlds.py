"""Refresh the vendored IANA root zone TLD list used by ``UrlRecognizer``."""

import sys
from pathlib import Path
from urllib.request import urlopen

IANA_URL = "https://data.iana.org/TLD/tlds-alpha-by-domain.txt"
TLD_FILE = Path(__file__).parent / "tlds.txt"


def update(url: str = IANA_URL, path: Path = TLD_FILE) -> int:
    """
    Download the IANA root zone list and rewrite the vendored copy.

    :param url: Location of the IANA ``tlds-alpha-by-domain.txt`` file
    :param path: File to rewrite
    :return: Number of TLDs written
    """
    with urlopen(url) as response:  # noqa: S310 - fixed https URL
        lines = response.read().decode("utf-8").splitlines()

    version = next((line for line in lines if line.startswith("#")), "# unknown")
    tlds = sorted(
        line.strip().lower() for line in lines if line.strip() and "#" not in line
    )
    if len(tlds) < 1000:
        raise ValueError(f"Refusing to write a suspiciously short list ({len(tlds)})")

    header = [
        f"# IANA Root Zone Database - {version.lstrip('# ')}",
        f"# Source: {url}",
        "# Regenerate with: "
        "python -m presidio_analyzer.predefined_recognizers.generic.update_tlds",
    ]
    path.write_text("\n".join(header + tlds) + "\n", encoding="utf-8")
    return len(tlds)


if __name__ == "__main__":
    count = update()
    print(f"Wrote {count} TLDs to {TLD_FILE}", file=sys.stderr)
