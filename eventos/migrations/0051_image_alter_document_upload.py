# Generated by Django 5.0.6 on 2024-06-21 00:14

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eventos', '0050_document'),
    ]

    operations = [
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('upload', models.FileField(upload_to='get_upload_path', validators=[django.core.validators.FileExtensionValidator(['jpg', 'bmp', 'png'])])),
            ],
        ),
        migrations.AlterField(
            model_name='document',
            name='upload',
            field=models.FileField(upload_to='get_upload_path', validators=[django.core.validators.FileExtensionValidator(['pdf', 'docx', 'ppt'])]),
        ),
    ]