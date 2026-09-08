import hashlib
import json
import os
import secrets
from urllib.parse import urljoin, urlparse

import requests
from django.conf import settings
from django.db import IntegrityError, transaction as db_transaction

from .security import decrypt_secret

DEFAULT_WEBHOOK_PATH = "/api/v2/services/webhook/sanaacash/"


class ProviderResult:
    def __init__(self, *, code="", description="", pending=False, success=False, ambiguous=False, response=None, raw_text=""):
        self.code = str(code or "")
        self.description = str(description or "")
        self.pending = pending
        self.success = success
        self.ambiguous = ambiguous
        self.response = response if isinstance(response, dict) else {"raw": response}
        self.raw_text = raw_text


class ProviderClient:
    def __init__(self, connection):
        self.connection = connection

    def _url(self, path):
        base = (self.connection.base_url or "").strip()
        parsed = urlparse(base)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("رابط المزود غير صالح.")
        if not settings.DEBUG and parsed.scheme != "https":
            raise ValueError("ربط المزود يجب أن يستخدم HTTPS في بيئة الإنتاج.")
        return urljoin(base.rstrip("/") + "/", (path or "").lstrip("/"))

    @staticmethod
    def sanaacash_token(password, transid, username, mobile):
        hashed = hashlib.md5((password or "").encode("utf-8")).hexdigest()
        return hashlib.md5((hashed + str(transid) + (username or "") + str(mobile or "")).encode("utf-8")).hexdigest()

    @staticmethod
    def new_numeric_transid(provider, *, request_kind="service", service_transaction=None):
        from services.models import ServiceRequestReference, ServiceTransaction
        for _ in range(256):
            value = secrets.randbelow(990_000_000) + 10_000
            if ServiceRequestReference.objects.filter(transid=value).exists():
                continue
            if ServiceTransaction.objects.filter(provider_transid=value).exists():
                continue
            if ServiceTransaction.objects.filter(provider_transaction_id=str(value)).exists():
                continue
            try:
                with db_transaction.atomic():
                    ref = ServiceRequestReference.objects.create(
                        transid=value, provider=provider, transaction=service_transaction, request_kind=request_kind
                    )
                    return ref.transid
            except IntegrityError:
                continue
        raise RuntimeError("تعذر إنشاء transid رقمي عشوائي فريد للمزود بعد عدة محاولات.")

    @staticmethod
    def normalize_digits(value):
        if value is None:
            return ""
        translation = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
        return str(value).translate(translation)

    @staticmethod
    def _render(value, context):
        if not isinstance(value, str):
            return value
        result = value
        for key, val in context.items():
            result = result.replace("{{" + key + "}}", str(val if val is not None else ""))
        return result

    def _params(self, link, transaction):
        provider_transid = getattr(transaction, "provider_transid", None)
        legacy_id = getattr(transaction, "provider_transaction_id", "")
        transid = str(provider_transid or legacy_id or "")
        context = dict(transaction.payload or {})
        context.update({
            "transaction.id": str(transaction.id), "transid": transid, "provider_transid": transid,
            "service.code": transaction.service.code, "service_id": transaction.service_id,
            "mobile": transaction.mobile, "transaction.mobile": transaction.mobile,
        })
        params = {k: self._render(v, context) for k, v in (link.fixed_params or {}).items()}
        for target, source in (link.field_map or {}).items():
            if isinstance(source, str) and source.startswith("{{") and source.endswith("}}"):
                params[target] = self._render(source, context)
            elif isinstance(source, str):
                params[target] = context.get(source, source)
            else:
                params[target] = source
        if self.connection.connection_type == "sanaacash":
            if not transid.isdigit() or not 10000 <= int(transid) <= 999_999_999:
                raise ValueError("transid يجب أن يكون رقمًا صحيحًا من 5 إلى 9 أرقام للمزود.")
            password = self.connection.get_password()
            if not self.connection.userid or not self.connection.username or not password:
                raise RuntimeError("بيانات اعتماد المزود غير مكتملة؛ أوقف التنفيذ بدل إرسال طلب ناقص.")
            params.setdefault("userid", self.connection.userid)
            params.setdefault("mobile", transaction.mobile or "0")
            params.setdefault("transid", transid)
            params.setdefault("token", self.sanaacash_token(password, transid, self.connection.username, transaction.mobile or "0"))
            if transaction.webhook_secret_encrypted:
                params.setdefault("backpass", decrypt_secret(transaction.webhook_secret_encrypted))
            webhook_base = os.getenv("SERVICES_WEBHOOK_BASE_URL", "https://shopik.alattab.site").rstrip("/")
            params.setdefault("backurl", webhook_base + DEFAULT_WEBHOOK_PATH)
        return params, context

    def _request(self, link, url, params, headers, timeout):
        method = str(link.http_method or "GET").upper()
        encoding = str(link.request_encoding or "query").lower()
        kwargs = {"headers": headers, "timeout": timeout}
        if method == "GET" or encoding == "query":
            kwargs["params"] = params
        elif encoding == "json":
            kwargs["json"] = params
        else:
            kwargs["data"] = params
        if method == "POST":
            return requests.post(url, **kwargs)
        if method == "PUT":
            return requests.put(url, **kwargs)
        return requests.get(url, **kwargs)

    @staticmethod
    def _decode(response):
        raw_text = response.text[:20000]
        try:
            data = response.json()
            parsed = True
        except (ValueError, json.JSONDecodeError):
            data = {"http_status": response.status_code, "raw": raw_text}
            parsed = False
        if isinstance(data, dict):
            code = data.get("resultCode", response.status_code)
            desc = data.get("resultDesc", data.get("message", ""))
        else:
            code, desc = response.status_code, ""
            data = {"raw": data}
        return data, raw_text, code, desc, parsed

    def check_balance(self):
        if self.connection.connection_type != "sanaacash":
            return ProviderResult(code="UNSUPPORTED", description="فحص رصيد المزود غير مهيأ لهذا النوع من الربط.")

        link = (
            self.connection.links.filter(is_active=True)
            .filter(operation__iexact="info")
            .order_by("priority", "id")
            .first()
        )
        if link is None:
            link = (
                self.connection.links.filter(is_active=True)
                .filter(code__iexact="info")
                .order_by("priority", "id")
                .first()
            )
        if link is None:
            return ProviderResult(code="CONFIG", description="لا توجد ربطية info فعالة لهذا المزود لفحص الرصيد.")

        transid = self.new_numeric_transid(self.connection, request_kind="balance")
        mobile = "0"
        try:
            password = self.connection.get_password()
            if not self.connection.userid or not self.connection.username or not password:
                return ProviderResult(code="CONFIG", description="بيانات اعتماد المزود غير مكتملة.")

            context = {"userid": self.connection.userid, "mobile": mobile, "transid": str(transid), "provider_transid": str(transid)}
            params = {key: self._render(value, context) for key, value in (link.fixed_params or {}).items()}
            for target, source in (link.field_map or {}).items():
                if isinstance(source, str) and source.startswith("{{") and source.endswith("}}"):
                    params[target] = self._render(source, context)
                elif isinstance(source, str):
                    params[target] = context.get(source, source)
                else:
                    params[target] = source
            params.setdefault("userid", self.connection.userid)
            params.setdefault("mobile", mobile)
            params.setdefault("transid", str(transid))
            params.setdefault("token", self.sanaacash_token(password, transid, self.connection.username, mobile))
            params.setdefault("action", "balance")

            headers = dict(self.connection.headers or {})
            headers.update(link.headers or {})
            timeout = max(1, int(self.connection.timeout_seconds or 20))
            response = self._request(link, self._url(link.path_template), params, headers, timeout)
            data, raw_text, code, desc, parsed = self._decode(response)
            if not 200 <= response.status_code < 300:
                return ProviderResult(code=f"HTTP_{response.status_code}", description=desc or "فشل رد المزود HTTP.", ambiguous=response.status_code >= 500, response=data, raw_text=raw_text)
            success = str(code) == "0" and "balance" in data
            return ProviderResult(
                code=code if parsed else "INVALID_RESPONSE",
                description=desc or ("تم جلب رصيد المزود بنجاح." if success else "رد المزود غير صالح."),
                success=success,
                ambiguous=not parsed,
                response=data,
                raw_text=raw_text,
            )
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            return ProviderResult(code="NETWORK" if isinstance(exc, requests.RequestException) else "CONFIG", description=str(exc), success=False, response={"error": str(exc)})

    def call(self, link, transaction, *, status_check=False):
        try:
            path = link.status_path_template if status_check and link.status_path_template else link.path_template
            params, context = self._params(link, transaction)
            if status_check and link.status_params:
                for target, value in link.status_params.items():
                    params[target] = self._render(value, context)
            headers = dict(self.connection.headers or {})
            headers.update(link.headers or {})
            timeout = max(1, int(self.connection.timeout_seconds or 20))
            response = self._request(link, self._url(path), params, headers, timeout)
            data, raw_text, code, desc, parsed = self._decode(response)
            if not 200 <= response.status_code < 300:
                return ProviderResult(code=f"HTTP_{response.status_code}", description=desc or "فشل رد المزود HTTP.", ambiguous=response.status_code >= 500, response=data, raw_text=raw_text)
            success_codes = {str(x) for x in (link.success_codes or ["0"])}
            pending_codes = {str(x) for x in (link.pending_codes or ["-2"])}
            pending = str(code) in pending_codes or "under process" in str(desc).lower() or "under proccess" in str(desc).lower()
            success = str(code) in success_codes
            if status_check and str(data.get("isDone")) == "1":
                success = True; pending = False
            if status_check and str(data.get("isBan")) == "1" and str(data.get("isDone")) != "1":
                success = False; pending = False
            if not parsed:
                return ProviderResult(code="INVALID_RESPONSE", description="رد المزود ليس JSON صالحًا؛ نتيجة العملية غير مؤكدة.", ambiguous=True, response=data, raw_text=raw_text)
            return ProviderResult(code=code, description=desc, pending=pending, success=success, response=data, raw_text=raw_text)
        except requests.RequestException as exc:
            return ProviderResult(code="NETWORK", description=str(exc), success=False, pending=False, ambiguous=True, response={"error": str(exc)})
        except (ValueError, RuntimeError) as exc:
            return ProviderResult(code="CONFIG", description=str(exc), success=False, pending=False, response={"error": str(exc)})
