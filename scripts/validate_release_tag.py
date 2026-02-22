from __future__ import annotations

import os
import re
from pathlib import Path

import tomllib


def load_project_version() -> str:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    project_version = pyproject.get("project", {}).get("version")
    if not isinstance(project_version, str) or not project_version:
        raise SystemExit("Could not find project.version in pyproject.toml")
    return project_version


def validate_release_tag(ref_name: str, project_version: str) -> None:
    match = re.fullmatch(r"v(\d+\.\d+\.\d+)", ref_name)
    if match is None:
        raise SystemExit(
            f"Invalid release tag format. Expected vX.Y.Z (for example v1.2.3), got: {ref_name}"
        )

    tag_version = match.group(1)
    if tag_version != project_version:
        raise SystemExit(
            "Release tag version mismatch: "
            f"tag={ref_name} does not match project.version={project_version}"
        )

    print(f"Release tag check passed: {ref_name} matches project.version {project_version}")


def main() -> None:
    ref_name = os.getenv("GITHUB_REF_NAME")
    if not ref_name:
        raise SystemExit("GITHUB_REF_NAME is not set")
    validate_release_tag(ref_name, load_project_version())


if __name__ == "__main__":
    main()
