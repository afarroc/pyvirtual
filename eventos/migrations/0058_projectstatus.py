# Generated by Django 5.0.6 on 2024-07-06 03:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eventos', '0057_alter_project_created_at_alter_project_updated_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status_name', models.CharField(max_length=50)),
                ('icon', models.CharField(blank=True, max_length=30)),
                ('active', models.BooleanField(default=True)),
                ('color', models.CharField(default='white', max_length=30)),
            ],
        ),
    ]
