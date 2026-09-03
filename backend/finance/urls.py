from django.urls import path
from rest_framework.routers import DefaultRouter

from .api import (
    CurrencyRateViewSet,
    PaymentViewSet,
    VendorCityShippingViewSet,
    VendorFinanceViewSet,
    VendorLedgerEntryViewSet,
    VendorPayoutViewSet,
    WalletTransactionViewSet,
    WalletViewSet,
    api_info,
)

router = DefaultRouter()
router.register("wallets", WalletViewSet, basename="finance-wallet")
router.register("wallet-transactions", WalletTransactionViewSet, basename="wallet-transaction")
router.register("payments", PaymentViewSet, basename="finance-payment")
router.register("vendor-finance", VendorFinanceViewSet, basename="vendor-finance")
router.register("vendor-payouts", VendorPayoutViewSet, basename="vendor-payout")
router.register("vendor-ledger", VendorLedgerEntryViewSet, basename="vendor-ledger")
router.register("currency-rates", CurrencyRateViewSet, basename="currency-rate")
router.register("vendor-city-shipping", VendorCityShippingViewSet, basename="vendor-city-shipping")

urlpatterns = [path("", api_info, name="finance-api-info")]
urlpatterns += router.urls
