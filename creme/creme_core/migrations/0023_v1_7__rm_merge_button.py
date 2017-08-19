# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


BUTTON_ID = 'button_creme_core-merge_entities'


def remove_config_for_merge_button(apps, schema_editor):
    ButtonMenuItem = apps.get_model('creme_core', 'ButtonMenuItem')

    # Default config
    bm_items = ButtonMenuItem.objects.filter(content_type__isnull=True)

    if len(bm_items) == 1:
        bm_item = bm_items[0]

        if bm_item.button_id == BUTTON_ID:
            bm_item.button_id = ''
            bm_item.save()

    # Specific configs
    ButtonMenuItem.objects \
                  .filter(content_type__isnull=False, button_id=BUTTON_ID) \
                  .delete()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0022_v1_7__rtype_min_display'),
    ]

    operations = [
        migrations.RunPython(remove_config_for_merge_button),
    ]
