from marketplace.models import Wallet as LegacyWallet, WalletTransaction as LegacyWalletTransaction
from marketplace.marketplace_models import Payment as LegacyPayment, VendorLedgerEntry as LegacyVendorLedgerEntry
from marketplace.models import VendorPayout as LegacyVendorPayout
from marketplace.models_extra import CurrencyRate as LegacyCurrencyRate, VendorCityShipping as LegacyVendorCityShipping


class Wallet(LegacyWallet):
    class Meta:
        proxy = True
        verbose_name = "محفظة"
        verbose_name_plural = "المحافظ"


class WalletTransaction(LegacyWalletTransaction):
    class Meta:
        proxy = True
        verbose_name = "حركة محفظة"
        verbose_name_plural = "حركات المحافظ"


class Payment(LegacyPayment):
    class Meta:
        proxy = True
        verbose_name = "دفعة"
        verbose_name_plural = "الدفعات"


class VendorPayout(LegacyVendorPayout):
    class Meta:
        proxy = True
        verbose_name = "سحب تاجر"
        verbose_name_plural = "طلبات سحب التجار"


class VendorLedgerEntry(LegacyVendorLedgerEntry):
    class Meta:
        proxy = True
        verbose_name = "قيد دفتر تاجر"
        verbose_name_plural = "قيود دفاتر التجار"


class CurrencyRate(LegacyCurrencyRate):
    class Meta:
        proxy = True
        verbose_name = "سعر صرف"
        verbose_name_plural = "أسعار الصرف"


class VendorCityShipping(LegacyVendorCityShipping):
    class Meta:
        proxy = True
        verbose_name = "شحن تاجر حسب المدينة"
        verbose_name_plural = "شحن التجار حسب المدن"
