from marketplace.models import Coupon as LegacyCoupon, Referral as LegacyReferral
from marketplace.marketplace_models import CouponRedemption as LegacyCouponRedemption
from marketplace.models_extra import Address as LegacyAddress, GiftTransfer as LegacyGiftTransfer, Loan as LegacyLoan


class Coupon(LegacyCoupon):
    class Meta:
        proxy = True
        verbose_name = "كوبون"
        verbose_name_plural = "الكوبونات"


class CouponRedemption(LegacyCouponRedemption):
    class Meta:
        proxy = True
        verbose_name = "استخدام كوبون"
        verbose_name_plural = "استخدامات الكوبونات"


class Referral(LegacyReferral):
    class Meta:
        proxy = True
        verbose_name = "إحالة"
        verbose_name_plural = "الإحالات"


class Address(LegacyAddress):
    class Meta:
        proxy = True
        verbose_name = "عنوان"
        verbose_name_plural = "العناوين"


class Loan(LegacyLoan):
    class Meta:
        proxy = True
        verbose_name = "طلب تمويل"
        verbose_name_plural = "طلبات التمويل"


class GiftTransfer(LegacyGiftTransfer):
    class Meta:
        proxy = True
        verbose_name = "تحويل هدية"
        verbose_name_plural = "تحويلات الهدايا"
