# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations
from django.utils.timezone import now

from creme.creme_core.utils.date_period import date_period_registry
from creme.creme_core.utils.dates import round_hour


STATUS_OK = 20
IS_COMMERCIAL_APPROACH_EMAIL_NOTIFICATION_ENABLED = 'commercial-is_commercial_approach_email_notification_enabled'


def convert_setting_value(apps, schema_editor):
    get_model = apps.get_model
    sv = get_model('creme_core', 'SettingValue').objects \
                                                .filter(key_id=IS_COMMERCIAL_APPROACH_EMAIL_NOTIFICATION_ENABLED) \
                                                .first()

    if sv is None:
        return

    if sv.value_str == 'False':
        get_model('creme_core', 'Job').objects \
                                      .get_or_create(type_id='%s-%s' % ('commercial', 'com_approaches_emails_send'),
                                                     defaults={'language':      settings.LANGUAGE_CODE,
                                                               'periodicity':   date_period_registry.get_period('days', 1),
                                                               # 'periodicity': {'type': 'days', 'value': 1},
                                                               'status':        STATUS_OK,
                                                               'reference_run': round_hour(now()),
                                                               'enabled':       False,  # < ====
                                                              }
                                                    )

    sv.delete()


class Migration(migrations.Migration):
    dependencies = [
        # ('commercial', '0004_v1_6__segment_nullable_ptype'),
        ('commercial', '0001_initial'),
        ('creme_core', '0015_v1_7__create_job_models'),
    ]

    operations = [
        migrations.RunPython(convert_setting_value),
    ]
