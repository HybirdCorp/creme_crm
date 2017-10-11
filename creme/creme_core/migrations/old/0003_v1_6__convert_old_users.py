# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def convert_old_users(apps, schema_editor):
    User = apps.get_model("auth", "User")
    create = apps.get_model("creme_core", "CremeUser").objects.create
    creme_users = [create(id=user.id,
                          password=user.password,
                          last_login=user.last_login,
                          username=user.username,
                          first_name=user.first_name,
                          last_name=user.last_name,
                          email=user.email,
                          date_joined=user.date_joined,
                          is_active=user.is_active,
                          is_staff=user.is_staff,
                          is_superuser=user.is_superuser,
                          is_team=user.is_team,
                          role_id=user.role_id,
                         ) for user in User.objects.all()
                  ]

    for creme_user in creme_users:
        creme_user.teammates_set = User.objects.filter(team_m2m__team=user) \
                                               .values_list('id', flat=True)


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0002_v1_6__create_creme_user'),
    ]

    operations = [
        migrations.RunPython(convert_old_users),
    ]
