from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
from django.db.models import Q


CORE_SETTINGS = [
    ("yemen_mobile_balance_query", "رقم خدمة استعلام رصيد يمن موبايل", "yemen_mobile", "استعلام رصيد يمن موبايل"),
    ("yemen_mobile_advance_query", "رقم خدمة استعلام سلفة يمن موبايل", "yemen_mobile", "استعلام سلفة يمن موبايل"),
    ("yemen_mobile_packages_query", "رقم خدمة استعلام باقات يمن موبايل", "yemen_mobile", "استعلام باقات يمن موبايل"),
    ("yemen_mobile_packages_list", "رقم خدمة جلب باقات يمن موبايل", "yemen_mobile", "جلب باقات يمن موبايل"),
    ("yemen_mobile_denominations_list", "رقم خدمة جلب فئات يمن موبايل", "yemen_mobile", "جلب فئات يمن موبايل"),
    ("yemen_mobile_recharge", "رقم خدمة تسديد رصيد يمن موبايل", "yemen_mobile", "تسديد رصيد يمن موبايل"),
    ("yemen_mobile_package_pay_activate", "رقم خدمة تسديد وتفعيل باقة يمن موبايل", "yemen_mobile", "تسديد وتفعيل باقة يمن موبايل"),
    ("yemen_mobile_package_activate", "رقم خدمة تفعيل باقة يمن موبايل", "yemen_mobile", "تفعيل باقة يمن موبايل"),
    ("yemen_mobile_package_delete", "رقم خدمة حذف باقة يمن موبايل", "yemen_mobile", "حذف باقة يمن موبايل"),
    ("yemen_mobile_real_recharge", "رقم خدمة تسديد ريال موبايل يمن موبايل", "yemen_mobile", "تسديد ريال موبايل"),
    ("yemen_mobile_wholesale", "رقم خدمة تسديد جملة يمن موبايل", "yemen_mobile", "تسديد جملة يمن موبايل"),

    ("sabafon_north_packages_list", "رقم خدمة جلب باقات سبأفون شمال", "sabafon_north", "جلب باقات سبأفون - شمال"),
    ("sabafon_north_denominations_list", "رقم خدمة جلب فئات سبأفون شمال", "sabafon_north", "جلب فئات سبأفون - شمال"),
    ("sabafon_north_units_pay", "رقم خدمة تسديد وحدات سبأفون شمال", "sabafon_north", "تسديد وحدات سبأفون - شمال"),
    ("sabafon_north_denominations_pay", "رقم خدمة تسديد فئات سبأفون شمال", "sabafon_north", "تسديد فئات سبأفون - شمال"),
    ("sabafon_north_packages_pay", "رقم خدمة تسديد باقات سبأفون شمال", "sabafon_north", "تسديد باقات سبأفون - شمال"),
    ("sabafon_north_wholesale", "رقم خدمة تسديد جملة سبأفون شمال", "sabafon_north", "تسديد جملة سبأفون - شمال"),
    ("sabafon_south_packages_list", "رقم خدمة جلب باقات سبأفون جنوب", "sabafon_south", "جلب باقات سبأفون - جنوب"),
    ("sabafon_south_denominations_list", "رقم خدمة جلب فئات سبأفون جنوب", "sabafon_south", "جلب فئات سبأفون - جنوب"),
    ("sabafon_south_units_pay", "رقم خدمة تسديد وحدات سبأفون جنوب", "sabafon_south", "تسديد وحدات سبأفون - جنوب"),
    ("sabafon_south_denominations_pay", "رقم خدمة تسديد فئات سبأفون جنوب", "sabafon_south", "تسديد فئات سبأفون - جنوب"),
    ("sabafon_south_packages_pay", "رقم خدمة تسديد باقات سبأفون جنوب", "sabafon_south", "تسديد باقات سبأفون - جنوب"),
    ("sabafon_south_wholesale", "رقم خدمة تسديد جملة سبأفون جنوب", "sabafon_south", "تسديد جملة سبأفون - جنوب"),

    ("you_instant_recharge", "رقم خدمة شحن فوري يو", "you", "شحن فوري يو"),
    ("you_denominations_recharge", "رقم خدمة شحن فئات يو", "you", "شحن فئات يو"),
    ("you_packages_recharge", "رقم خدمة شحن باقات يو", "you", "شحن باقات يو"),
    ("you_wholesale_recharge", "رقم خدمة شحن جملة يو", "you", "شحن جملة يو"),
    ("you_postpaid_recharge", "رقم خدمة شحن فوترة يو", "you", "شحن فوترة يو"),
    ("you_denominations_list", "رقم خدمة جلب فئات يو", "you", "جلب فئات يو"),
    ("you_packages_list", "رقم خدمة جلب باقات يو", "you", "جلب باقات يو"),

    ("yemen4g_packages_list", "رقم خدمة جلب باقات يمن فورجي", "yemen4g", "جلب باقات يمن فورجي"),
    ("yemen4g_packages_pay", "رقم خدمة تسديد باقات يمن فورجي", "yemen4g", "تسديد باقات يمن فورجي"),
    ("yemen4g_package_change", "رقم خدمة تغيير باقة يمن فورجي", "yemen4g", "تغيير باقة يمن فورجي"),
    ("yemen4g_recharge", "رقم خدمة شحن رصيد يمن فورجي", "yemen4g", "شحن رصيد يمن فورجي"),
    ("yemen4g_balance_query", "رقم خدمة استعلام رصيد يمن فورجي", "yemen4g", "استعلام رصيد يمن فورجي"),

    ("yemen_net_adsl_query", "رقم خدمة استعلام ADSL يمن نت", "yemen_net", "استعلام ADSL يمن نت"),
    ("yemen_net_landline_query", "رقم خدمة استعلام الهاتف الثابت", "yemen_net", "استعلام الهاتف الثابت"),
    ("yemen_net_packages_list", "رقم خدمة جلب باقات يمن نت", "yemen_net", "جلب باقات يمن نت"),
    ("yemen_net_package_pay", "رقم خدمة تسديد باقة يمن نت", "yemen_net", "تسديد باقة يمن نت"),
    ("yemen_net_landline_pay", "رقم خدمة تسديد رصيد الهاتف الثابت", "yemen_net", "تسديد رصيد الهاتف الثابت"),

    ("wai_balance_query", "رقم خدمة استعلام رصيد واي", "wai", "استعلام رصيد واي"),
    ("wai_recharge", "رقم خدمة شحن رصيد واي", "wai", "شحن رصيد واي"),
    ("wai_denominations_list", "رقم خدمة جلب فئات واي", "wai", "جلب فئات واي"),
    ("wai_denominations_pay", "رقم خدمة شحن فئات واي", "wai", "شحن فئات واي"),
    ("wai_packages_list", "رقم خدمة جلب باقات واي", "wai", "جلب باقات واي"),
    ("wai_package_pay_activate", "رقم خدمة تسديد وتفعيل باقة واي", "wai", "تسديد وتفعيل باقة واي"),

    ("transfer_send", "رقم خدمة إرسال حوالة", "transfers", "خدمة إرسال الحوالة"),
    ("transfer_receive", "رقم خدمة استلام حوالة", "transfers", "خدمة استلام الحوالة"),
    ("instant_recharge", "رقم خدمة شحن فوري", "general_payments", "الخدمة العامة للشحن الفوري"),
    ("yemen_mobile_instant_recharge", "رقم خدمة شحن فوري يمن موبايل", "general_payments", "شحن فوري يمن موبايل"),
    ("you_instant_recharge_legacy", "رقم خدمة شحن فوري يو (الإعداد العام)", "general_payments", "شحن فوري يو - الإعداد العام"),
    ("sabafon_instant_recharge", "رقم خدمة شحن فوري سبأفون", "general_payments", "شحن فوري سبأفون"),
    ("wai_instant_recharge", "رقم خدمة شحن فوري واي", "general_payments", "شحن فوري واي"),
    ("you_packages_legacy", "رقم خدمة باقات يو (الإعداد العام)", "general_payments", "باقات يو - الإعداد العام"),
    ("sabafon_packages_legacy", "رقم خدمة باقات سبأفون (الإعداد العام)", "general_payments", "باقات سبأفون - الإعداد العام"),
    ("sabafon_units_legacy", "رقم خدمة وحدات سبأفون", "general_payments", "وحدات سبأفون - الإعداد العام"),
    ("mobile_balance_legacy", "رقم خدمة رصيد موبايلي", "general_payments", "خدمة رصيد موبايلي"),
    ("wholesale_legacy", "رقم خدمة الجملة", "general_payments", "خدمة الجملة"),
    ("landline_discounts", "رقم خدمة تخفيضات الثابت", "general_payments", "تخفيضات الهاتف الثابت"),
    ("internet_discounts", "رقم خدمة تخفيضات النت", "general_payments", "تخفيضات الإنترنت"),
    ("mobile_wholesale_legacy", "رقم خدمة موبايلي جملة", "general_payments", "موبايلي جملة"),
    ("sabafon_wholesale_legacy", "رقم خدمة سبأفون جملة", "general_payments", "سبأفون جملة"),
    ("you_wholesale_legacy", "رقم خدمة يو جملة", "general_payments", "يو جملة"),
    ("fixed_phone_service", "رقم خدمة الهاتف الثابت", "general_payments", "الهاتف الثابت"),
    ("terrestrial_internet_service", "رقم خدمة الإنترنت الأرضي", "general_payments", "الإنترنت الأرضي"),
    ("sabafon_south_packages_legacy", "رقم خدمة باقات سبأفون الجنوب", "general_payments", "باقات سبأفون الجنوب"),
    ("sabafon_south_instant_legacy", "رقم خدمة شحن فوري سبأفون الجنوب", "general_payments", "شحن فوري سبأفون الجنوب"),
    ("wifi_cards_sales", "رقم خدمة مبيعات كروت الواي فاي", "general_payments", "مبيعات كروت الواي فاي"),
]


def seed_settings(apps, schema_editor):
    ServiceSetting = apps.get_model("services", "ServiceSetting")
    for key, name, group, description in CORE_SETTINGS:
        ServiceSetting.objects.get_or_create(
            key=key,
            defaults={
                "name": name,
                "group": group,
                "description": description,
                "setting_type": "service",
                "service_id": None,
                "value": None,
                "is_system": True,
                "is_active": True,
                "sort_order": 0,
            },
        )


def unseed_settings(apps, schema_editor):
    ServiceSetting = apps.get_model("services", "ServiceSetting")
    ServiceSetting.objects.filter(is_system=True).delete()


class Migration(migrations.Migration):
    dependencies = [("services", "0011_wifi_card_credentials")]

    operations = [
        migrations.CreateModel(
            name="ServiceSetting",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.SlugField(max_length=140, unique=True)),
                ("name", models.CharField(max_length=220)),
                ("group", models.SlugField(default="general", max_length=80)),
                ("description", models.TextField(blank=True)),
                ("setting_type", models.CharField(choices=[("service", "خدمة"), ("text", "نص"), ("json", "JSON"), ("boolean", "نعم/لا")], default="service", max_length=12)),
                ("value", models.JSONField(blank=True, null=True)),
                ("is_system", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("service", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="service_settings", to="services.service")),
            ],
            options={
                "verbose_name": "إعداد خدمة",
                "verbose_name_plural": "إعدادات الخدمات",
                "ordering": ["group", "sort_order", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="servicesetting",
            index=models.Index(fields=["group", "is_active", "sort_order"], name="svc_setting_group_idx"),
        ),
        migrations.AddIndex(
            model_name="servicesetting",
            index=models.Index(fields=["service", "is_active"], name="svc_setting_service_idx"),
        ),
        migrations.AddConstraint(
            model_name="servicesetting",
            constraint=models.CheckConstraint(
                condition=Q(setting_type="service", service__isnull=False) | ~Q(setting_type="service"),
                name="svc_setting_service_required",
            ),
        ),
        migrations.RunPython(seed_settings, unseed_settings),
    ]
