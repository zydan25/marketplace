import requests

from .provider import ProviderClient, ProviderResult


def fetch_provider_info(connection):
    """Fetch the provider's current account information from its canonical /info endpoint."""
    if connection.connection_type != "sanaacash":
        return ProviderResult(code="UNSUPPORTED", description="فحص رصيد المزود غير مهيأ لهذا النوع من الربط.")

    transid = ProviderClient.new_numeric_transid(connection, request_kind="balance")
    mobile = "0"
    params = {
        "userid": connection.userid,
        "mobile": mobile,
        "transid": str(transid),
        "token": ProviderClient.sanaacash_token(connection.get_password(), transid, connection.username, mobile),
    }
    headers = dict(connection.headers or {})
    timeout = max(1, int(connection.timeout_seconds or 20))
    client = ProviderClient(connection)
    try:
        response = requests.get(client._url("info"), params=params, headers=headers, timeout=timeout)
        data, raw_text, code, desc = client._decode(response)
        balance = data.get("balance", data.get("accountBalance", data.get("availableBalance")))
        success = str(code) == "0" and balance is not None
        if success:
            data = dict(data)
            data["normalized_balance"] = balance
        return ProviderResult(
            code=code,
            description=desc or ("تم جلب رصيد المزود بنجاح." if success else "تعذر استخراج الرصيد من استجابة info."),
            success=success,
            response=data,
            raw_text=raw_text,
        )
    except requests.RequestException as exc:
        return ProviderResult(code="NETWORK", description=str(exc), success=False, response={"error": str(exc)})
