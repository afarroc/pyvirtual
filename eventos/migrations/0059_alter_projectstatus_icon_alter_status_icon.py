# Generated by Django 5.0.6 on 2024-07-06 03:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eventos', '0058_projectstatus'),
    ]

    operations = [
        migrations.AlterField(
            model_name='projectstatus',
            name='icon',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='status',
            name='icon',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
    ]
