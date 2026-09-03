from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("marketplace", "0017_seed_global_storefront_themes")]
    operations = [
        migrations.CreateModel(name="Coupon", fields=[], options={"verbose_name": "كوبون", "verbose_name_plural": "الكوبونات", "proxy": True}, bases=("marketplace.coupon",)),
        migrations.CreateModel(name="CouponRedemption", fields=[], options={"verbose_name": "استخدام كوبون", "verbose_name_plural": "استخدامات الكوبونات", "proxy": True}, bases=("marketplace.couponredemption",)),
        migrations.CreateModel(name="Referral", fields=[], options={"verbose_name": "إحالة", "verbose_name_plural": "الإحالات", "proxy": True}, bases=("marketplace.referral",)),
        migrations.CreateModel(name="Address", fields=[], options={"verbose_name": "عنوان", "verbose_name_plural": "العناوين", "proxy": True}, bases=("marketplace.address",)),
        migrations.CreateModel(name="Loan", fields=[], options={"verbose_name": "طلب تمويل", "verbose_name_plural": "طلبات التمويل", "proxy": True}, bases=("marketplace.loan",)),
        migrations.CreateModel(name="GiftTransfer", fields=[], options={"verbose_name": "تحويل هدية", "verbose_name_plural": "تحويلات الهدايا", "proxy": True}, bases=("marketplace.gifttransfer",)),
    ]
