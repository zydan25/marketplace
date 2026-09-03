from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("marketplace", "0017_seed_global_storefront_themes")]
    operations = [
        migrations.CreateModel(
            name="DesignTheme",
            fields=[],
            options={"verbose_name": "ثيم واجهة", "verbose_name_plural": "ثيمات الواجهات", "proxy": True},
            bases=("marketplace.designtheme",),
        ),
        migrations.CreateModel(
            name="StorefrontSection",
            fields=[],
            options={"verbose_name": "قسم واجهة", "verbose_name_plural": "أقسام الواجهة", "proxy": True},
            bases=("marketplace.storefrontsection",),
        ),
        migrations.CreateModel(
            name="StorefrontMedia",
            fields=[],
            options={"verbose_name": "وسائط واجهة", "verbose_name_plural": "وسائط الواجهة", "proxy": True},
            bases=("marketplace.storefrontmedia",),
        ),
    ]
