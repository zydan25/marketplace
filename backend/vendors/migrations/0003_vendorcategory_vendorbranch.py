# Generated manually for the multi-vendor control workspace.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("vendors", "0002_delete_vendorapplication_delete_vendorprofile_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="VendorCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=140)),
                ("slug", models.SlugField(max_length=170)),
                ("description", models.TextField(blank=True)),
                ("image", models.ImageField(blank=True, null=True, upload_to="vendor/categories/")),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="children", to="vendors.vendorcategory")),
                ("vendor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="store_categories", to="vendors.vendorprofile")),
            ],
            options={
                "db_table": "marketplace_vendorcategory",
                "ordering": ["sort_order", "name", "id"],
            },
        ),
        migrations.CreateModel(
            name="VendorBranch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=160)),
                ("code", models.CharField(max_length=60)),
                ("manager_name", models.CharField(blank=True, max_length=160)),
                ("phone", models.CharField(blank=True, max_length=32)),
                ("governorate", models.CharField(blank=True, max_length=100)),
                ("address", models.CharField(blank=True, max_length=255)),
                ("latitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("longitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("opening_hours", models.JSONField(blank=True, default=dict)),
                ("is_main", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("vendor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="branches", to="vendors.vendorprofile")),
            ],
            options={
                "db_table": "marketplace_vendorbranch",
                "ordering": ["-is_main", "name", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="vendorcategory",
            constraint=models.UniqueConstraint(fields=("vendor", "slug"), name="uniq_vendor_category_slug"),
        ),
        migrations.AddIndex(
            model_name="vendorcategory",
            index=models.Index(fields=("vendor", "is_active"), name="vendorcat_vendor_active_idx"),
        ),
        migrations.AddIndex(
            model_name="vendorcategory",
            index=models.Index(fields=("vendor", "parent", "sort_order"), name="vendorcat_tree_idx"),
        ),
        migrations.AddConstraint(
            model_name="vendorbranch",
            constraint=models.UniqueConstraint(fields=("vendor", "code"), name="uniq_vendor_branch_code"),
        ),
        migrations.AddIndex(
            model_name="vendorbranch",
            index=models.Index(fields=("vendor", "is_active"), name="vendorbranch_vendor_active_idx"),
        ),
        migrations.AddIndex(
            model_name="vendorbranch",
            index=models.Index(fields=("vendor", "is_main"), name="vendorbranch_vendor_main_idx"),
        ),
    ]
