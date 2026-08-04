"""Resolve a python-build-standalone download URL.

Usage: python pbs.py <python-major> <arch>

Prints the browser download URL of the matching cpython install_only
tarball from the latest release, or exits non-zero if none matches.
"""

import json
import re
import sys
import urllib.request

API = "https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest"


def main() -> int:
    major, arch = sys.argv[1], sys.argv[2]
    pattern = re.compile(
        r"cpython-" + re.escape(major) + r"\.\d+\+\d+-" + re.escape(arch)
        + r"-unknown-linux-gnu-install_only\.tar\.gz$"
    )
    with urllib.request.urlopen(API, timeout=30) as resp:
        assets = json.load(resp)["assets"]
    url = next((a["browser_download_url"] for a in assets if pattern.match(a["name"])), None)
    if url is None:
        print(f"no python-build-standalone asset for cpython {major} {arch}", file=sys.stderr)
        return 1
    print(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
