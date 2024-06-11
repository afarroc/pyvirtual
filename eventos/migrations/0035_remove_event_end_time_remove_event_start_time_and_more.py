# Generated by Django 5.0.4 on 2024-06-11 01:05

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eventos', '0034_task_created_at_task_important_task_updated_at_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='event',
            name='end_time',
        ),
        migrations.RemoveField(
            model_name='event',
            name='start_time',
        ),
        migrations.AlterField(
            model_name='event',
            name='event_status',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='eventos.status'),
        ),
        migrations.CreateModel(
            name='EventHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('edited_at', models.DateTimeField(auto_now_add=True)),
                ('field_name', models.CharField(max_length=100)),
                ('old_value', models.TextField(blank=True, null=True)),
                ('new_value', models.TextField(blank=True, null=True)),
                ('editor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='eventos.event')),
            ],
        ),
        migrations.CreateModel(
            name='EventState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='eventos.event')),
                ('status', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='eventos.status')),
            ],
        ),
    ]