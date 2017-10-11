# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from collections import defaultdict
from json import dumps as jsondumps, loads as jsonloads

from django.conf import settings
from django.db import migrations


USER_MOBILE_SYNC_SERVER_URL    = 'activesync-mapi-server_url-user'
USER_MOBILE_SYNC_SERVER_DOMAIN = 'activesync-mapi-domain-user'
USER_MOBILE_SYNC_SERVER_SSL    = 'activesync-mapi-server_ssl-user'  # type=SettingKey.BOOL
USER_MOBILE_SYNC_SERVER_LOGIN  = 'activesync-mapi-server_login-user'
USER_MOBILE_SYNC_SERVER_PWD    = 'activesync-mapi-server_pwd-user'
USER_MOBILE_SYNC_ACTIVITIES    = 'activesync-sync_activities_user'  # type=SettingKey.BOOL
USER_MOBILE_SYNC_CONTACTS      = 'activesync-sync_contacts_user'    # type=SettingKey.BOOL


def migrate_user_settings(apps, schema_editor):
    if settings.AUTH_USER_MODEL != 'creme_core.CremeUser':
        print('It seems the user model is customised ; so you will have to write your own migration.')
        return

    get_model = apps.get_model
    CremeUser    = get_model('creme_core', 'CremeUser')
    SettingValue = get_model('creme_core', 'SettingValue')

    users_data = defaultdict(dict)

    # String values
    for svalue in SettingValue.objects.filter(key_id__in=(USER_MOBILE_SYNC_SERVER_URL,
                                                          USER_MOBILE_SYNC_SERVER_DOMAIN,
                                                          USER_MOBILE_SYNC_SERVER_LOGIN,
                                                          USER_MOBILE_SYNC_SERVER_PWD,
                                                         )):
        users_data[svalue.user_id][svalue.key_id] = svalue.value_str

    # Boolean values
    for svalue in SettingValue.objects.filter(key_id__in=(USER_MOBILE_SYNC_SERVER_SSL,
                                                          USER_MOBILE_SYNC_ACTIVITIES,
                                                          USER_MOBILE_SYNC_CONTACTS,
                                                         )):
        users_data[svalue.user_id][svalue.key_id] = True if svalue.value_str == 'True' else False

    for user in CremeUser.objects.filter(id__in=users_data.keys()):
        values = jsonloads(user.json_settings)
        values.update(users_data[user.id])

        user.json_settings = jsondumps(values)
        user.save()

    SettingValue.objects.filter(key_id__in=(USER_MOBILE_SYNC_SERVER_URL,
                                            USER_MOBILE_SYNC_SERVER_DOMAIN,
                                            USER_MOBILE_SYNC_SERVER_LOGIN,
                                            USER_MOBILE_SYNC_SERVER_PWD,
                                            USER_MOBILE_SYNC_SERVER_SSL,
                                            USER_MOBILE_SYNC_ACTIVITIES,
                                            USER_MOBILE_SYNC_CONTACTS,
                                           )
                               ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0018_v1_7__cremeuser_settings'),
        # ('activesync', '0003_v1_6__django18_hints'),
        ('activesync', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(migrate_user_settings),
    ]
