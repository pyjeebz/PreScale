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
