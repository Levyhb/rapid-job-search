from unittest.mock import Mock

import httpcore
import httpx
import pytest

from app.collectors.network import (
    PublicHTTPTransport,
    PublicNetworkBackend,
    UnsafeTarget,
    validate_target,
)
from app.collectors.portals import collect_company


@pytest.mark.parametrize("host", [
    "127.0.0.1", "10.0.0.1", "169.254.169.254", "0.0.0.0", "224.0.0.1",
    "[::1]", "[::]", "[fd00::1]", "[fe80::1]", "[::ffff:127.0.0.1]",
    "[64:ff9b::7f00:1]", "[2002:7f00:1::1]",
])
def test_private_literal_is_rejected_before_http(host):
    handler = Mock()
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = collect_company(
            {"nome": "Test", "url": f"http://{host}"}, lambda item: None, client=client
        )
    assert report.reason_code == "unsafe_target"
    handler.assert_not_called()


@pytest.mark.parametrize("url", [
    "http://public.example:6379", "ftp://public.example", "https://user:pass@public.example",
    "http://[fe80::1%25eth0]",
])
def test_invalid_protocol_port_or_credentials_are_rejected(url):
    with pytest.raises(UnsafeTarget):
        validate_target(url)


def records(*addresses):
    return [(2, 1, 6, "", (address, 443)) for address in addresses]


@pytest.mark.parametrize("addresses", [
    ("127.0.0.1",), ("10.0.0.1",), ("93.184.216.34", "192.168.1.1"),
    ("::ffff:127.0.0.1",), (),
])
def test_nonpublic_or_mixed_dns_never_connects(monkeypatch, addresses):
    monkeypatch.setattr("socket.getaddrinfo", lambda *a, **kw: records(*addresses))
    connect = Mock()
    monkeypatch.setattr(httpcore.SyncBackend, "connect_tcp", connect)
    with pytest.raises(UnsafeTarget):
        PublicNetworkBackend().connect_tcp("portal.example", 443)
    connect.assert_not_called()


def test_connection_pins_validated_ip_without_resolving_hostname_again(monkeypatch):
    resolver = Mock(side_effect=[records("93.184.216.34"), records("127.0.0.1")])
    monkeypatch.setattr("socket.getaddrinfo", resolver)
    connect = Mock(return_value=object())
    monkeypatch.setattr(httpcore.SyncBackend, "connect_tcp", connect)
    PublicNetworkBackend().connect_tcp("portal.example", 443, timeout=3)
    assert connect.call_args.args[:2] == ("93.184.216.34", 443)
    assert resolver.call_count == 1
    with pytest.raises(UnsafeTarget):
        PublicNetworkBackend().connect_tcp("portal.example", 443)
    assert connect.call_count == 1


def test_dns_failure_is_closed(monkeypatch):
    import socket

    def failed(*args, **kwargs):
        raise socket.gaierror("offline")

    monkeypatch.setattr(socket, "getaddrinfo", failed)
    with pytest.raises(httpcore.ConnectError):
        PublicNetworkBackend().connect_tcp("portal.example", 443)


def test_redirect_is_validated_even_if_injected_client_follows_redirects():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(302, headers={"Location": "http://127.0.0.1/admin"})

    with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
        report = collect_company(
            {"nome": "Test", "url": "https://portal.example"}, lambda job: None, client=client
        )
    assert len(calls) == 1
    assert report.reason_code == "unsafe_target"


def test_public_dns_keeps_host_and_tls_server_name(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", lambda *a, **kw: records("93.184.216.34"))
    stream = httpcore.MockStream([b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok"])
    tls = Mock(return_value=stream)
    monkeypatch.setattr(stream, "start_tls", tls)
    connect = Mock(return_value=stream)
    monkeypatch.setattr(httpcore.SyncBackend, "connect_tcp", connect)
    with httpx.Client(transport=PublicHTTPTransport(), trust_env=False) as client:
        response = client.get("https://portal.example/")
    assert response.text == "ok"
    assert connect.call_args.args[0] == "93.184.216.34"
    assert tls.call_args.kwargs["server_hostname"] == "portal.example"
    assert tls.call_args.args[0].check_hostname


def test_redirect_loop_is_bounded():
    handler = Mock(return_value=httpx.Response(302, headers={"Location": "/again"}))
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = collect_company(
            {"nome": "Test", "url": "https://portal.example"}, lambda item: None, client=client
        )
    assert handler.call_count == 6
    assert report.reason_code == "redirect_limit"
