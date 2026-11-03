"""Transporte público: DNS validado na conexão, sem proxy ou segunda resolução."""

import ipaddress
import socket
import ssl
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar
from threading import BoundedSemaphore

import certifi
import httpcore
import httpx

NETWORK_DEADLINE = ContextVar("portal_network_deadline", default=None)
_DNS_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="portal-dns")
_DNS_SLOTS = BoundedSemaphore(2)


def time_left(timeout):
    deadline = NETWORK_DEADLINE.get()
    if deadline is None:
        return timeout
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise httpcore.ReadTimeout("Orçamento total de coleta esgotado.")
    return min(timeout, remaining) if timeout is not None else remaining


@contextmanager
def request_budget(deadline):
    token = NETWORK_DEADLINE.set(deadline)
    try:
        yield
    finally:
        NETWORK_DEADLINE.reset(token)


def resolve(host, port, timeout):
    # O resolvedor do SO não aceita timeout. Limitamos a espera e o número
    # de resoluções em segundo plano; uma chamada lenta nunca gera fila infinita.
    if not _DNS_SLOTS.acquire(timeout=time_left(timeout)):
        raise httpcore.ConnectTimeout("Resolvedor ocupado.")
    try:
        future = _DNS_POOL.submit(socket.getaddrinfo, host, port, type=socket.SOCK_STREAM)
    except BaseException:
        _DNS_SLOTS.release()
        raise
    future.add_done_callback(lambda _: _DNS_SLOTS.release())
    try:
        return future.result(timeout=time_left(timeout))
    except TimeoutError as error:
        future.cancel()
        raise httpcore.ConnectTimeout("Tempo de resolução esgotado.") from error


class BudgetStream(httpcore.NetworkStream):
    def __init__(self, stream):
        self.stream = stream

    def read(self, max_bytes, timeout=None):
        result = self.stream.read(max_bytes, timeout=time_left(timeout))
        time_left(timeout)
        return result

    def write(self, buffer, timeout=None):
        self.stream.write(buffer, timeout=time_left(timeout))
        time_left(timeout)

    def start_tls(self, ssl_context, server_hostname=None, timeout=None):
        stream = self.stream.start_tls(
            ssl_context, server_hostname=server_hostname, timeout=time_left(timeout)
        )
        return BudgetStream(stream)

    def get_extra_info(self, info):
        return self.stream.get_extra_info(info)

    def close(self):
        self.stream.close()


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
    try:
        url = httpx.URL(value)
    except httpx.InvalidURL as error:
        raise UnsafeTarget("URL de destino inválida.") from error
    if (
        url.scheme not in {"http", "https"}
        or not url.host
        or url.username
        or url.password
        or "%" in url.host
        or (url.port if url.port is not None else (443 if url.scheme == "https" else 80))
        not in {80, 443}
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
            records = resolve(host, port, timeout if timeout is not None else 25)
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
                return BudgetStream(super().connect_tcp(
                    address, port, time_left(timeout), local_address, socket_options
                ))
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
