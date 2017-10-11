# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        # ('auth', '0001_initial'),
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MobileFavorite',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('entity', models.ForeignKey(related_name='mobile_favorite', to='creme_core.CremeEntity')),
                # ('user', models.ForeignKey(related_name='mobile_favorite', to='auth.User')),
                ('user', models.ForeignKey(related_name='mobile_favorite', to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
