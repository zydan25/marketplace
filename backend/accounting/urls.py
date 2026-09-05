from django.urls import path
from rest_framework.routers import DefaultRouter

from .api_v2 import AccountViewSet, JournalEntryViewSet, VoucherViewSet, WalletViewSet, WithdrawalViewSet
from .extra_api import account_report, post_journal
from .financial_api import gift, transfer

router = DefaultRouter()
router.register("accounts", AccountViewSet, basename="account")
router.register("wallets", WalletViewSet, basename="accounting-wallet")
router.register("journals", JournalEntryViewSet, basename="journal-entry")
router.register("vouchers", VoucherViewSet, basename="voucher")
router.register("withdrawals", WithdrawalViewSet, basename="withdrawal")

urlpatterns = [
    path("me/report/", account_report, name="account-report"),
    path("journals/post/", post_journal, name="journal-post"),
    path("transfers/", transfer, name="transfer"),
    path("gifts/", gift, name="gift"),
]
urlpatterns += router.urls
