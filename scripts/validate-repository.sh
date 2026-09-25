#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 -m compileall -q scripts
python3 -B -m unittest discover -s scripts/tests -p 'test_*.py'

python3 - <<'PY'
from pathlib import Path
import importlib.util
import tomllib

module_path = Path("scripts/agent-task.py")
spec = importlib.util.spec_from_file_location("agent_task", module_path)
if spec is None or spec.loader is None:
    raise SystemExit("could not load scripts/agent-task.py")
agent_task = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent_task)

for path in sorted(Path("examples").glob("*/manifest.toml")):
    with path.open("rb") as handle:
        manifest = tomllib.load(handle)
    agent_task.validate_manifest(manifest)
    print(f"PASS: {path}")
PY

bash -n scripts/validate-repository.sh
echo "PASS: workflow repository validation"
