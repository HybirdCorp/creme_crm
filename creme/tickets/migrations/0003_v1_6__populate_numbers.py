# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def populate_numbers(apps, schema_editor):
    get_model = apps.get_model
    TicketNumber = get_model('tickets', 'TicketNumber')
    create_number = TicketNumber.objects.create
    last_number = None

    # NB: we create, then delete, TicketNumbers in order to keep the sequence
    # (PostgerSQL) correct, in an esay way.
    for ticket in get_model('tickets', 'Ticket').objects.order_by('id'):
        last_number = create_number()
        ticket.number = last_number.id
        ticket.save()

    if last_number:
        TicketNumber.objects.exclude(id=last_number.id).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('tickets', '0002_v1_6__titles_not_unique__add_number'),
    ]

    operations = [
        migrations.RunPython(populate_numbers),
    ]
