# Generated by Django 5.0.4 on 2024-06-16 08:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('eventos', '0046_event_assigned_to_event_attendees'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='event',
            name='attendees',
        ),
    ]
