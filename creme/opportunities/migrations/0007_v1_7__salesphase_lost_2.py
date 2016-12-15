# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from django.conf import settings
from django.db import migrations
from django.utils.translation import activate, pgettext


def set_lost_field(apps, schema_editor):
    SalesPhase = apps.get_model('opportunities', 'SalesPhase')

    if SalesPhase.objects.exists():
        activate(settings.LANGUAGE_CODE)

        name = pgettext('opportunities-sales_phase', u'Lost')
        sale_phase = SalesPhase.objects.filter(name=name).first()

        if sale_phase is not None:
            sale_phase.lost = True
            sale_phase.save()
        else:
            print(u'There is no SalesPhase named "%s" ; '
                  u'you should probably set the attribute "lost=True" to at least one SalesPhase.' % name
                 )


class Migration(migrations.Migration):
    dependencies = [
        ('opportunities', '0006_v1_7__salesphase_lost_1'),
    ]

    operations = [
        migrations.RunPython(set_lost_field),
    ]
