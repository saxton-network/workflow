"""Read-only Git observation. No ref, worktree, or source mutations."""
import os
from pathlib import Path
import subprocess
from .contracts import Rejected


class GitObserver:
    def __init__(self, repository: Path):
        self.repository = Path(repository)

    def observe(self) -> tuple[str, str]:
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env["GIT_GRAFT_FILE"] = os.devnull
        base = ["git", "--no-replace-objects", "-c", "core.commitGraph=false",
                "-c", "advice.graftFileDeprecated=false", "-C", str(self.repository)]
        try:
            def run(*args):
                return subprocess.run(base + list(args), env=env, check=True,
                                      capture_output=True, text=True, timeout=5).stdout.strip()
            return run("rev-parse", "--verify", "HEAD^{commit}"), run("branch", "--show-current")
        except (OSError, subprocess.SubprocessError) as exc:
            raise Rejected("Git state UNKNOWN; execution blocked") from exc

    def check(self, plan: dict) -> None:
        sha, branch = self.observe()
        if (sha, branch) != (plan["source_sha"], plan["source_branch"]):
            raise Rejected("Git divergence; execution blocked")
