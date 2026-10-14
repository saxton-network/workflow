#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 -m compileall -q scripts
python3 -m compileall -q aitism_runtime
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
bash -n scripts/check-release-version.sh

for version in v0.1.0 v0.1.0-alpha.2 v1.20.3-rc.1 v2.0.0-x-y.7; do
  bash scripts/check-release-version.sh "$version"
done
for version in 0.1.0 v1.2 v1.2.3.4 v01.2.3 v1.2.3- v1.2.3-alpha..1 v1.2.3-01 v1.2.3+build "v1.2.3 "; do
  if bash scripts/check-release-version.sh "$version" 2>/dev/null; then
    echo "FAIL: release version check accepted $version" >&2
    exit 1
  fi
done
echo "PASS: release version check"
echo "PASS: workflow repository validation"
