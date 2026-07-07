import uuid
import django.db.models.deletion
from django.db import migrations, models


def swap_pks_forward(apps, schema_editor):
    db = schema_editor.connection
    cursor = db.cursor()

    # 1. Temporal PK UUID en M2M tags
    cursor.execute("""
        ALTER TABLE bitacora_bitacoraentry_tags
        ADD COLUMN new_bitacoraentry_id uuid DEFAULT NULL;
    """)

    # 2. Poblar M2M desde uuid_new
    cursor.execute("""
        UPDATE bitacora_bitacoraentry_tags AS t
        SET new_bitacoraentry_id = e.uuid_new
        FROM bitacora_bitacoraentry AS e
        WHERE t.bitacoraentry_id = e.id;
    """)

    # 3. Temporal UUID en attachment
    cursor.execute("""
        ALTER TABLE bitacora_bitacoraattachment
        ADD COLUMN new_entry_id uuid DEFAULT NULL;
    """)

    cursor.execute("""
        UPDATE bitacora_bitacoraattachment AS a
        SET new_entry_id = e.uuid_new
        FROM bitacora_bitacoraentry AS e
        WHERE a.entry_id = e.id;
    """)

    # 4. Quitar restricciones dependientes de PKs/FKs antiguas
    cursor.execute("""
        ALTER TABLE bitacora_bitacoraentry_tags
        DROP CONSTRAINT IF EXISTS bitacora_bitacoraent_bitacoraentry_id_69ac99cf_fk_bitacora_;
    """)
    cursor.execute("""
        ALTER TABLE bitacora_bitacoraattachment
        DROP CONSTRAINT IF EXISTS bitacora_bitacoraatt_entry_id_4bec8fe6_fk_bitacora_;
    """)

    # 5. Swap PK en bitacoraentry
    cursor.execute("""
        ALTER TABLE bitacora_bitacoraentry
        DROP CONSTRAINT IF EXISTS bitacora_bitacoraentry_pkey;
    """)
    cursor.execute("""
        ALTER TABLE bitacora_bitacoraentry
        DROP COLUMN id;
    """)
    cursor.execute("""
        ALTER TABLE bitacora_bitacoraentry
        RENAME COLUMN uuid_new TO id;
    """)
    cursor.execute("""
        ALTER TABLE bitacora_bitacoraentry
        ADD PRIMARY KEY (id);
    """)

    # 6. Actualizar M2M tags
    cursor.execute("""
        ALTER TABLE bitacora_bitacoraentry_tags
        DROP COLUMN bitacoraentry_id;
    """)
    cursor.execute("""
        ALTER TABLE bitacora_bitacoraentry_tags
        RENAME COLUMN new_bitacoraentry_id TO bitacoraentry_id;
    """)
    cursor.execute("""
        ALTER TABLE bitacora_bitacoraentry_tags
        ALTER COLUMN bitacoraentry_id SET NOT NULL;
    """)
    cursor.execute("""
        ALTER TABLE bitacora_bitacoraentry_tags
        ADD CONSTRAINT bitacora_bitacoraentry_t_bitacoraentry_id_tag_id_uniq
        UNIQUE (bitacoraentry_id, tag_id);
    """)
    cursor.execute("""
        ALTER TABLE bitacora_bitacoraentry_tags
        ADD CONSTRAINT bitacora_bitacoraent_bitacoraentry_id_fk
        FOREIGN KEY (bitacoraentry_id)
        REFERENCES bitacora_bitacoraentry (id);
    """)

    # 7. Actualizar attachment
    cursor.execute("""
        ALTER TABLE bitacora_bitacoraattachment
        DROP COLUMN entry_id;
    """)
    cursor.execute("""
        ALTER TABLE bitacora_bitacoraattachment
        RENAME COLUMN new_entry_id TO entry_id;
    """)
    cursor.execute("""
        ALTER TABLE bitacora_bitacoraattachment
        ALTER COLUMN entry_id SET NOT NULL;
    """)
    cursor.execute("""
        ALTER TABLE bitacora_bitacoraattachment
        ADD CONSTRAINT bitacora_bitacoraatt_entry_id_fk
        FOREIGN KEY (entry_id)
        REFERENCES bitacora_bitacoraentry (id);
    """)

    # 8. Swap PK en bitacoraattachment
    cursor.execute("""
        ALTER TABLE bitacora_bitacoraattachment
        DROP CONSTRAINT IF EXISTS bitacora_bitacoraattachment_pkey;
    """)
    cursor.execute("""
        ALTER TABLE bitacora_bitacoraattachment
        DROP COLUMN id;
    """)
    cursor.execute("""
        ALTER TABLE bitacora_bitacoraattachment
        RENAME COLUMN uuid_new TO id;
    """)
    cursor.execute("""
        ALTER TABLE bitacora_bitacoraattachment
        ADD PRIMARY KEY (id);
    """)

    cursor.close()


def swap_pks_reverse(apps, schema_editor):
    raise NotImplementedError(
        "La migración 0004 no es reversible. "
        "Restaurar desde backup si es necesario."
    )


class Migration(migrations.Migration):

    dependencies = [
        ('bitacora', '0003_refactor_conventions'),
    ]

    operations = [
        migrations.RunPython(swap_pks_forward, swap_pks_reverse),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name='bitacoraentry',
                    name='uuid_new',
                ),
                migrations.RemoveField(
                    model_name='bitacoraattachment',
                    name='uuid_new',
                ),
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
                migrations.AlterField(
                    model_name='bitacoraattachment',
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
