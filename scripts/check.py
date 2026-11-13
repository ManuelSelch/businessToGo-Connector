#!/usr/bin/env python3
"""Dependency-free local checks. Never installs or contacts Odoo."""
import ast
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    for source in ROOT.rglob("*.py"):
        if ".git" not in source.parts:
            ast.parse(source.read_text(), filename=str(source))
    print("Python syntax: passed", flush=True)
    return subprocess.call(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
    )


if __name__ == "__main__":
    raise SystemExit(main())
