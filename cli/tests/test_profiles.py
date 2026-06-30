"""Tests for launch profiles."""

from click.testing import CliRunner

from prescale_cli.main import cli
from prescale_cli.profiles import PROFILES, lookup, scenario_block


def test_lookup_is_case_and_space_tolerant():
    assert lookup("product-hunt") is PROFILES["product-hunt"]
    assert lookup("  Product-Hunt ") is PROFILES["product-hunt"]
    assert lookup("nope") is None
    assert lookup("") is None


def test_profiles_have_sane_fields():
    for p in PROFILES.values():
        assert p.peak_users > 0
        assert p.think_time_s >= 0
        assert p.label


def test_scenario_block_around_the_peak():
    p = PROFILES["product-hunt"]  # peak 100
    assert scenario_block(p, 150)["would_survive"] is True
    assert scenario_block(p, 100)["would_survive"] is True
    assert scenario_block(p, 90)["would_survive"] is False
    assert scenario_block(p, 90)["label"] == p.label
    assert scenario_block(p, 90)["peak_users"] == 100


def test_profiles_command_lists_names():
    res = CliRunner().invoke(cli, ["profiles"])
    assert res.exit_code == 0
    for name in PROFILES:
        assert name in res.output
