# Generated by Django 3.1.3 on 2020-12-18 01:59

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('app', '0003_auto_20201216_1649'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='BackloggedGamesModel',
            new_name='BackloggedGames',
        ),
    ]
