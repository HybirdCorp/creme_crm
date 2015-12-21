# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.contrib.auth.models
import django.core.validators
from django.db import models, migrations

# NB: replaces the vanilla migrations.
# 0002_alter_permission_name_max_length
# 0003_alter_user_email_max_length
# 0004_alter_user_username_opts
# 0005_alter_user_last_login_null
# 0006_require_contenttypes_0002

class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='group',
            managers=[
                ('objects', django.contrib.auth.models.GroupManager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='permission',
            managers=[
                ('objects', django.contrib.auth.models.PermissionManager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='user',
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),

        migrations.AlterField(
            model_name='permission',
            name='name',
            field=models.CharField(max_length=255, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(max_length=254, verbose_name='email address', blank=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='last_login',
            field=models.DateTimeField(null=True, verbose_name='last login', blank=True),
        ),
        # No database changes; modifies validators and error_messages (#13147).
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(error_messages={'unique': 'A user with that username already exists.'}, max_length=30,
                                   validators=[django.core.validators.RegexValidator('^[\\w.@+-]+$', 'Enter a valid username. This value may contain only letters, numbers and @/./+/-/_ characters.', 'invalid')],
                                   help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.',
                                   unique=True, verbose_name='username',
                                  ),
        ),
    ]
