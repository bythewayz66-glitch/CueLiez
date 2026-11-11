import json
import sys
import types

import pytest

from cueliez import cli


def _install_module(monkeypatch, name, handler):
    mod = types.ModuleType(name)
    mod.entry = handler
    monkeypatch.setitem(sys.modules, name, mod)
    monkeypatch.setitem(cli.SUBCOMMANDS, "fakecmd", f"{name}:entry")


def test_subcommand_receives_remaining_args_and_return_code(monkeypatch):
    seen = {}

    def handler(argv):
        seen["argv"] = argv
        return 7

    _install_module(monkeypatch, "cueliez_test_sub_ok", handler)
    assert cli.run_cli(["fakecmd", "--flag", "value"]) == 7
    assert seen["argv"] == ["--flag", "value"]


def test_subcommand_error_with_code_is_reported_as_json_exit_2(monkeypatch, capsys):
    class CodedError(Exception):
        code = "fake_failure"

    def handler(argv):
        raise CodedError("boom")

    _install_module(monkeypatch, "cueliez_test_sub_err", handler)
    assert cli.run_cli(["fakecmd"]) == 2
    payload = json.loads(capsys.readouterr().err)
    assert payload["ok"] is False
    assert payload["error_code"] == "fake_failure"
    assert payload["error"] == "boom"


def test_missing_subcommand_module_fails_with_exit_2(monkeypatch, capsys):
    monkeypatch.setitem(cli.SUBCOMMANDS, "fakecmd", "cueliez.does_not_exist:entry")
    assert cli.run_cli(["fakecmd"]) == 2
    assert json.loads(capsys.readouterr().err)["ok"] is False


def test_existing_file_with_subcommand_name_is_still_a_transcript(monkeypatch, tmp_path):
    called = []
    _install_module(monkeypatch, "cueliez_test_sub_shadow", lambda argv: called.append(argv) or 0)
    transcript = tmp_path / "fakecmd"
    transcript.write_text(json.dumps([{"role": "subject", "text": "I went to the store."}]), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert cli.run_cli(["fakecmd", "--no-seal"]) == 0
    assert called == []


def test_unregistered_name_falls_through_to_legacy_parser():
    with pytest.raises(SystemExit):
        cli.run_cli(["--definitely-not-a-flag"])


def test_help_lists_registered_subcommands(monkeypatch):
    monkeypatch.setitem(cli.SUBCOMMANDS, "fakecmd", "x:y")
    assert "fakecmd" in cli.build_arg_parser().format_help()
