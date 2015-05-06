# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from django.db import models, migrations
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CremeUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last login')),
                ('username', models.CharField(help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.',
                                              unique=True, max_length=30, verbose_name='Username',
                                              validators=[django.core.validators.RegexValidator(re.compile(b'^[\\w.@+-]+$'), 'Enter a valid username.', b'invalid')]
                                             )
                ),
                ('first_name', models.CharField(max_length=100, verbose_name='First name', blank=True)),
                ('last_name', models.CharField(max_length=100, verbose_name='Last name', blank=True)),
                ('email', models.EmailField(max_length=75, verbose_name='Email address', blank=True)),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Date joined')),
                ('is_active', models.BooleanField(default=True, verbose_name='Is active?')),
                ('is_staff', models.BooleanField(default=False, verbose_name='Is staff?')),
                ('is_superuser', models.BooleanField(default=False, verbose_name='Is a superuser?')),
                ('is_team', models.BooleanField(default=False, verbose_name='Is a team?')),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Role', to='creme_core.UserRole', null=True)),
                ('teammates_set', models.ManyToManyField(related_name='teams_set', verbose_name='Teammates', to='creme_core.CremeUser')),
            ],
            options={
                'ordering': ('username',),
                'verbose_name': 'User',
                'verbose_name_plural': 'Users',
            },
            bases=(models.Model,),
        ),
    ]
