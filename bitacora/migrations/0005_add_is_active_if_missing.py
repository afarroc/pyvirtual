from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bitacora', '0004_uuid_primary_keys'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE bitacora_bitacoraentry "
                "ADD COLUMN IF NOT EXISTS is_active boolean DEFAULT TRUE;"
            ),
            reverse_sql=(
                "ALTER TABLE bitacora_bitacoraentry "
                "DROP COLUMN IF EXISTS is_active;"
            ),
        ),
    ]
