# Generated by Django 5.0.6 on 2024-06-28 21:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('eventos', '0054_event_tipificacion'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Tipificacion',
            new_name='Classification',
        ),
        migrations.RenameField(
            model_name='event',
            old_name='tipificacion',
            new_name='classification',
        ),
    ]
