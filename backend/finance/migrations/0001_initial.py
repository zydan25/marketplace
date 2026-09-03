from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("marketplace", "0017_seed_global_storefront_themes")]
    operations = [
        migrations.CreateModel(name="Wallet", fields=[], options={"verbose_name": "محفظة", "verbose_name_plural": "المحافظ", "proxy": True}, bases=("marketplace.wallet",)),
        migrations.CreateModel(name="WalletTransaction", fields=[], options={"verbose_name": "حركة محفظة", "verbose_name_plural": "حركات المحافظ", "proxy": True}, bases=("marketplace.wallettransaction",)),
        migrations.CreateModel(name="Payment", fields=[], options={"verbose_name": "دفعة", "verbose_name_plural": "الدفعات", "proxy": True}, bases=("marketplace.payment",)),
        migrations.CreateModel(name="VendorPayout", fields=[], options={"verbose_name": "سحب تاجر", "verbose_name_plural": "طلبات سحب التجار", "proxy": True}, bases=("marketplace.vendorpayout",)),
        migrations.CreateModel(name="VendorLedgerEntry", fields=[], options={"verbose_name": "قيد دفتر تاجر", "verbose_name_plural": "قيود دفاتر التجار", "proxy": True}, bases=("marketplace.vendorledgerentry",)),
        migrations.CreateModel(name="CurrencyRate", fields=[], options={"verbose_name": "سعر صرف", "verbose_name_plural": "أسعار الصرف", "proxy": True}, bases=("marketplace.currencyrate",)),
        migrations.CreateModel(name="VendorCityShipping", fields=[], options={"verbose_name": "شحن تاجر حسب المدينة", "verbose_name_plural": "شحن التجار حسب المدن", "proxy": True}, bases=("marketplace.vendorcityshipping",)),
    ]
