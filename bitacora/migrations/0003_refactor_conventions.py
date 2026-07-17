import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def rename_autor_to_created_by(apps, schema_editor):
    db = schema_editor.connection
    cursor = db.cursor()
    if db.vendor == 'postgresql':
        cursor.execute(
            'ALTER TABLE bitacora_bitacoraentry RENAME COLUMN autor_id TO created_by_id;'
        )
    else:
        try:
            cursor.execute(
                'ALTER TABLE bitacora_bitacoraentry CHANGE autor_id created_by_id INT;'
            )
        except Exception:
            pass
    cursor.close()


def add_is_active_if_missing(apps, schema_editor):
    db = schema_editor.connection
    cursor = db.cursor()
    if db.vendor == 'postgresql':
        cursor.execute(
            'ALTER TABLE bitacora_bitacoraentry ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;'
        )
    else:
        try:
            cursor.execute(
                'ALTER TABLE bitacora_bitacoraentry ADD COLUMN is_active BOOLEAN DEFAULT TRUE;'
            )
        except Exception:
            pass
    cursor.close()


def populate_uuids(apps, schema_editor):
    BitacoraEntry = apps.get_model('bitacora', 'BitacoraEntry')
    for entry in BitacoraEntry.objects.all():
        entry.uuid_new = uuid.uuid4()
        entry.save(update_fields=['uuid_new'])

    BitacoraAttachment = apps.get_model('bitacora', 'BitacoraAttachment')
    for att in BitacoraAttachment.objects.all():
        att.uuid_new = uuid.uuid4()
        att.save(update_fields=['uuid_new'])


class Migration(migrations.Migration):

    dependencies = [
        ('bitacora', '0002_alter_bitacoraentry_contenido'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(rename_autor_to_created_by, migrations.RunPython.noop),
        migrations.AddField(
            model_name='bitacoraentry',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(add_is_active_if_missing, migrations.RunPython.noop),

        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RenameField(
                    model_name='bitacoraentry',
                    old_name='autor',
                    new_name='created_by',
                ),
            ],
            database_operations=[],
        ),

        migrations.AddField(
            model_name='bitacoraentry',
            name='uuid_new',
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.AddField(
            model_name='bitacoraattachment',
            name='uuid_new',
            field=models.UUIDField(null=True, editable=False),
        ),

        migrations.RunPython(populate_uuids, migrations.RunPython.noop),
    ]
