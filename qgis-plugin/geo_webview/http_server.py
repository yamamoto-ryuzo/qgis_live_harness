# -*- coding: utf-8 -*-
"""Shared lightweight HTTP utilities for QMapPermalink.

This module provides minimal request/response helpers used by the
plugin's internal socket-based HTTP servers. Keeping these utilities
centralized makes future extensions (middleware, logging, CORS, etc.)
easier.
"""


def read_http_request(conn, max_size=8192):
    """Read raw HTTP request bytes from a connected socket.

    Args:
        conn: socket-like object with recv
        max_size: maximum bytes to read (prevents unbounded memory use)

    Returns:
        bytes: raw request bytes (may be empty on error/timeout)
    """
    try:
        data = b''
        while b'\r\n\r\n' not in data and len(data) < max_size:
            chunk = conn.recv(1024)
            if not chunk:
                break
            data += chunk
        return data
    except Exception:
        return b''


def send_http_response(conn, status_code, reason, body, content_type="text/plain; charset=utf-8"):
    """Send a minimal HTTP response (text or bytes).

    Args:
        conn: socket-like object with sendall
        status_code: integer HTTP status code
        reason: status reason phrase
        body: str or bytes body
        content_type: Content-Type header value
    """
    try:
        if isinstance(body, str):
            body_bytes = body.encode('utf-8')
        else:
            body_bytes = body or b''

        header_lines = [
            f"HTTP/1.1 {status_code} {reason}",
            f"Content-Length: {len(body_bytes)}",
            f"Content-Type: {content_type}",
            "Access-Control-Allow-Origin: *",
            "Connection: close",
            "",
            "",
        ]
        header = "\r\n".join(header_lines).encode('utf-8')
        conn.sendall(header + body_bytes)
    except Exception:
        try:
            conn.close()
        except Exception:  # nosec B110  # 設計上の許容
            pass


def send_binary_response(conn, status_code, reason, data, content_type):
    """Send a binary HTTP response (images, etc.)."""
    try:
        header_lines = [
            f"HTTP/1.1 {status_code} {reason}",
            f"Content-Length: {len(data)}",
            f"Content-Type: {content_type}",
            "Access-Control-Allow-Origin: *",
            "Connection: close",
            "",
            "",
        ]
        header = "\r\n".join(header_lines).encode('utf-8')
        conn.sendall(header + data)
    except Exception:
        try:
            conn.close()
        except Exception:  # nosec B110  # 設計上の許容
            pass


def send_options_response(conn):
    """CORS + Private Network Access プリフライト(OPTIONS)応答。

    ホスト版エンジン(https://*.github.io)から http://localhost への
    fetch は Chrome の Private Network Access 対象となり、プリフライト
    応答に Access-Control-Allow-Private-Network が必要。
    """
    try:
        header_lines = [
            "HTTP/1.1 204 No Content",
            "Access-Control-Allow-Origin: *",
            "Access-Control-Allow-Methods: GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers: *",
            "Access-Control-Allow-Private-Network: true",
            "Access-Control-Max-Age: 600",
            "Content-Length: 0",
            "Connection: close",
            "",
            "",
        ]
        header = "\r\n".join(header_lines).encode('utf-8')
        conn.sendall(header)
    except Exception:
        try:
            conn.close()
        except Exception:  # nosec B110  # 設計上の許容
            pass


def send_head_response(conn, status_code, reason, content_length, content_type):
    """Send headers only for a HEAD request (no body)."""
    try:
        header_lines = [
            f"HTTP/1.1 {status_code} {reason}",
            f"Content-Length: {int(content_length)}",
            f"Content-Type: {content_type}",
            "Access-Control-Allow-Origin: *",
            "Connection: close",
            "",
            "",
        ]
        header = "\r\n".join(header_lines).encode('utf-8')
        conn.sendall(header)
    except Exception:
        try:
            conn.close()
        except Exception:  # nosec B110  # 設計上の許容
            pass
