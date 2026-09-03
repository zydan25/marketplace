from django.urls import path
from rest_framework.routers import DefaultRouter

from .api import (
    AddressViewSet,
    CouponRedemptionViewSet,
    CouponViewSet,
    GiftTransferViewSet,
    LoanViewSet,
    ReferralViewSet,
    api_info,
)

router = DefaultRouter()
router.register("coupons", CouponViewSet, basename="promotion-coupon")
router.register("coupon-redemptions", CouponRedemptionViewSet, basename="coupon-redemption")
router.register("referrals", ReferralViewSet, basename="referral")
router.register("addresses", AddressViewSet, basename="promotion-address")
router.register("loans", LoanViewSet, basename="promotion-loan")
router.register("gifts", GiftTransferViewSet, basename="promotion-gift")

urlpatterns = [path("", api_info, name="promotions-api-info")]
urlpatterns += router.urls
