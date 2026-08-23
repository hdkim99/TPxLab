"""Fail CI unless scientific dependencies are ARM64 wheels and Tk imports."""

from __future__ import annotations

import importlib.metadata
import platform
import tkinter


def main() -> int:
    """Verify the measured DGX architecture and binary scientific distributions."""

    machine = platform.machine().lower()
    if machine not in {"aarch64", "arm64"}:
        raise RuntimeError(f"expected ARM64 runner, got {machine}")

    for package in ("numpy", "scipy"):
        distribution = importlib.metadata.distribution(package)
        wheel = distribution.read_text("WHEEL") or ""
        tags = [
            line.removeprefix("Tag: ") for line in wheel.splitlines() if line.startswith("Tag: ")
        ]
        if not tags or not any("aarch64" in tag.lower() or "arm64" in tag.lower() for tag in tags):
            raise RuntimeError(f"{package} is not installed from an ARM64 wheel: {tags}")
        print(f"{package} {distribution.version}: {tags}")

    print(f"Python {platform.python_version()} on {machine}; Tk {tkinter.TkVersion}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
