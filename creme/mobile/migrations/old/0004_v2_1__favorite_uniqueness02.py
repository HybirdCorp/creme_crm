# -*- coding: utf-8 -*-

# from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0001_initial'),
        # migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('mobile', '0003_v2_1__favorite_uniqueness01'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='mobilefavorite',
            unique_together={('entity', 'user')},
        ),
    ]
