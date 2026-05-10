"""Elasticsearch / OpenSearch client wrapper."""

from __future__ import annotations

import ssl
from dataclasses import dataclass, field
from typing import Any

import urllib3


@dataclass
class Connection:
    host: str
    api_key: str | None = None
    username: str | None = None
    password: str | None = None
    verify_certs: bool = True

    _pool: urllib3.PoolManager | None = field(default=None, init=False, repr=False, compare=False)

    def _session(self) -> urllib3.PoolManager:
        if self._pool is not None:
            return self._pool
        timeout = urllib3.Timeout(connect=10, read=30)
        if not self.verify_certs:
            self._pool = urllib3.PoolManager(
                cert_reqs=ssl.CERT_NONE,
                headers=self._headers(),
                timeout=timeout,
            )
        else:
            self._pool = urllib3.PoolManager(headers=self._headers(), timeout=timeout)
        return self._pool

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"ApiKey {self.api_key}"
        elif self.username and self.password:
            import base64

            cred = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            headers["Authorization"] = f"Basic {cred}"
        return headers

    def get(self, path: str) -> Any:
        url = f"{self.host.rstrip('/')}/{path.lstrip('/')}"
        http = self._session()
        resp = http.request("GET", url)
        if resp.status >= 400:
            raise ConnectionError(f"GET {path} returned {resp.status}: {resp.data.decode()}")
        import json

        return json.loads(resp.data.decode())

    def request(
        self, method: str, path: str, body: Any = None, headers: dict[str, str] | None = None
    ) -> Any:
        """Generic HTTP request. body can be dict (auto-serialized) or str."""
        import json as _json

        url = f"{self.host.rstrip('/')}/{path.lstrip('/')}"
        http = self._session()

        kwargs: dict[str, Any] = {}
        if body is not None:
            if isinstance(body, (dict, list)):
                kwargs["body"] = _json.dumps(body).encode()
            else:
                kwargs["body"] = body.encode() if isinstance(body, str) else body
        if headers:
            merged = {**self._headers(), **headers}
            kwargs["headers"] = merged

        resp = http.request(method, url, **kwargs)
        if resp.status >= 400:
            raise ConnectionError(f"{method} {path} returned {resp.status}: {resp.data.decode()}")
        if resp.data:
            try:
                return _json.loads(resp.data.decode())
            except Exception:
                return resp.data.decode()
        return None

    def test_connection(self) -> dict:
        return self.get("/")
