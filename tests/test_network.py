"""Network URL helper tests."""

from __future__ import annotations

from emberforge.network import format_serve_urls, local_client_host


def test_local_client_host_for_wildcard_bind():
    assert local_client_host("0.0.0.0") == "127.0.0.1"
    assert local_client_host("::") == "127.0.0.1"
    assert local_client_host("192.168.1.10") == "192.168.1.10"


def test_format_serve_urls_includes_local_and_lan_placeholder():
    lines = format_serve_urls("0.0.0.0", 8000)
    assert any("127.0.0.1:8000" in line for line in lines)
    assert any("LAN" in line for line in lines)


def test_format_serve_urls_localhost_only():
    lines = format_serve_urls("127.0.0.1", 8000)
    assert len(lines) == 1
    assert "127.0.0.1:8000" in lines[0]