# Generated by Django 3.1.3 on 2020-12-18 02:00

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('app', '0005_auto_20201217_2100'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='BackloggedGame',
            new_name='BackloggedGameModel',
        ),
    ]
