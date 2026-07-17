import django.db.models.deletion
from django.db import migrations, models


def safe_drop_callrecord_uuid(apps, schema_editor):
    db = schema_editor.connection
    cursor = db.cursor()
    if db.vendor == 'postgresql':
        cursor.execute('ALTER TABLE IF EXISTS kpis_callrecord DROP COLUMN IF EXISTS uuid;')
    else:
        try:
            cursor.execute('ALTER TABLE kpis_callrecord DROP COLUMN uuid;')
        except Exception:
            pass
    cursor.close()


def safe_drop_exchangerate_uuid(apps, schema_editor):
    db = schema_editor.connection
    cursor = db.cursor()
    if db.vendor == 'postgresql':
        cursor.execute('ALTER TABLE IF EXISTS kpis_exchangerate DROP COLUMN IF EXISTS uuid;')
    else:
        try:
            cursor.execute('ALTER TABLE kpis_exchangerate DROP COLUMN uuid;')
        except Exception:
            pass
    cursor.close()


class Migration(migrations.Migration):

    dependencies = [
        ('kpis', '0002_refactor_callrecord'),
    ]

    operations = [
        migrations.RunPython(safe_drop_callrecord_uuid, migrations.RunPython.noop),
        migrations.RunPython(safe_drop_exchangerate_uuid, migrations.RunPython.noop),

        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name='callrecord',
                    name='uuid',
                ),
                migrations.RemoveField(
                    model_name='exchangerate',
                    name='uuid',
                ),
                migrations.AlterField(
                    model_name='callrecord',
                    name='aht',
                    field=models.FloatField(validators=[django.core.validators.MinValueValidator(0)], verbose_name='AHT (segundos)'),
                ),
                migrations.AlterField(
                    model_name='callrecord',
                    name='created_at',
                    field=models.DateTimeField(auto_now_add=True, default=0),
                    preserve_default=False,
                ),
                migrations.AlterField(
                    model_name='callrecord',
                    name='evaluaciones',
                    field=models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Evaluaciones'),
                ),
                migrations.AlterField(
                    model_name='callrecord',
                    name='eventos',
                    field=models.IntegerField(validators=[django.core.validators.MinValueValidator(0)], verbose_name='Eventos'),
                ),
                migrations.AlterField(
                    model_name='callrecord',
                    name='fecha',
                    field=models.DateField(db_index=True, default=0, help_text='Primer día de la semana a la que corresponde el registro', verbose_name='Fecha'),
                    preserve_default=False,
                ),
                migrations.AlterField(
                    model_name='callrecord',
                    name='id',
                    field=models.UUIDField(default=django.db.models.deletion.SET_NULL, editable=False, primary_key=True, serialize=False),
                ),
                migrations.AlterField(
                    model_name='callrecord',
                    name='satisfaccion',
                    field=models.FloatField(default=0.0, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Satisfacción (1-10)'),
                ),
                migrations.AlterField(
                    model_name='callrecord',
                    name='semana',
                    field=models.IntegerField(db_index=True, help_text='Número de semana ISO (calculado de fecha)', verbose_name='Semana'),
                ),
                migrations.AlterField(
                    model_name='exchangerate',
                    name='id',
                    field=models.UUIDField(default=django.db.models.deletion.SET_NULL, editable=False, primary_key=True, serialize=False),
                ),
                migrations.AlterField(
                    model_name='exchangerate',
                    name='rate',
                    field=models.DecimalField(decimal_places=6, help_text='Tasa promedio PEN/USD — Compra interbancaria', max_digits=10, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Tasa de cambio'),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql='ALTER TABLE IF EXISTS kpis_callrecord DROP COLUMN IF EXISTS uuid;',
                    reverse_sql=migrations.RunSQL.noop,
                ),
                migrations.RunSQL(
                    sql='ALTER TABLE IF EXISTS kpis_exchangerate DROP COLUMN IF EXISTS uuid;',
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),
    ]
