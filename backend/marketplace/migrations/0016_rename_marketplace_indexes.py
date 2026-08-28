from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0015_merge_20260828_1929"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="catalogoption",
            old_name="marketplace_c_group_i_0e79c0_idx",
            new_name="catopt_grp_active_idx",
        ),
        migrations.RenameIndex(
            model_name="catalogoption",
            old_name="marketplace_c_categor_0be1ef_idx",
            new_name="catopt_cat_grp_active_idx",
        ),
        migrations.RenameIndex(
            model_name="vendorcityshipping",
            old_name="marketplace_v_vendor_c_f2b09e_idx",
            new_name="vcs_vendor_city_active_idx",
        ),
    ]
