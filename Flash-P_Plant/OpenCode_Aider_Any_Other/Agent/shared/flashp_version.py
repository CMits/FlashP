#!/usr/bin/env python3
"""
Flash-P version utility.

Reads the VERSION file and provides a function to get the current version.
All output-producing scripts should call get_version() and stamp it into their outputs.
"""

from pathlib import Path


def get_version() -> str:
    """Read the Flash-P framework version from the VERSION file."""
    version_file = Path(__file__).parent / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return "unknown"


def get_version_info() -> dict:
    """Return version metadata dict suitable for embedding in JSON outputs."""
    return {
        "flash_p_version": get_version(),
    }


if __name__ == "__main__":
    print(f"Flash-P v{get_version()}")
