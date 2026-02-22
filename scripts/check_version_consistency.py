from __future__ import annotations

from pathlib import Path

import tomllib

import tutr

pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
project_version = pyproject.get("project", {}).get("version")
if not isinstance(project_version, str) or not project_version:
    raise SystemExit("Could not find project.version in pyproject.toml")
module_version = tutr.__version__

if project_version != module_version:
    raise SystemExit(
        "Version mismatch: pyproject.toml project.version="
        f"{project_version} != tutr.__version__={module_version}"
    )

print(f"Version check passed: {project_version}")
