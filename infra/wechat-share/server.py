#!/usr/bin/env python3
"""Small WeChat JS-SDK signature service for qinzy.tech."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import boto3


APP_ID = os.environ.get("WECHAT_APP_ID", "wxbd83f6ed93c8184e")
APP_SECRET_PARAMETER = os.environ.get(
    "WECHAT_APP_SECRET_PARAMETER", "/qinzy/wechat/app-secret"
)
AWS_REGION = os.environ.get("AWS_REGION", "ap-southeast-1")
PORT = int(os.environ.get("PORT", "8080"))
ALLOWED_HOSTS = {"qinzy.tech", "www.qinzy.tech"}
ALLOWED_ORIGINS = {"https://qinzy.tech", "https://www.qinzy.tech"}

_ssm = boto3.client("ssm", region_name=AWS_REGION)
_cache: dict[str, object] = {}
_cache_lock = threading.Lock()


class WeChatAPIError(RuntimeError):
    pass


def _fetch_json(url: str) -> dict[str, object]:
    request = urllib.request.Request(url, headers={"User-Agent": "qinzy-wechat-share/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise WeChatAPIError("WeChat API request failed") from exc

    error_code = int(payload.get("errcode", 0) or 0)
    if error_code:
        error_message = str(payload.get("errmsg", "unknown WeChat API error"))
        raise WeChatAPIError(f"WeChat API error {error_code}: {error_message}")
    return payload


def _app_secret() -> str:
    cached = _cache.get("app_secret")
    if isinstance(cached, str):
        return cached

    response = _ssm.get_parameter(Name=APP_SECRET_PARAMETER, WithDecryption=True)
    value = response["Parameter"]["Value"].strip()
    if not value or value == "NOT_CONFIGURED":
        raise WeChatAPIError("WeChat AppSecret is not configured")
    _cache["app_secret"] = value
    return value


def _jsapi_ticket() -> str:
    now = time.time()
    cached_ticket = _cache.get("ticket")
    ticket_expires_at = float(_cache.get("ticket_expires_at", 0))
    if isinstance(cached_ticket, str) and ticket_expires_at > now + 120:
        return cached_ticket

    with _cache_lock:
        now = time.time()
        cached_ticket = _cache.get("ticket")
        ticket_expires_at = float(_cache.get("ticket_expires_at", 0))
        if isinstance(cached_ticket, str) and ticket_expires_at > now + 120:
            return cached_ticket

        access_token = _cache.get("access_token")
        token_expires_at = float(_cache.get("token_expires_at", 0))
        if not isinstance(access_token, str) or token_expires_at <= now + 120:
            token_url = "https://api.weixin.qq.com/cgi-bin/token?" + urllib.parse.urlencode(
                {
                    "grant_type": "client_credential",
                    "appid": APP_ID,
                    "secret": _app_secret(),
                }
            )
            token_payload = _fetch_json(token_url)
            access_token = str(token_payload["access_token"])
            token_lifetime = int(token_payload.get("expires_in", 7200))
            _cache["access_token"] = access_token
            _cache["token_expires_at"] = now + token_lifetime

        ticket_url = "https://api.weixin.qq.com/cgi-bin/ticket/getticket?" + urllib.parse.urlencode(
            {"access_token": access_token, "type": "jsapi"}
        )
        ticket_payload = _fetch_json(ticket_url)
        ticket = str(ticket_payload["ticket"])
        ticket_lifetime = int(ticket_payload.get("expires_in", 7200))
        _cache["ticket"] = ticket
        _cache["ticket_expires_at"] = now + ticket_lifetime
        return ticket


def _signature(page_url: str) -> dict[str, object]:
    parsed = urllib.parse.urlsplit(page_url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("Only HTTPS qinzy.tech URLs can be signed")

    clean_url = urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path or "/", parsed.query, "")
    )
    timestamp = int(time.time())
    nonce = secrets.token_hex(12)
    signing_text = (
        f"jsapi_ticket={_jsapi_ticket()}&noncestr={nonce}"
        f"&timestamp={timestamp}&url={clean_url}"
    )
    signature = hashlib.sha1(signing_text.encode("utf-8")).hexdigest()
    return {
        "appId": APP_ID,
        "timestamp": timestamp,
        "nonceStr": nonce,
        "signature": signature,
        "url": clean_url,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "qinzy-wechat-share/1.0"

    def _cors_origin(self) -> str | None:
        origin = self.headers.get("Origin")
        return origin if origin in ALLOWED_ORIGINS else None

    def _send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        cors_origin = self._cors_origin()
        if cors_origin:
            self.send_header("Access-Control-Allow-Origin", cors_origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        cors_origin = self._cors_origin()
        if cors_origin:
            self.send_header("Access-Control-Allow-Origin", cors_origin)
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", "86400")
            self.send_header("Vary", "Origin")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/health":
            self._send_json(200, {"ok": True, "appId": APP_ID})
            return

        if parsed.path != "/sign":
            self._send_json(404, {"error": "not_found"})
            return

        origin = self.headers.get("Origin")
        if origin and origin not in ALLOWED_ORIGINS:
            self._send_json(403, {"error": "origin_not_allowed"})
            return

        query = urllib.parse.parse_qs(parsed.query)
        page_url = query.get("url", [""])[0]
        if not page_url:
            self._send_json(400, {"error": "missing_url"})
            return

        try:
            payload = _signature(page_url)
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
        except WeChatAPIError as exc:
            self.log_error("%s", exc)
            self._send_json(503, {"error": str(exc)})
        except Exception as exc:
            self.log_error("Unexpected signing error: %s", exc)
            self._send_json(500, {"error": "signing_failed"})
        else:
            self._send_json(200, payload)

    def log_message(self, format_string: str, *args: object) -> None:
        print(f"{self.address_string()} - {format_string % args}", flush=True)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
