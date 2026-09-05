import hashlib
import json
import os
from urllib.parse import urljoin

import requests

from .security import decrypt_secret


class ProviderResult:
    def __init__(self, *, code="", description="", pending=False, success=False, response=None, raw_text=""):
        self.code = str(code or "")
        self.description = str(description or "")
        self.pending = pending
        self.success = success
        self.response = response if isinstance(response, dict) else {"raw": response}
        self.raw_text = raw_text


class ProviderClient:
    def __init__(self, connection):
        self.connection = connection

    def _url(self, path):
        base = (self.connection.base_url or "").rstrip("/") + "/"
        return urljoin(base, (path or "").lstrip("/"))

    @staticmethod
    def sanaacash_token(password, transid, username, mobile):
        hashed = hashlib.md5(password.encode("utf-8")).hexdigest()
        return hashlib.md5((hashed + str(transid) + username + str(mobile)).encode("utf-8")).hexdigest()

    @staticmethod
    def _render(value, context):
        if not isinstance(value, str):
            return value
        result = value
        for key, val in context.items():
            result = result.replace("{{" + key + "}}", str(val if val is not None else ""))
        return result

    def _params(self, link, transaction):
        context = dict(transaction.payload or {})
        context.update({
            "transaction.id": str(transaction.id),
            "transid": transaction.provider_transaction_id,
            "mobile": transaction.mobile,
            "transaction.mobile": transaction.mobile,
        })
        params = {k: self._render(v, context) for k, v in (link.fixed_params or {}).items()}
        for target, source in (link.field_map or {}).items():
            if isinstance(source, str) and source.startswith("{{") and source.endswith("}}"):
                params[target] = self._render(source, context)
            else:
                params[target] = context.get(source, source)
        if self.connection.connection_type == "sanaacash":
            params.setdefault("userid", self.connection.userid)
            params.setdefault("mobile", transaction.mobile)
            params.setdefault("transid", transaction.provider_transaction_id)
            params.setdefault("token", self.sanaacash_token(self.connection.get_password(), transaction.provider_transaction_id, self.connection.username, transaction.mobile))
            if transaction.webhook_secret_encrypted:
                params.setdefault("backpass", decrypt_secret(transaction.webhook_secret_encrypted))
            webhook_base = os.getenv("SERVICES_WEBHOOK_BASE_URL", "https://shopik.alattab.site").rstrip("/")
            params.setdefault("backurl", webhook_base + "/api/v2/services/webhook/sanaacash/")
        return params, context

    def call(self, link, transaction, *, status_check=False):
        path = link.status_path_template if status_check and link.status_path_template else link.path_template
        params, context = self._params(link, transaction)
        if status_check and link.status_params:
            for target, value in link.status_params.items():
                params[target] = self._render(value, context)
        headers = dict(self.connection.headers or {})
        headers.update(link.headers or {})
        timeout = max(1, int(self.connection.timeout_seconds or 20))
        try:
            if link.http_method == "POST":
                response = requests.post(self._url(path), params=params, headers=headers, timeout=timeout)
            elif link.http_method == "PUT":
                response = requests.put(self._url(path), params=params, headers=headers, timeout=timeout)
            else:
                response = requests.get(self._url(path), params=params, headers=headers, timeout=timeout)
            raw_text = response.text[:20000]
            try:
                data = response.json()
            except (ValueError, json.JSONDecodeError):
                data = {"http_status": response.status_code, "raw": raw_text}
            code = data.get("resultCode", response.status_code)
            desc = data.get("resultDesc", data.get("message", ""))
            success_codes = set(str(x) for x in (link.success_codes or ["0"]))
            pending_codes = set(str(x) for x in (link.pending_codes or ["-2"]))
            pending = str(code) in pending_codes or "under process" in str(desc).lower() or "under proccess" in str(desc).lower()
            success = str(code) in success_codes
            if status_check and data.get("isDone") == "1":
                success = True
                pending = False
            if status_check and data.get("isBan") == "1" and data.get("isDone") != "1":
                success = False
                pending = False
            return ProviderResult(code=code, description=desc, pending=pending, success=success, response=data, raw_text=raw_text)
        except requests.RequestException as exc:
            return ProviderResult(code="NETWORK", description=str(exc), success=False, pending=False, response={"error": str(exc)})
