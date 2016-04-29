# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict

import pytz

from django.conf import settings
from django.db import migrations, models


def migrate_old_settings(apps, schema_editor):
    if settings.AUTH_USER_MODEL != 'creme_core.CremeUser':
        return

    USER_TIMEZONE   = 'creme_config-usertimezone'
    USER_THEME_NAME = 'creme_config-userthemename'

    svalues_qs = apps.get_model('creme_core', 'SettingValue')\
                     .objects.filter(key_id__in=(USER_TIMEZONE, USER_THEME_NAME))
    users_info = defaultdict(dict)

    for svalue in svalues_qs:
        users_info[svalue.user_id][svalue.key_id] = svalue.value_str

    default_tz = settings.TIME_ZONE
    default_theme = settings.THEMES[0][0]

    for user in apps.get_model('creme_core', 'CremeUser').objects.all():
        get_info = users_info[user.id].get
        user.time_zone = get_info(USER_TIMEZONE,   default_tz)
        user.theme     = get_info(USER_THEME_NAME, default_theme)
        user.save()

    svalues_qs.delete()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0016_v1_7__entity_indexes_count'),
    ]

    operations = [
        migrations.AddField(
            model_name='cremeuser',
            name='theme',
            field=models.CharField(default=settings.THEMES[0][0], max_length=50, verbose_name='Theme',
                                   # choices=[(b'icecream', 'Ice cream'), (b'chantilly', 'Chantilly')],
                                   choices=settings.THEMES,
                                  ),
        ),
        migrations.AddField(
            model_name='cremeuser',
            name='time_zone',
            field=models.CharField(default=settings.TIME_ZONE,
                                   max_length=50, verbose_name='Time zone',
                                   choices=[(tz, tz) for tz in pytz.common_timezones],
                                  ),
        ),

        migrations.RunPython(migrate_old_settings),
    ]
