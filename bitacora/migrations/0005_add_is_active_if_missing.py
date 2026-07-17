import uuid

from django.db import migrations, models


def drop_column_if_exists(apps, schema_editor):
    db = schema_editor.connection
    cursor = db.cursor()
    table = 'bitacora_bitacoraentry'
    column = 'is_active'
    if db.vendor == 'postgresql':
        cursor.execute(f'ALTER TABLE {table} DROP COLUMN IF EXISTS {column};')
    else:
        try:
            cursor.execute(f'ALTER TABLE {table} DROP COLUMN {column};')
        except Exception:
            pass
    cursor.close()


class Migration(migrations.Migration):

    dependencies = [
        ('bitacora', '0004_uuid_primary_keys'),
    ]

    operations = [
        migrations.RunPython(drop_column_if_exists, migrations.RunPython.noop),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='bitacoraentry',
                    name='id',
                    field=models.UUIDField(
                        primary_key=True,
                        default=uuid.uuid4,
                        editable=False,
                        serialize=False,
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
