# Generated by Django 5.0.4 on 2024-05-08 10:26

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eventos', '0030_alter_event_event_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='event_status',
            field=models.ForeignKey(default=16, on_delete=django.db.models.deletion.CASCADE, to='eventos.status'),
        ),
    ]
