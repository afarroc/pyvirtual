# Generated by Django 5.0.4 on 2024-05-05 08:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('eventos', '0009_remove_eventattendee_event_remove_eventattendee_user_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='task',
            name='project',
        ),
    ]