from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("marketplace", "0009_vendor_application")]
    operations = [
        migrations.CreateModel(
            name="StorefrontMedia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=180)),
                ("image", models.ImageField(upload_to="storefront/")),
                ("alt_text", models.CharField(blank=True, max_length=180)),
                ("target_url", models.CharField(blank=True, max_length=500)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("vendor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="storefront_media", to="marketplace.vendorprofile")),
            ],
            options={"ordering": ["-updated_at", "id"]},
        ),
        migrations.AddIndex(model_name="storefrontmedia", index=models.Index(fields=["vendor", "is_active"], name="marketplace_st_vendor_6d31f7_idx")),
    ]
