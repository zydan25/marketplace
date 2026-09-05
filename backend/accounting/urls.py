from django.urls import path
from rest_framework.routers import DefaultRouter

from .api import AccountViewSet, JournalEntryViewSet, VoucherViewSet, WalletViewSet, WithdrawalViewSet

router = DefaultRouter()
router.register("accounts", AccountViewSet, basename="account")
router.register("wallets", WalletViewSet, basename="accounting-wallet")
router.register("journals", JournalEntryViewSet, basename="journal-entry")
router.register("vouchers", VoucherViewSet, basename="voucher")
router.register("withdrawals", WithdrawalViewSet, basename="withdrawal")

urlpatterns = router.urls
