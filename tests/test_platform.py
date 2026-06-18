"""Runtime platform detection tests."""

from __future__ import annotations

from emberforge.runtime.platform import macos_say_available, running_in_container, runtime_platform


def test_runtime_platform_is_non_empty():
    assert runtime_platform()


def test_macos_say_available_on_darwin_when_say_exists(monkeypatch):
    monkeypatch.setattr("emberforge.runtime.platform.sys.platform", "darwin")
    monkeypatch.setattr(
        "emberforge.runtime.platform.shutil.which",
        lambda cmd: "/usr/bin/say" if cmd == "say" else None,
    )
    assert macos_say_available() is True


def test_macos_say_unavailable_on_linux(monkeypatch):
    monkeypatch.setattr("emberforge.runtime.platform.sys.platform", "linux")
    monkeypatch.setattr("emberforge.runtime.platform.shutil.which", lambda cmd: None)
    assert macos_say_available() is False


def test_running_in_container_detects_marker(monkeypatch):
    def fake_path(path: str):
        class _P:
            def is_file(self) -> bool:
                return path in {"/.dockerenv", "/run/.containerenv"}

        return _P()

    monkeypatch.setattr("emberforge.runtime.platform.Path", fake_path)
    assert running_in_container() is True


def test_running_in_container_false_without_marker(monkeypatch):
    def fake_path(path: str):
        class _P:
            def is_file(self) -> bool:
                return False

        return _P()

    monkeypatch.setattr("emberforge.runtime.platform.Path", fake_path)
    assert running_in_container() is False