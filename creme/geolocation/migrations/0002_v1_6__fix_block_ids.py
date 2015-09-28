# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def update_block_ids(apps, schema_editor):
    get_model = apps.get_model

    def generate_id(app_name, name):
        return u'block_%s-%s' % (app_name, name)

    BlockDetailviewLocation = get_model('creme_core', 'BlockDetailviewLocation')
    BlockDetailviewLocation.objects.filter(block_id=generate_id('persons', 'geolocation')) \
                                   .update(block_id=generate_id('geolocation', 'detail_google_maps'))
    BlockDetailviewLocation.objects.filter(block_id=generate_id('whoisarround', 'geolocation')) \
                                   .update(block_id=generate_id('geolocation', 'google_whoisaround'))

    old_id = generate_id('persons_filters', 'geolocation')
    new_id = generate_id('geolocation', 'filtered_google_maps')
    for model_name in ('BlockPortalLocation', 'BlockMypageLocation'):
        get_model('creme_core', model_name).objects.filter(block_id=old_id).update(block_id=new_id)


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0001_initial'),
        ('geolocation', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(update_block_ids),
    ]
