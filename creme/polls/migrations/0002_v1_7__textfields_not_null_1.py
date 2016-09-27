# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


FORM_SECTION_FIELDS = ['body']
REPLY_SECTION_FIELDS = ['body']
CAMPAIGN_FIELDS = ['goal']


def fill_none_strings(apps, schema_editor):
    def migrate_model(name, fields):
        manager = apps.get_model('polls', name).objects

        for field_name in fields:
            manager.filter(**{field_name: None}).update(**{field_name: ''})

    def migrate_swappable_model(setting_model, name, fields):
        if setting_model == 'polls.%s' % name:
            migrate_model(name, fields)

    migrate_model('PollFormSection',  FORM_SECTION_FIELDS)
    migrate_model('PollReplySection', REPLY_SECTION_FIELDS)

    migrate_swappable_model(settings.POLLS_CAMPAIGN_MODEL, 'PollCampaign', CAMPAIGN_FIELDS)


class Migration(migrations.Migration):
    dependencies = [
        ('polls', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fill_none_strings)
    ]
