# Generated by Django 5.2.4 on 2025-07-23 08:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='bookcover',
            name='cover_image',
            field=models.ImageField(blank=True, null=True, upload_to='generated_covers/'),
        ),
    ]
