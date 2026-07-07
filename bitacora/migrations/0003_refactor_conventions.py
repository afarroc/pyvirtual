import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def rename_autor_to_created_by(apps, schema_editor):
    db = schema_editor.connection
    cursor = db.cursor()
    cursor.execute(
        "ALTER TABLE bitacora_bitacoraentry RENAME COLUMN autor_id TO created_by_id;"
    )
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
        # Rename real en BD: autor_id -> created_by_id
        migrations.RunPython(rename_autor_to_created_by, migrations.RunPython.noop),

        # Sincronizar estado Django sin tocar BD más allá de is_active
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RenameField(
                    model_name='bitacoraentry',
                    old_name='autor',
                    new_name='created_by',
                ),
                migrations.AlterField(
                    model_name='bitacoraentry',
                    name='created_by',
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='bitacora_entries',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                migrations.AddField(
                    model_name='bitacoraentry',
                    name='is_active',
                    field=models.BooleanField(default=True),
                ),
                migrations.AlterField(
                    model_name='bitacoraentry',
                    name='mood',
                    field=models.CharField(
                        blank=True,
                        max_length=20,
                        choices=[
                            ('muy_bien', '😄 Muy bien'),
                            ('bien',     '🙂 Bien'),
                            ('neutral',  '😐 Neutral'),
                            ('mal',      '😕 Mal'),
                            ('muy_mal',  '😞 Muy mal'),
                        ],
                    ),
                ),
                migrations.AlterField(
                    model_name='bitacoraentry',
                    name='categoria',
                    field=models.CharField(
                        default='personal',
                        max_length=50,
                        choices=[
                            ('personal',  'Personal'),
                            ('viaje',     'Viaje'),
                            ('trabajo',   'Trabajo'),
                            ('meta',      'Meta'),
                            ('idea',      'Idea'),
                            ('recuerdo',  'Recuerdo'),
                            ('diario',    'Diario'),
                            ('reflexion', 'Reflexión'),
                        ],
                    ),
                ),
                migrations.AlterField(
                    model_name='bitacoraentry',
                    name='related_event',
                    field=models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='bitacora_entries',
                        to='events.event',
                    ),
                ),
                migrations.AlterField(
                    model_name='bitacoraentry',
                    name='related_task',
                    field=models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='bitacora_entries',
                        to='events.task',
                    ),
                ),
                migrations.AlterField(
                    model_name='bitacoraentry',
                    name='related_project',
                    field=models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='bitacora_entries',
                        to='events.project',
                    ),
                ),
                migrations.AlterField(
                    model_name='bitacoraentry',
                    name='related_room',
                    field=models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='bitacora_entries',
                        to='rooms.room',
                    ),
                ),
            ],
            database_operations=[
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
            ],
        ),

        # UUID temporales para el swap de PK
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

        # Poblar UUIDs en registros existentes
        migrations.RunPython(populate_uuids, migrations.RunPython.noop),
    ]
