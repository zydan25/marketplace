from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
def accounting_contract(request):
    return Response({
        "service": "marketplace-accounting",
        "version": "2",
        "source_of_truth": "journal_entries",
        "client_rule": "The client requests services and displays server results; it does not calculate balances, commissions, escrow or refunds.",
        "balance": {"GET": "/api/v2/accounting/wallets/me/balance/?currency=YER", "calculated_from": "posted JournalLine rows for the wallet account"},
        "statement": {"GET": "/api/v2/accounting/wallets/me/statement/?currency=YER", "report": "/api/v2/accounting/me/report/?currency=YER"},
        "transfers": {"POST": "/api/v2/accounting/transfers/", "entry": "Dr sender customer wallet / Cr recipient customer wallet"},
        "gifts": {"POST": "/api/v2/accounting/gifts/", "entry": "Dr sender customer wallet / Cr recipient customer wallet", "source_type": "gift"},
        "orders": {"POST": "/api/v2/orders/orders/", "validation": ["customer", "products", "vendor", "stock", "pricing", "shipping", "commission", "accounting balance"], "entry": "Dr customer wallet / Cr vendor pending + commission income"},
        "confirmation": {"POST": "/api/v2/orders/orders/{id}/confirm_received/", "entry": "Dr vendor pending / Cr vendor available"},
        "withdrawals": {"POST": "/api/v2/accounting/withdrawals/", "hold_entry": "Dr vendor available / Cr withdrawal hold", "pay_entry": "Dr withdrawal hold / Cr cash", "reject_entry": "Dr withdrawal hold / Cr vendor available"},
        "documents": "/ACCOUNTING_API_GUIDE_AR.md",
        "immutability": "Posted entries are immutable; corrections are new adjustment/reversal entries.",
    })
