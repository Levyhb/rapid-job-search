"""Transporte público: DNS validado na conexão, sem proxy ou segunda resolução."""

import ipaddress
import socket
import ssl
from contextlib import contextmanager

import certifi
import httpcore
import httpx


class UnsafeTarget(httpx.TransportError):
    pass


def public_address(value):
    address = ipaddress.ip_address(value)
    if not address.is_global or address.is_multicast:
        return False
    if isinstance(address, ipaddress.IPv6Address):
        # Não permitir túneis/tradução que escondam outro destino IPv4.
        if address.ipv4_mapped or address.sixtofour or address.teredo:
            return False
        if address in ipaddress.ip_network("64:ff9b::/96"):
            return False
    return True


def validate_target(value):
    url = httpx.URL(value)
    if (
        url.scheme not in {"http", "https"}
        or not url.host
        or url.username
        or url.password
        or "%" in url.host
        or (url.port or (443 if url.scheme == "https" else 80)) not in {80, 443}
    ):
        raise UnsafeTarget("Destino HTTP não permitido pela política de coleta.")
    try:
        address = ipaddress.ip_address(url.host)
    except ValueError:
        return url
    if not public_address(address):
        raise UnsafeTarget("O coletor aceita somente endereços públicos.")
    return url


class PublicNetworkBackend(httpcore.SyncBackend):
    def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        if port not in {80, 443} or "%" in host:
            raise UnsafeTarget("Destino de rede não permitido.")
        try:
            records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except OSError as error:
            raise httpcore.ConnectError("Não foi possível resolver o portal.") from error
        addresses = list(dict.fromkeys(record[4][0] for record in records))
        if not addresses or not all(public_address(address) for address in addresses):
            raise UnsafeTarget("A resolução do portal contém endereço não público.")
        # A conexão recebe apenas o IP canônico validado. HTTP Host e TLS SNI
        # continuam sendo o hostname original no httpcore; não desativar TLS.
        last_error = None
        for address in addresses:
            try:
                return super().connect_tcp(
                    address, port, timeout, local_address, socket_options
                )
            except (httpcore.ConnectError, httpcore.ConnectTimeout) as error:
                last_error = error
        raise last_error


@contextmanager
def mapped_errors():
    try:
        yield
    except (
        httpcore.NetworkError, httpcore.TimeoutException,
        httpcore.ProtocolError, httpcore.UnsupportedProtocol,
    ) as error:
        mapped = getattr(httpx, type(error).__name__, httpx.TransportError)
        raise mapped("Falha de transporte ao consultar o portal.") from error


class CoreResponseStream(httpx.SyncByteStream):
    def __init__(self, stream):
        self.stream = stream

    def __iter__(self):
        with mapped_errors():
            yield from self.stream

    def close(self):
        with mapped_errors():
            self.stream.close()


class PublicHTTPTransport(httpx.BaseTransport):
    """Adaptador das APIs públicas HTTPX/httpcore, com backend de rede restrito."""

    def __init__(self):
        self.pool = httpcore.ConnectionPool(
            ssl_context=ssl.create_default_context(cafile=certifi.where()),
            network_backend=PublicNetworkBackend(),
            max_connections=4,
            max_keepalive_connections=2,
        )

    def handle_request(self, request):
        validate_target(request.url)
        core_request = httpcore.Request(
            method=request.method,
            url=httpcore.URL(
                scheme=request.url.raw_scheme, host=request.url.raw_host,
                port=request.url.port, target=request.url.raw_path,
            ),
            headers=request.headers.raw,
            content=request.stream,
            extensions=request.extensions,
        )
        with mapped_errors():
            response = self.pool.handle_request(core_request)
        return httpx.Response(
            response.status, headers=response.headers,
            stream=CoreResponseStream(response.stream), extensions=response.extensions,
        )

    def close(self):
        self.pool.close()
