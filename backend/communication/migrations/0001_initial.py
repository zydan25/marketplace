from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("marketplace", "0017_seed_global_storefront_themes")]
    operations = [
        migrations.CreateModel(name="Notification", fields=[], options={"verbose_name": "إشعار", "verbose_name_plural": "الإشعارات", "proxy": True}, bases=("marketplace.notification",)),
        migrations.CreateModel(name="Conversation", fields=[], options={"verbose_name": "محادثة", "verbose_name_plural": "المحادثات", "proxy": True}, bases=("marketplace.conversation",)),
        migrations.CreateModel(name="Message", fields=[], options={"verbose_name": "رسالة", "verbose_name_plural": "الرسائل", "proxy": True}, bases=("marketplace.message",)),
    ]
