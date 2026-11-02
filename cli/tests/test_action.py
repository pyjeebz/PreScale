"""The GitHub Action's metadata (action/action.yml) loads on GitHub."""

from pathlib import Path

import yaml

ACTION = Path(__file__).resolve().parents[2] / "action" / "action.yml"


def test_metadata_has_no_expressions_outside_defaults_and_steps():
    # GitHub evaluates ${{ }} anywhere in action.yml and refuses to load the
    # action when one sits in a description (only github/inputs contexts work).
    action = yaml.safe_load(ACTION.read_text())
    assert "${{" not in action["description"]
    for name, spec in action["inputs"].items():
        assert "${{" not in spec["description"], name
        assert "secrets." not in str(spec.get("default", "")), name


def test_capacity_check_passes_stale_and_each_allow_writes_host(tmp_path):
    import os
    import subprocess

    stub = tmp_path / "prescale"
    stub.write_text('#!/bin/sh\nfor a in "$@"; do printf "[%s]" "$a"; done\n')
    stub.chmod(0o755)
    action = yaml.safe_load(ACTION.read_text())
    script = next(s for s in action["runs"]["steps"] if s.get("name") == "Capacity check")["run"]
    env = {"PATH": f"{tmp_path}:{os.environ['PATH']}", "RUNNER_TEMP": "/tmp",
           "INPUT_MAX_USERS": "100", "INPUT_STAGE_SECONDS": "5", "INPUT_FAIL": "false",
           "INPUT_COMMENT": "true", "INPUT_ALLOW_PRODUCTION": "false",
           "INPUT_HOST_PERMISSION": "false", "INPUT_APP": "", "INPUT_APP_TIMEOUT": "600",
           "INPUT_URL": "", "INPUT_STALE": "fail",
           "INPUT_ALLOW_WRITES": "staging.myapp.com\n  qa.myapp.com  \n\n"}
    def run(**inputs):
        return subprocess.run(["bash", "-eo", "pipefail", "-c", script], env={**env, **inputs},
                              capture_output=True, text=True).stdout

    assert run().endswith("[--stale][fail][--allow-writes][staging.myapp.com]"
                          "[--allow-writes][qa.myapp.com]")
    # the default passes no new flag, so a pinned older prescale-version keeps working
    assert "--stale" not in run(INPUT_STALE="warn", INPUT_ALLOW_WRITES="")
    assert "--stale" not in run(INPUT_STALE="", INPUT_ALLOW_WRITES="")
    assert run(INPUT_STALE="Fail", INPUT_ALLOW_WRITES="a.com, b.com").endswith(
        "[--stale][fail][--allow-writes][a.com][--allow-writes][b.com]")
