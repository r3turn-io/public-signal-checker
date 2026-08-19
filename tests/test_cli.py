from public_signal_checker.cli import main


def test_main_returns_success(capsys):
    result = main()

    captured = capsys.readouterr()

    assert result == 0
    assert "R3TURN Public Signal Checker v0.1" in captured.out
    assert "pre-release" in captured.out
