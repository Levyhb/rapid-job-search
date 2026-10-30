import gzip
import time

import httpcore
import httpx
import pytest

from app.collectors import portals
from app.collectors.network import BudgetStream, request_budget
from app.collectors.portals import SourceProblem, _read, collect_company


class Chunks(httpx.SyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks
        self.consumed = 0
        self.closed = False

    def __iter__(self):
        for chunk in self.chunks:
            self.consumed += 1
            yield chunk

    def close(self):
        self.closed = True


def read(stream, headers=None):
    with httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, stream=stream, headers=headers)
    )) as client:
        return _read(client, "https://portal.example", time.monotonic() + 180)


def test_large_chunked_body_stops_before_consuming_full_stream(monkeypatch):
    monkeypatch.setattr(portals, "MAX_RESPONSE_BYTES", 65536)
    stream = Chunks([b"a" * 65536 for _ in range(5)])
    with pytest.raises(SourceProblem) as caught:
        read(stream)
    assert caught.value.code == "response_limit"
    assert stream.consumed == 2
    assert stream.closed


def test_content_length_rejects_before_reading_body(monkeypatch):
    monkeypatch.setattr(portals, "MAX_RESPONSE_BYTES", 10)
    stream = Chunks([b"body"])
    with pytest.raises(SourceProblem) as caught:
        read(stream, {"Content-Length": "100"})
    assert caught.value.code == "response_limit"
    assert stream.consumed == 0
    assert stream.closed


def test_compressed_expansion_is_bounded(monkeypatch):
    monkeypatch.setattr(portals, "MAX_RESPONSE_BYTES", 1024)
    compressed = gzip.compress(b"a" * 100000)
    assert len(compressed) < 1024
    stream = Chunks([compressed])
    with pytest.raises(SourceProblem) as caught:
        read(stream, {"Content-Encoding": "gzip"})
    assert caught.value.code == "response_limit"
    assert stream.closed


def test_small_gzip_is_decoded_once_and_headers_match():
    content = b'{"jobs": []}'
    compressed = gzip.compress(content)
    response = read(Chunks([compressed]), {
        "Content-Encoding": "gzip", "Content-Length": str(len(compressed)),
    })
    assert response.json() == {"jobs": []}
    assert "content-encoding" not in response.headers
    assert int(response.headers["content-length"]) == len(content)


@pytest.mark.parametrize("body", [b"not gzip", gzip.compress(b"hello")[:-4]])
def test_invalid_or_truncated_compression_fails_closed(body):
    with pytest.raises(httpx.DecodingError):
        read(Chunks([body]), {"Content-Encoding": "gzip"})


def test_unsupported_encoding_is_rejected_before_read():
    stream = Chunks([b"compressed"])
    with pytest.raises(SourceProblem) as caught:
        read(stream, {"Content-Encoding": "br"})
    assert caught.value.code == "response_encoding"
    assert stream.consumed == 0
    assert stream.closed


def test_slow_stream_consumes_total_budget_and_closes(monkeypatch):
    clock = [0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])

    def slow_chunks():
        clock[0] = 181
        yield b"body"
        yield b"never"

    stream = Chunks(slow_chunks())
    with httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, stream=stream)
    )) as client:
        report = collect_company(
            {"nome": "Test", "url": "https://portal.example"}, lambda job: None, client=client
        )
    assert report.reason_code == "collection_limit"
    assert stream.closed


def test_redirect_body_is_not_downloaded():
    stream = Chunks([b"large unused redirect body"])
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(302, headers={"Location": "/jobs"}, stream=stream)
        return httpx.Response(200, text="small")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        response = _read(client, "https://portal.example", time.monotonic() + 180)
    assert response.text == "small"
    assert stream.consumed == 0 and stream.closed
    assert all(request.headers["accept-encoding"] == "identity" for request in calls)


def test_socket_read_timeout_shrinks_with_total_budget(monkeypatch):
    from unittest.mock import Mock

    clock = [100]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    stream = Mock()
    stream.read.return_value = b"ok"
    wrapped = BudgetStream(stream)
    with request_budget(105):
        assert wrapped.read(100, timeout=25) == b"ok"
        assert stream.read.call_args.kwargs["timeout"] == 5
        clock[0] = 106
        with pytest.raises(httpcore.ReadTimeout):
            wrapped.read(100, timeout=25)
    assert stream.read.call_count == 1
